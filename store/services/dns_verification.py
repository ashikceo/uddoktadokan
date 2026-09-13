"""DNS resolution for custom domains.

Performs real DNS lookups (A/AAAA + CNAME) and confirms the domain points at
this platform before the domain is allowed to go live. Every resolved address
is checked to be a public IP to prevent SSRF / internal-network pivots.

No user input is ever trusted — the domain has already been validated by
``store.domain_utils.validate_domain`` before arriving here.
"""
import ipaddress
import logging
import socket

import dns.resolver

logger = logging.getLogger('store.custom_domains')

RESOLVER_TIMEOUT = 5.0
RESOLVER_LIFETIME = 6.0


def _resolver():
    return dns.resolver.Resolver(configure=True)


def _is_public_ip(ip_str):
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_multicast or addr.is_reserved or addr.is_unspecified)


def _resolve_a(domain):
    ips = set()
    try:
        answers = _resolver().resolve(_strip_trailing(domain), 'A', lifetime=RESOLVER_LIFETIME)
        for ans in answers:
            ips.add(str(ans.address))
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers,
            dns.resolver.LifetimeTimeout, dns.exception.DNSException):
        pass
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug('A lookup failed for %s: %s', domain, exc)
    return ips


def _resolve_aaaa(domain):
    ips = set()
    try:
        answers = _resolver().resolve(_strip_trailing(domain), 'AAAA', lifetime=RESOLVER_LIFETIME)
        for ans in answers:
            ips.add(str(ans.address))
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers,
            dns.resolver.LifetimeTimeout, dns.exception.DNSException):
        pass
    except Exception as exc:  # pragma: no cover
        logger.debug('AAAA lookup failed for %s: %s', domain, exc)
    return ips


def _resolve_cname(domain):
    """Return the raw CNAME target (Apex may use ALIAS; www usually uses CNAME)."""
    try:
        answers = _resolver().resolve(_strip_trailing(domain), 'CNAME', lifetime=RESOLVER_LIFETIME)
        for ans in answers:
            return str(ans.target).rstrip('.')
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers,
            dns.resolver.LifetimeTimeout, dns.exception.DNSException):
        return None
    except Exception as exc:  # pragma: no cover
        logger.debug('CNAME lookup failed for %s: %s', domain, exc)
    return None


def _strip_trailing(domain):
    return domain.rstrip('.')


def _cname_resolves_to_platform(domain, platform_domain):
    """Resolve the CNAME chain and confirm the final A record equals platform A."""
    target = _resolve_cname(domain)
    if not target:
        return False
    # Follow the whole chain (bounded).
    for _ in range(5):
        next_target = _resolve_cname(target)
        if not next_target:
            break
        target = next_target
    target = _strip_trailing(target)
    if target == _strip_trailing(platform_domain):
        return True
    target_ips = _resolve_a(target) | _resolve_aaaa(target)
    platform_ips = _resolve_a(platform_domain) | _resolve_aaaa(platform_domain)
    return bool(target_ips & platform_ips) and bool(target_ips)


def check_domain_dns(normalized_domain, platform_domain=None, server_ip=None):
    """Check whether *normalized_domain* points to this platform.

    Returns a dict::

        {
            'ok': bool,
            'records': ['A 203.0.113.10', 'CNAME www -> platform.com'],
            'message': 'DNS detected successfully.' | 'DNS is not pointing to our platform yet.',
        }

    Matching rules:
      * an A/AAAA record on the apex (or ``www``) equal to ``server_ip``;
      * the apex A/AAAA records alternately matching the platform domain's A/AAAA;
      * a CNAME chain whose final target equals ``platform_domain`` or resolves
        to the same addresses as the platform domain.
    """
    platform_domain = _strip_trailing((platform_domain or '').lower().strip())
    server_ip = (server_ip or '').strip()

    records = []
    apex_ips = _resolve_a(normalized_domain)
    apex_aaaa = _resolve_aaaa(normalized_domain)
    www = 'www.' + normalized_domain
    www_ips = _resolve_a(www)
    www_aaaa = _resolve_aaaa(www)

    for ip in sorted(apex_ips):
        records.append(f'A {ip}')
    for ip in sorted(apex_aaaa):
        records.append(f'AAAA {ip}')
    for ip in sorted(www_ips):
        records.append(f'A {ip} (www)')
    for ip in sorted(www_aaaa):
        records.append(f'AAAA {ip} (www)')

    # Every listed record must resolve to a public address before proceeding.
    all_ips = apex_ips | apex_aaaa | www_ips | www_aaaa
    if not all_ips:
        return {
            'ok': False,
            'records': records,
            'message': 'No DNS records found yet. DNS is not pointing to our platform.',
        }
    if any(not _is_public_ip(ip) for ip in all_ips):
        return {
            'ok': False,
            'records': records,
            'message': 'The domain resolves to a non-public address and cannot be connected.',
        }

    # 1. Direct IP match.
    if server_ip:
        if server_ip in all_ips:
            return {
                'ok': True,
                'records': records,
                'message': 'DNS detected successfully.',
            }

    # 2. Apex resolves to the same addresses as the platform domain.
    if platform_domain:
        platform_ips = _resolve_a(platform_domain) | _resolve_aaaa(platform_domain)
        if platform_ips and (apex_ips & platform_ips or www_ips & platform_ips):
            return {
                'ok': True,
                'records': records,
                'message': 'DNS detected successfully (matched the platform address).',
            }

    # 3. CNAME points at the platform domain.
    if platform_domain and (_cname_resolves_to_platform(normalized_domain, platform_domain)
                            or _cname_resolves_to_platform(www, platform_domain)):
        return {
            'ok': True,
            'records': records,
            'message': 'DNS detected successfully (CNAME matched the platform).',
        }

    return {
        'ok': False,
        'records': records,
        'message': 'DNS is not pointing to our platform yet.',
    }


def inspect_domain(domain):
    """Lightweight inspector for the status page (best-effort, never raises)."""
    try:
        ip = socket.gethostbyname(domain)
    except Exception:
        ip = None
    return ip