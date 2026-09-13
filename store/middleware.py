"""Django middleware for custom domain routing.

Two responsibilities:

1. **Host validation** — only the platform hosts plus domains that map to an
   ACTIVE custom domain may serve content. Everything else is rejected with a
   400 (``DisallowedHost``), preventing Host-header attacks and domain
   spoofing even though ``ALLOWED_HOSTS`` contains ``*`` (the wildcard is
   never actually permissive — this middleware is the gatekeeper).

2. **Routing** — when a request arrives on a live custom domain it attaches:

       request.is_custom_domain  -> True
       request.custom_domain     -> the CustomDomain row
       request.custom_store      -> the Partner (seller/partner/dealer store)

   It also:
       * redirects ``www.mystore.com`` -> ``mystore.com`` (canonical, no loop)
       * renders the connected store at the domain root ``/``
       * returns 404 for marketplace-wide pages on a custom domain
         (``/shop/``, ``/category/``, ``/search/``, ``/blog/`` …), keeping the
         custom domain exclusively for its own store.
"""
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseNotFound, HttpResponsePermanentRedirect

from .domain_utils import host_key
from .services import custom_domain as custom_domain_service

# Marketplace paths that must NOT be served on a store's custom domain.
_MARKETPLACE_PREFIXES = (
    '/shop',       # /shop/ + /shop_grid/
    '/shop_grid/',
    '/category/',
    '/search',
    '/blog',
    '/landing/',
    '/page/',
    '/contact/',
    '/partners/',
    '/sellers',
    '/dealers',
    '/union_list',
    '/sitemap.xml',
)

# Paths that must keep working on a custom domain (store, product, checkout…).
_ALLOWED_CUSTOM_PREFIXES = (
    '/',
    '/cart',
    '/checkout',
    '/apply-coupon/',
    '/order-confirmation/',
    '/order/',
    '/payment/',
    '/wishlist/',
    '/compare/',
    '/quick-view/',
    '/product/',
    '/partner/',
    '/accounts/',
    '/login',
    '/register',
    '/logout',
    '/password-reset/',
    '/dashboard/',
    '/robots.txt',
    '/favicon.ico',
)


def _host_only(value):
    value = (value or '').strip().lower()
    if not value:
        return ''
    if value.startswith('['):  # IPv6 literal
        end = value.find(']')
        return value[:end + 1] if end != -1 else value
    return value.split(':', 1)[0]


def _platform_hosts():
    hosts = set()
    cfg = getattr(settings, 'PLATFORM_DOMAIN', '')
    if cfg:
        hosts.add(cfg)
    for h in getattr(settings, 'ALLOWED_HOSTS', []):
        if h == '*':
            continue
        h = _host_only(h)
        if h:
            hosts.add(h)
    return hosts


def _is_custom_path_allowed(path):
    if path.startswith(_MARKETPLACE_PREFIXES):
        return False
    return path.startswith(_ALLOWED_CUSTOM_PREFIXES)


class CustomDomainRoutingMiddleware:
    """Resolve the request host to a connected custom-domain store."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'CUSTOM_DOMAIN_ENABLED', True):
            return self.get_response(request)

        host = _host_only(request.META.get('HTTP_HOST', ''))
        if not host:
            host = _host_only(request.get_host())

        platform_hosts = _platform_hosts()
        if host in platform_hosts:
            return self.get_response(request)

        store = custom_domain_service.get_store_for_host(host)

        if not store:
            # Unknown host — block before anything can use it.
            raise DisallowedHost('Invalid HTTP_HOST header: {}'
                                 .format(request.META.get('HTTP_HOST', '')))

        row = getattr(request, 'custom_domain', None)
        if row is None:
            from .models import CustomDomain
            row = CustomDomain.objects.filter(
                normalized_domain=host_key(host), is_active=True, status='active',
            ).first()
        request.is_custom_domain = True
        request.custom_store = store
        request.custom_domain = row

        # Canonical host handling: www.mystore.com -> mystore.com (no loop).
        canonical = host_key(host)
        if host != canonical:
            if request.method in ('GET', 'HEAD'):
                url = '{scheme}://{host}{path}'.format(
                    scheme='https' if request.is_secure() else 'http',
                    host=canonical,
                    path=request.get_full_path(),
                )
                return HttpResponsePermanentRedirect(url)

        # Serve the connected store directly at the domain root.
        if request.path == '/':
            from .views import partner_detail as partner_detail_view
            return partner_detail_view(request, store.slug)

        if not _is_custom_path_allowed(request.path):
            return HttpResponseNotFound()

        return self.get_response(request)