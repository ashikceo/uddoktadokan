# Automated Custom Domain System

Shop owners (sellers, partners and dealers all use the same `Partner` record)
can connect a domain they own and the platform will automatically:

1. **Validate** the domain (punycoded + hostname rules, no IPs, no reserved names),
2. **Check DNS** until an `A`/`AAAA`/`CNAME` matches this server,
3. **Issue a Let's Encrypt certificate** via the `certbot` CLI (webroot challenge),
4. **Route** the domain to that owner's store so visitors see the store at
   `https://their-own-domain` with the domain kept in the address bar,
5. **Renew** certificates automatically.

One domain can be *primary/live* per store at a time. Activating a new domain
automatically demotes the previous one. Marketplace pages (`/shop/`,
`/category/`, `/search/`, `/blog/`, `/partners/`, `/sellers/`, `/dealers/`,
`/contact/`, ...) intentionally return **404** on a custom domain so the custom
domain stays exclusively the store's own shopfront.

## Highlights

- **No per-domain nginx config needed.** One catch-all `default_server` block
  (see below) serves every domain using SNI (`$ssl_server_name`) to pick the
  certificate issued for that exact domain.
- **Background automation.** Celery beat runs every
  `CUSTOM_DOMAIN_CHECK_MINUTES` (default 5); if Celery beat is not used, a
  cron job running `manage.py check_custom_domains` every 5 minutes has the
  same effect.
- **Safety.** Unknown hosts (any host that isn't the platform or an active
  custom domain) are rejected with HTTP 400 by
  `store.middleware.CustomDomainRoutingMiddleware`, even though
  `ALLOWED_HOSTS` contains `*`. DNS lookups only accept **public** addresses,
  preventing SSRF/internal-network pivots.
- **Owner dashboards.** The "Custom Domain" card (and its management page at
  `/dashboard/custom-domain/`) is visible to every partner with a store
  (Seller / Partner / Dealer), and shows the live status, lets the owner add /
  re-check / disconnect domains and switch the live (primary) domain.

## Components

| Component | File |
|---|---|
| Normalization + validation | `store/domain_utils.py` |
| Routing + host validation middleware | `store/middleware.py` |
| DNS checks (dnspython) | `store/services/dns_verification.py` |
| certbot/ACME provisioning | `store/services/acme.py` |
| Lifecycle orchestration | `store/services/custom_domain.py` |
| Owner dashboard page | `store/views.py::dashboard_custom_domain` + `templates/store/dashboard_custom_domain.html` |
| Background tasks | `store/tasks.py` (`check_custom_domains_task`, `renew_custom_domain_certificates`) |
| Management commands | `manage.py check_custom_domains`, `manage.py provision_custom_domain_ssl` |

## Settings / Environment variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `PLATFORM_DOMAIN` | `uddoktardokan.com` | The platform's canonical domain, used as the CNAME target and for DNS matching |
| `SERVER_IP` | *(empty)* | Public IP of the server, shown to owners and matched against `A` records |
| `CUSTOM_DOMAIN_ENABLED` | `True` | Master switch; when `False` no custom domain is served or provisioned |
| `CUSTOM_DOMAIN_ALLOW_INTERNAL` | `False` | Allow IANA-reserved names (`*.test`, `*.localhost`) — development only |
| `ACME_EMAIL` (alias `SSL_EMAIL`) | *(empty)* | Contact e-mail passed to Let's Encrypt |
| `ACME_DIRECTORY_URL` | *(empty)* | Optional ACME directory override (testing only) |
| `SSL_WEBROOT` | `<project>/ssl_webroot` | Webroot for the HTTP-01 challenge |
| `CUSTOM_DOMAIN_CHECK_MINUTES` | `5` | How often Celery beat verifies DNS / provisions SSL |
| `CUSTOM_DOMAIN_RENEW_DAYS` | `30` | Renew certificates expiring within this many days |

## One-time server setup (manual — cannot be done from Django)

```bash
# 1. Install certbot (always required for production SSL)
apt-get install -y certbot   # or: dnf install certbot; pacman -S certbot

# 2. Option A — adopt the catch-all nginx config (recommended)
#    Copy nginx/nginx.conf into your site config so that:
#      - port 80 has a default_server that serves /.well-known/acme-challenge/
#        from /var/www/letsencrypt (webroot), and proxies everything else,
#      - port 443 has a default_server whose cert paths use
#        /etc/letsencrypt/live/$ssl_server_name/{fullchain,privkey}.pem.
#    Then point your platform cert at the default_server (or let
#    `certbot --nginx` manage the main site).
#
#    Option B — certbot --nginx (alternative): lets certbot write its own
#    per-domain server blocks; this also works but creates a config per domain.

# 3. Prepare the webroot (must exist for --webroot challenges)
mkdir -p /var/www/letsencrypt/.well-known/acme-challenge
chown -R www-data:www-data /var/www/letsencrypt   # or your web user

# 4. Set env vars in Django (see table above), then reload the app

# 5. Background processing — pick ONE of:
#    a) Celery (recommended): run worker + beat as you already do; beat calls
#       store.tasks.check_custom_domains_task every 5 minutes and
#       store.tasks.renew_custom_domain_certificates daily (already scheduled).
#    b) Cron fallback (no Celery beat):
cd "<project>/website"
*/5 * * * * "<venv>/bin/python" manage.py check_custom_domains --limit 200

# 6. (Optional, recommended) certbot auto-renewal as a safety net
echo "0 3 * * * certbot renew --quiet" > /etc/cron.d/certbot-renew

# 7. Firewall / security group: allow ports 80 and 443 (and the DNS records
#    for every custom domain must point at this server before activation).
```

> The webroot directory above must be the same path as `SSL_WEBROOT` so Django
> and nginx agree on where the HTTP-01 challenge files live.

## Forwards / testing in development

- With `CUSTOM_DOMAIN_ALLOW_INTERNAL=True` domains like `shop.local.test` are
  accepted; point them at `127.0.0.1` in `/etc/hosts` and use a fake resolver or
  the `CUSTOM_DOMAIN_DEV_DNS` hook if you add one.
- `DNS` tests in CI never hit the network — see `store/tests_custom_domain.py`.
- `manage.py check_custom_domains --domain <x>` processes a single domain.

## Renaming / edge cases

- **www** is a 301 redirect to the naked domain (no loop; canonical host only).
- Activating a store on a domain invalidates the routing cache immediately
  (helper functions signal-based cache invalidation on every `CustomDomain`
  save/delete).
- Disconnecting keeps the domain row (`status=disconnected`) for history; the
  cache is invalidated automatically.