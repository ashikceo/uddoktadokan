"""Production ACME (Let's Encrypt) automation via the certbot CLI.

Django orchestrates the flow: once DNS is confirmed it invokes
``certbot certonly`` for the domain, stores the issued certificate under
``/etc/letsencrypt/live/<domain>/`` and schedules automatic renewal.

The certbot binary must be installed on the production server — that single
server-level dependency is outside what a Django process can install by
itself, so it is documented as an explicit manual deployment step (see
``docs/custom_domains.md``). Private keys are never read or logged by Django.
"""
import logging
import re
import shutil
import subprocess
from datetime import datetime, timezone

from django.conf import settings

logger = logging.getLogger('store.custom_domains')

LIVE_DIR = '/etc/letsencrypt/live'
_ENDDATE_RE = re.compile(r'notAfter=(.*)')


def certbot_available():
    return bool(shutil.which('certbot'))


def _cert_paths(domain):
    return f'{LIVE_DIR}/{domain}/fullchain.pem', f'{LIVE_DIR}/{domain}/privkey.pem'


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return result.returncode, (result.stdout or '') + ('\n' + result.stderr if result.stderr else '')


def certificate_expiry(domain):
    """Return cert expiry as aware datetime, or None if unavailable."""
    cert_path, _ = _cert_paths(domain)
    try:
        code, out = _run(['openssl', 'x509', '-enddate', '-noout', '-in', cert_path])
        if code != 0:
            return None
        match = _ENDDATE_RE.search(out)
        if not match:
            return None
        # OpenSSL emits naive local time — treat it as UTC to be safe.
        parsed = datetime.strptime(match.group(1).strip(), '%b %d %H:%M:%S %Y %Z')
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception as exc:
        logger.debug('Could not read cert expiry for %s: %s', domain, exc)
        return None


def provision_ssl(normalized_domain, email=''):
    """Issue (or re-issue) a certificate for a domain through certbot.

    Returns ``(ok, message)``.
    """
    if not certbot_available():
        return False, 'certbot is not installed on this server (SSL provisioning deferred).'

    email = email or getattr(settings, 'ACME_EMAIL', '')
    webroot = getattr(settings, 'SSL_WEBROOT', '')
    directory = getattr(settings, 'ACME_DIRECTORY_URL', '')

    cmd = ['certbot', 'certonly', '--webroot', '-w', webroot, '-d', normalized_domain,
           '--non-interactive', '--agree-tos', '--keep-until-expiring', '--quiet']
    if email:
        cmd += ['--email', email]
    if directory:
        cmd += ['--server', directory]

    try:
        code, out = _run(cmd)
    except Exception as exc:
        logger.warning('certbot run failed for %s: %s', normalized_domain, exc)
        return False, 'SSL provisioning failed. The system will retry automatically.'

    expiry = certificate_expiry(normalized_domain)
    if code == 0 and expiry:
        logger.info('Certificate issued for %s (expires %s)', normalized_domain, expiry)
        return True, 'SSL certificate is active.'
    if code == 0:
        return True, 'SSL certificate is generated.'
    logger.warning('certbot failed for %s: %s', normalized_domain, out[-1500:])
    return False, 'SSL provisioning failed. The system will retry automatically.'


def renew_all_certificates():
    """Renew all expiring certificates. Returns number renewed (best effort)."""
    if not certbot_available():
        return 0
    try:
        code, out = _run(['certbot', 'renew', '--quiet'])
        if code != 0:
            logger.warning('certbot renew reported a problem: %s', out[-1500:])
            return 0
        return 1
    except Exception as exc:
        logger.warning('certbot renew raised: %s', exc)
        return 0