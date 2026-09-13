"""Domain normalization and validation helpers for the custom domain system.

Kept free of model imports so it can be used both by ``store.models`` and the
service layer without creating import cycles.
"""
import re

import idna
from django.conf import settings

_SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*://')
_LABEL_RE = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?')
_IPV4_RE = re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}$')
_IPV6_RE = re.compile(r'^[0-9a-fA-F:]{2,45}$')

# IANA special-use / internal hostnames that must never host a store.
_RESERVED_SUFFIXES = (
    '.localhost',
    '.local',
    '.internal',
    '.invalid',
    '.test',
    '.example',
    '.home.arpa',
    '.lan',
)


def normalize_domain(value):
    """Normalize a raw user input into a bare hostname.

    Handles ``https://mystore.com/``, ``www.mystore.com``, ``MYSTORE.COM``,
    surrounding whitespace and query/fragment suffixes. Returns ``None`` for
    empty input.
    """
    if not value:
        return None
    value = str(value).strip().lower()
    value = _SCHEME_RE.sub('', value)
    # Strip path, query and fragment.
    value = re.split(r'[/?#]', value, maxsplit=1)[0]
    value = value.strip(' .')
    return value or None


def _is_ip_literal(host):
    if _IPV4_RE.match(host):
        return True
    if _IPV6_RE.match(host) and ':' in host:
        return True
    return False


def validate_domain(value, allow_internal=None):
    """Validate and canonicalize a domain.

    Returns the punycode-canonical ascii hostname (lowercase, trailing dot
    removed). Raises ``ValueError`` with a user-safe message when invalid.

    ``allow_internal`` optionally permits IANA reserved suffixes such as
    ``.test`` / ``.localhost`` which are only ever useful in local development.
    """
    if allow_internal is None:
        allow_internal = getattr(settings, 'CUSTOM_DOMAIN_ALLOW_INTERNAL', False)

    raw = normalize_domain(value)
    if not raw:
        raise ValueError('Enter a valid domain name.')
    if len(raw) > 253:
        raise ValueError('That domain name is too long.')

    if _is_ip_literal(raw):
        raise ValueError('IP addresses are not allowed — enter a domain name like mystore.com.')

    if ' ' in raw or '@' in raw or ',' in raw or ':' in raw:
        raise ValueError('Enter a valid domain name.')

    if raw == 'localhost' or raw.endswith(_RESERVED_SUFFIXES) or raw.endswith('.home.arpa'):
        if allow_internal and (raw.endswith('.localhost') or raw.endswith('.test')):
            pass
        else:
            raise ValueError('Internal or reserved host names cannot be used.')

    try:
        ascii_host = idna.encode(raw, uts46=True).decode('ascii').lower().rstrip('.')
    except Exception:
        raise ValueError('Enter a valid domain name.')

    labels = ascii_host.split('.')
    if len(labels) < 2:
        raise ValueError('Enter a full domain name including the extension (for example mystore.com).')

    for label in labels:
        if len(label) > 63 or not _LABEL_RE.fullmatch(label):
            raise ValueError('Enter a valid domain name.')

    # TLD must exist and match a plausible public suffix (no digits only).
    tld = labels[-1]
    if len(tld) < 2 or not tld.isalpha():
        raise ValueError('Enter a valid domain name.')

    return ascii_host


def strip_www(host):
    if host.startswith('www.'):
        return host[4:]
    return host


def host_key(host):
    """Canonical cache key for a host (non-www)."""
    return strip_www(normalize_domain(host) or (host or '').lower())