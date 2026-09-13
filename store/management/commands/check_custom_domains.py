"""Advance the custom-domain lifecycle for all pending/failed domains.

Best used from cron when Celery beat is not available:

    * / 5 * * * /path/to/venv/bin/python manage.py check_custom_domains

Any connected (DNS-verified) domain receives its SSL certificate and goes live
automatically; the whole rest of the flow needs no manual intervention.
"""
from django.core.management.base import BaseCommand

from store.services.custom_domain import check_pending_domains


class Command(BaseCommand):
    help = 'Check DNS/SSL for all pending custom domains and activate ready stores.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', default='', help='Only process a single normalized domain.')
        parser.add_argument('--limit', type=int, default=200, help='Max domains to process per run.')

    def handle(self, *args, **options):
        summary = check_pending_domains(limit=options['limit'], domain=options['domain'])
        self.stdout.write(self.style.SUCCESS(
            f"Processed {summary['processed']} domain(s), activated {summary['activated']}."
        ))
        if summary.get('certbot') is False:
            self.stdout.write(self.style.WARNING(
                'certbot is not installed on this server — SSL provisioning is deferred until it is available.'
            ))
        return f"Processed {summary['processed']}, activated {summary['activated']}."