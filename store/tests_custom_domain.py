"""Tests for the automated custom domain system.

Run with:

    venv/bin/python manage.py test store.tests_custom_domain

DNS lookups are mocked — tests never touch the network.
"""
from datetime import timedelta
from unittest import mock

from django.http import HttpResponseNotFound
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .domain_utils import host_key, normalize_domain, strip_www, validate_domain
from .models import CustomDomain, Partner, Product
from .services import custom_domain as service
from .services.dns_verification import check_domain_dns

PUBLIC_IP = '8.8.8.8'
PLATFORM = 'platform.store'


def make_partner(name, **kwargs):
    kwargs.setdefault('name', name)
    return Partner.objects.create(**kwargs)


def make_product(partner, slug, name='Widget'):
    return Product.objects.create(name=name, price=100, slug=slug, partner=partner)


class MakeActiveDomain:
    """Helper to create an already-live custom domain for a partner."""
    @staticmethod
    def make(partner, domain, server='A', primary=True):
        row = CustomDomain.objects.create(
            owner=partner,
            domain=domain,
            normalized_domain=domain,
            status='active',
            dns_status='connected',
            ssl_status='active',
            is_active=True,
            is_primary=primary,
            dns_verified_at=timezone.now(),
            ssl_issued_at=timezone.now(),
        )
        return row


class DomainValidationTests(TestCase):
    def test_strips_scheme_path_query_and_upper(self):
        self.assertEqual(
            validate_domain('HTTPS://SHOP.MYSTORE.COM/path?x=1'),
            'shop.mystore.com',
        )

    def test_normalize_returns_none_for_empty(self):
        self.assertIsNone(normalize_domain('   '))

    def test_strips_www_host_key(self):
        self.assertEqual(strip_www('www.mystore.com'), 'mystore.com')
        self.assertEqual(host_key('shOP.MyStore.COM'), 'shop.mystore.com')

    def test_accepts_valid_subdomains_and_punycode(self):
        self.assertEqual(validate_domain('shop.mystore.store'), 'shop.mystore.store')
        self.assertEqual(validate_domain('xn--bcher-kva.store'), 'xn--bcher-kva.store')

    def test_rejects_ip_literal(self):
        for raw in ('192.168.1.1', '10.0.0.1', '2001:db8::1'):
            with self.assertRaises(ValueError):
                validate_domain(raw)

    def test_rejects_single_label(self):
        with self.assertRaises(ValueError):
            validate_domain('shop')

    def test_rejects_spaces_and_invalid_chars(self):
        for raw in ('bad host.com', 'exa mple.com', 'my@store.com'):
            with self.assertRaises(ValueError):
                validate_domain(raw)

    def test_rejects_reserved_localhost_test(self):
        for raw in ('localhost', 'foo.local', 'foo.test', 'foo.internal', 'foo.invalid'):
            with self.assertRaises(ValueError):
                validate_domain(raw)

    @override_settings(CUSTOM_DOMAIN_ALLOW_INTERNAL=True)
    def test_allows_internal_names_when_enabled(self):
        self.assertEqual(validate_domain('shop.local.test'), 'shop.local.test')

    @override_settings(CUSTOM_DOMAIN_ALLOW_INTERNAL=False)
    def test_internal_flag_off_still_rejects(self):
        with self.assertRaises(ValueError):
            validate_domain('shop.local.test')

    def test_rejects_digit_or_short_tld(self):
        with self.assertRaises(ValueError):
            validate_domain('store.123')
        with self.assertRaises(ValueError):
            validate_domain('store.e')


class CustomDomainModelTests(TestCase):
    def setUp(self):
        self.p = make_partner('Store One')

    def test_save_attaches_account_type_via_service(self):
        row = CustomDomain.objects.create(
            owner=self.p, domain='one.store', normalized_domain='one.store',
            account_type=service.account_type_for(self.p),
        )
        self.assertEqual(row.account_type, 'PARTNER')

    def test_unique_normalized_domain(self):
        MakeActiveDomain.make(self.p, 'dup.store')
        with self.assertRaises(Exception):
            MakeActiveDomain.make(make_partner('Store Two'), 'dup.store')

    def test_activation_demotes_previous_primary(self):
        first = MakeActiveDomain.make(self.p, 'first.store')
        second = MakeActiveDomain.make(self.p, 'second.store')
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(second.is_primary)
        self.assertTrue(second.is_active)
        self.assertFalse(first.is_primary)
        self.assertFalse(first.is_active)

    def test_save_forces_inactive_when_status_not_active(self):
        row = CustomDomain.objects.create(
            owner=self.p, domain='pending.store', normalized_domain='pending.store',
            is_active=True, is_primary=True, status='pending',
        )
        row.refresh_from_db()
        self.assertFalse(row.is_active)

    def test_retire_disconnects(self):
        row = MakeActiveDomain.make(self.p, 'bye.store')
        row.retire()
        row.refresh_from_db()
        self.assertEqual(row.status, 'disconnected')
        self.assertFalse(row.is_active)
        self.assertFalse(row.is_primary)


class CustomDomainServiceTests(TestCase):
    def setUp(self):
        self.p = make_partner('Store One')

    def test_account_type_for_flags(self):
        self.assertEqual(service.account_type_for(make_partner('S', is_seller=True)), 'SELLER')
        self.assertEqual(service.account_type_for(make_partner('D', is_dealer=True)), 'DEALER')
        self.assertEqual(service.account_type_for(make_partner('P')), 'PARTNER')

    def test_claim_domain_creates_pending_row(self):
        row, err = service.claim_domain(self.p, 'https://New.Store/')
        self.assertIsNone(err)
        self.assertEqual(row.normalized_domain, 'new.store')
        self.assertEqual(row.status, 'pending')

    def test_claim_domain_rejects_duplicate_owner(self):
        MakeActiveDomain.make(self.p, 'taken.store')
        row, err = service.claim_domain(make_partner('Other'), 'taken.store')
        self.assertIsNone(row)
        self.assertIn('already connected', err)

    def test_claim_domain_invalid_raises(self):
        with self.assertRaises(ValueError):
            service.claim_domain(self.p, 'not-a-domain')

    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a', return_value={PUBLIC_IP})
    def test_process_domain_followed_by_activated(self, *mocks):
        row, _ = service.claim_domain(self.p, 'pipeline.store')
        with mock.patch('store.services.custom_domain.acme.provision_ssl',
                        return_value=(True, 'SSL active.')) as m_prov:
            with mock.patch('store.services.custom_domain.acme.certificate_expiry',
                            return_value=timezone.now() + timedelta(days=90)):
                ok = service.process_domain(row)
        row.refresh_from_db()
        self.assertTrue(ok)
        self.assertEqual(row.status, 'active')
        self.assertTrue(row.is_active)
        self.assertTrue(row.is_primary)
        self.assertTrue(m_prov.called)

    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a', return_value=set())
    def test_process_domain_with_no_dns_stays_pending(self, *mocks):
        row, _ = service.claim_domain(self.p, 'spencer.store')
        ok = service.process_domain(row)
        row.refresh_from_db()
        self.assertFalse(ok)
        self.assertEqual(row.dns_status, 'failed')


class DnsVerificationTests(TestCase):
    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a', side_effect=lambda d: {PUBLIC_IP})
    def test_matches_server_ip(self, *mocks):
        result = check_domain_dns('mystore.store', platform_domain=PLATFORM, server_ip=PUBLIC_IP)
        self.assertTrue(result['ok'])
        self.assertIn('A ' + PUBLIC_IP, result['records'])

    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a',
                side_effect=lambda d: {'9.9.9.9'})
    def test_matches_platform_address_when_ips_equal(self, *mocks):
        result = check_domain_dns('mystore.store', platform_domain=PLATFORM, server_ip='')
        self.assertTrue(result['ok'])

    @mock.patch('store.services.dns_verification._resolve_cname', return_value=PLATFORM)
    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a', return_value={'9.9.9.9'})
    def test_cname_chain_to_platform(self, *mocks):
        result = check_domain_dns('www.mystore.store', platform_domain=PLATFORM, server_ip='')
        self.assertTrue(result['ok'])

    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a', return_value=set())
    def test_no_records_fails(self, *mocks):
        result = check_domain_dns('mystore.store', platform_domain=PLATFORM, server_ip=PUBLIC_IP)
        self.assertFalse(result['ok'])
        self.assertIn('No DNS records', result['message'])

    @mock.patch('store.services.dns_verification._resolve_aaaa', return_value=set())
    @mock.patch('store.services.dns_verification._resolve_a', return_value={'10.0.0.5'})
    def test_private_address_rejected(self, *mocks):
        result = check_domain_dns('mystore.store', platform_domain=PLATFORM, server_ip=PUBLIC_IP)
        self.assertFalse(result['ok'])
        self.assertIn('non-public', result['message'])


class CustomDomainRoutingTests(TestCase):
    def setUp(self):
        self.p = make_partner('Store One')
        self.other = make_partner('Store Two')
        self.active = MakeActiveDomain.make(self.p, 'one.store')
        MakeActiveDomain.make(self.other, 'two.store')

    def get(self, path, host):
        return self.client.get(path, HTTP_HOST=host)

    def test_unknown_host_rejected(self):
        resp = self.get('/', 'evil.attacker.store')
        self.assertEqual(resp.status_code, 400)

    def test_platform_host_passes(self):
        resp = self.get('/', 'localhost')
        self.assertEqual(resp.status_code, 200)

    @override_settings(PLATFORM_DOMAIN=PLATFORM)
    def test_configured_platform_domain_passes(self):
        resp = self.get('/', PLATFORM)
        self.assertEqual(resp.status_code, 200)

    def test_root_renders_store_for_owner(self):
        resp = self.get('/', 'one.store')
        self.assertEqual(resp.status_code, 200)

    def test_marketplace_page_404_on_custom_domain(self):
        for path in ('/shop/', '/category/electronics/', '/search/?q=phone',
                     '/blog/', '/partners/', '/sellers/', '/dealers/', '/contact/'):
            resp = self.get(path, 'one.store')
            self.assertIsInstance(resp, (HttpResponseNotFound,))
            self.assertEqual(resp.status_code, 404)

    def test_owner_partner_page_passes(self):
        resp = self.get(f'/partner/{self.p.slug}/', 'one.store')
        self.assertEqual(resp.status_code, 200)

    def test_other_partner_page_404_on_custom_domain(self):
        resp = self.get(f'/partner/{self.other.slug}/', 'one.store')
        self.assertEqual(resp.status_code, 404)

    def test_owner_product_renders(self):
        prod = make_product(self.p, 'widget-one')
        resp = self.get(f'/product/{prod.slug}/', 'one.store')
        self.assertEqual(resp.status_code, 200)

    def test_foreign_product_404_on_custom_domain(self):
        prod = make_product(self.other, 'widget-two')
        resp = self.get(f'/product/{prod.slug}/', 'one.store')
        self.assertEqual(resp.status_code, 404)

    def test_checkout_and_cart_paths_work(self):
        for path in ('/cart/', '/checkout/', '/wishlist/', '/compare/', '/dashboard/'):
            resp = self.get(path, 'one.store')
            self.assertIn(resp.status_code, (200, 302), f'{path} -> {resp.status_code}')

    def test_www_redirects_to_canonical(self):
        resp = self.get('/', 'www.one.store')
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp['Location'], 'http://one.store/')

    def test_domain_without_active_custom_domain_rejected(self):
        resp = self.get('/', 'three.store')
        self.assertEqual(resp.status_code, 400)

    def test_get_store_cache_returns_owner(self):
        self.assertEqual(service.get_store_for_host('one.store').pk, self.p.pk)

    def test_activation_invalidates_route_cache(self):
        service.get_store_for_host('new.store')
        row = CustomDomain.objects.create(
            owner=self.p, domain='new.store', normalized_domain='new.store',
            status='active', dns_status='connected', ssl_status='active',
            is_active=True, is_primary=True,
        )
        row.save()
        self.assertEqual(service.get_store_for_host('new.store').pk, self.p.pk)


class DashboardUrlTests(TestCase):
    def test_dashboard_url_resolves(self):
        self.assertTrue(reverse('dashboard_custom_domain').endswith('/dashboard/custom-domain/'))

    def test_dashboard_card_renders_for_partner(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user('dashboard-owner', 'o@o.store', 'pw')
        p = make_partner('Dashboard Owner')
        p.user = user
        p.save(update_fields=['user'])
        MakeActiveDomain.make(p, 'dash.store')
        self.client.login(username='dashboard-owner', password='pw')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Custom Domain')
        self.assertContains(resp, 'dash.store')