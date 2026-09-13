"""Provision SSL certificates for a specific custom domain (or all DNS-verified).

This is the manual/ops twin of the scheduled ``provision_custom_domain_ssl``
task — useful right after wiring up certbot to expedite activation:

    * python manage.py provision_custom_domain_ssl --domain mystore.com
    * python manage.py provision_custom_domain_ssl --all
"""
from django.core.management.base import BaseCommand

from store.models import CustomDomain
from store.services.custom_domain import run_ssl_provision


class Command(BaseCommand):
    help = 'Issue Let\'s Encrypt certificates for custom domains through certbot.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', default='', help='Normalized domain to provision (required).')
        parser.add_argument('--all', action='store_true', help='Provision SSL for every DNS-verified domain.')

    def handle(self, *args, **options):
        domains = CustomDomain.objects.filter(dns_status='connected').exclude(ssl_status='active')
        if options['domain']:
            domains = domains.filter(normalized_domain=options['domain'])
        elif not options['all']:
            self.stdout.write(self.style.WARNING('Pass --domain X or --all.'))
            return

        done = skipped = failed = 0
        for row in domains:
            try:
                ok = run_ssl_provision(row)
            except Exception as exc:
                self.stderr.write(f'{row.normalized_domain}: error {exc}')
                ok = False
            if ok:
                done += 1
                self.stdout.write(self.style.SUCCESS(f'{row.normalized_domain}: SSL active.'))
            elif row.ssl_status != 'active':
                failed += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f'Provisioned {done}, skipped {skipped}, failed {failed}.'))