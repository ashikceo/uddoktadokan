"""Custom domain lifecycle orchestration (Django side).

Workflow:

    owner adds domain -> claim_domain() validates + creates status=pending
    -> background checks (celery beat / management command) call
       check_pending_domains()
    -> each pending domain runs process_domain():
           DNS confirmed  -> dns_status=connected, start SSL provisioning
           SSL issued     -> ssl_status=active, status=active, is_active=True
    -> CustomDomainRoutingMiddleware serves the store on the live domain.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ..domain_utils import host_key, validate_domain
from ..models import CustomDomain, Partner
from . import acme, dns_verification

logger = logging.getLogger('store.custom_domains')


def account_type_for(partner):
    """Derive the account type from the partner role flags."""
    if partner.is_dealer:
        return 'DEALER'
    if partner.is_seller:
        return 'SELLER'
    return 'PARTNER'


def custom_domain_enabled():
    return getattr(settings, 'CUSTOM_DOMAIN_ENABLED', True)


def cache_key(host):
    return f'custom_domain:map:{host_key(host)}'


def get_store_for_host(host):
    """Return the active Partner routed to *host*, or None.

    Uses the cache to avoid a query per request. Invalidated automatically by
    model signals on any CustomDomain change.
    """
    if not host:
        return None
    norm = host_key(host)
    if not norm:
        return None
    key = cache_key(norm)
    partner_id = cache.get(key)
    if partner_id is None:
        try:
            row = CustomDomain.objects.select_related('owner').filter(
                normalized_domain=norm, is_active=True, status='active',
            ).first()
            partner_id = row.owner_id if row else None
        except Exception:
            partner_id = None
        cache.set(key, partner_id, 300)
    if not partner_id:
        return None
    return Partner.objects.filter(pk=partner_id).first()


def claim_domain(owner, raw_domain):
    """Validate and claim *raw_domain* for *owner* (a Partner).

    Returns ``(CustomDomain, None)`` on success, or ``(None, error_message)``.
    Raises ValueError for invalid input.
    """
    normalized = validate_domain(raw_domain)
    if CustomDomain.objects.filter(normalized_domain=normalized).exists():
        return None, 'This domain is already connected to another store.'

    domain = CustomDomain(
        owner=owner,
        domain=normalized,
        normalized_domain=normalized,
        account_type=account_type_for(owner),
    )
    domain.save()
    logger.info('CustomDomain %s created for %s (%s)', normalized, owner.slug, domain.account_type)
    return domain, None


def run_dns_check(domain_obj):
    """Check DNS for a domain and persist results."""
    result = dns_verification.check_domain_dns(
        domain_obj.normalized_domain,
        platform_domain=getattr(settings, 'PLATFORM_DOMAIN', ''),
        server_ip=getattr(settings, 'SERVER_IP', ''),
    )
    domain_obj.last_dns_check = timezone.now()
    if result['ok']:
        domain_obj.dns_status = 'connected'
        domain_obj.dns_verified_at = domain_obj.last_dns_check
        domain_obj.error_message = ''
        if domain_obj.status in ('pending', 'failed'):
            domain_obj.status = 'dns_verified'
            domain_obj.ssl_status = 'waiting'
    else:
        domain_obj.dns_status = 'failed'
        if domain_obj.status != 'failed':
            domain_obj.status = 'pending'
        domain_obj.error_message = result['message']
    domain_obj.save(update_fields=[
        'dns_status', 'status', 'error_message', 'dns_verified_at', 'last_dns_check', 'updated_at',
    ])
    return result


def run_ssl_provision(domain_obj):
    """Attempt SSL provisioning for a DNS-connected domain."""
    if not custom_domain_enabled():
        return
    if domain_obj.ssl_status == 'active':
        return
    if domain_obj.dns_status != 'connected':
        return
    domain_obj.status = 'ssl_provisioning'
    domain_obj.ssl_status = 'provisioning'
    domain_obj.error_message = ''
    domain_obj.save(update_fields=['status', 'ssl_status', 'error_message', 'updated_at'])

    ok, message = acme.provision_ssl(domain_obj.normalized_domain, getattr(settings, 'ACME_EMAIL', ''))
    domain_obj.last_ssl_check = timezone.now()
    if ok:
        domain_obj.ssl_status = 'active'
        domain_obj.ssl_issued_at = timezone.now()
        expiry = acme.certificate_expiry(domain_obj.normalized_domain)
        domain_obj.ssl_expires_at = expiry or (timezone.now() + timedelta(days=90))
        domain_obj.status = 'active'
        domain_obj.is_active = True
        domain_obj.is_primary = True
        domain_obj.error_message = ''
    else:
        domain_obj.ssl_status = 'failed'
        domain_obj.status = 'failed'
        domain_obj.error_message = message
    domain_obj.save()
    logger.info('SSL for %s -> %s', domain_obj.normalized_domain, domain_obj.ssl_status)
    return ok


def process_domain(domain_obj):
    """Advance a single domain through its lifecycle (DNS -> SSL -> active)."""
    if domain_obj.status == 'active':
        # Renewal window check happens asynchronously in renew_ssl_if_needed().
        return True
    if domain_obj.dns_status != 'connected':
        run_dns_check(domain_obj)
    if domain_obj.dns_status == 'connected' and domain_obj.status not in ('active',):
        run_ssl_provision(domain_obj)
    return domain_obj.status == 'active'


def check_pending_domains(limit=200, domain=None):
    """Background entry point: advance all pending/failed domains.

    Returns a small summary ``{'processed': n, 'activated': n, ...}``.
    """
    qs = CustomDomain.objects.select_related('owner').filter(
        status__in=['pending', 'dns_verified', 'ssl_provisioning', 'failed'],
    ).order_by('created_at')
    if not custom_domain_enabled():
        # Still allow status cleanup/reporting without touching DNS.
        return {'processed': qs.count(), 'activated': 0}
    if domain:
        qs = qs.filter(normalized_domain=domain)
    processed = 0
    activated = 0
    for row in qs[:limit]:
        processed += 1
        try:
            if process_domain(row):
                activated += 1
        except Exception as exc:
            logger.exception('Custom domain processing failed for %s', row.normalized_domain)
            row.status = 'failed'
            row.error_message = 'Background processing failed — the system will retry automatically.'
            row.save(update_fields=['status', 'error_message', 'updated_at'])
    return {'processed': processed, 'activated': activated, 'certbot': acme.certbot_available()}


def renew_ssl_if_needed():
    """Renew all certificates that are within the renewal window."""
    renew_days = getattr(settings, 'CUSTOM_DOMAIN_RENEW_DAYS', 30)
    now = timezone.now()
    due = CustomDomain.objects.filter(
        ssl_status='active',
        status='active',
        ssl_expires_at__isnull=False,
        ssl_expires_at__lte=now + timedelta(days=renew_days),
    )
    renewed = 0
    for row in due:
        ok, _ = acme.provision_ssl(row.normalized_domain, getattr(settings, 'ACME_EMAIL', ''))
        if ok:
            row.ssl_status = 'active'
            expiry = acme.certificate_expiry(row.normalized_domain)
            if expiry:
                row.ssl_expires_at = expiry
            row.last_ssl_check = now
            row.save()
            renewed += 1
    if renewed:
        logger.info('Renewed SSL for %d custom domains.', renewed)
    return renewed


def disconnect(domain_obj):
    """Disconnect a domain (keeps history)."""
    domain_obj.retire()
    return True