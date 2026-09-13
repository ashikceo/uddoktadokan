# Uddoktar Dokan

A full-featured multi-seller e-commerce platform (Bengali marketplace) built with **Django 6**, featuring a customer storefront, seller dashboard, custom-domain support, wallet & payments, POS terminals, a medicine inventory module, and a mobile-first (Daraz-style) responsive UI.

## Features

### Storefront
- Homepage built from site settings: hero slider, B2B/B2C buttons, product tabs (All / New / Discounted / Hot), partner product sections, blog marquee + YouTube video, promo cards, brand marquee and banner strips — all toggleable from the admin
- Advanced shop / category grid with filters, sorting, labels and sidebar categories
- Product detail pages with gallery, color/size variants, reviews, Q&A, related products, and social sharing
- Search, wishlist (guest-friendly), compare, cart with coupon support, and checkout (COD, SSLCommerz)
- Blog, campaigns (promo cards), discount cards, return/refund, terms, and contact pages
- Fully responsive Daraz-style mobile UI: sticky mobile header + search, bottom navigation bar, 2-column mobile product grids, mobile filter drawer, sticky product CTA bar and card-based cart (desktop design is untouched)

### Seller dashboard
- Seller registration / store front per partner (slug-based partner stores)
- Product management with bulk upload, categories, attributes, stock + low-stock alerts, reviews & Q&A moderation
- Order management with delivery-status workflow (picked up → in transit → delivered) and custom orders
- Profit analytics (revenue / cost / commission / net profit / margin), wallet with recharge & withdrawals
- Store visibility toggles (slider, all-products section, random products, etc.), custom menus, side banners
- Support tickets and seller–customer messaging
- **Custom domain system**: point your own domain at your store. ACME (Let’s Encrypt) certificate provisioning, DNS verification helpers, `check_custom_domains` + `provision_custom_domain_ssl` management commands. See [`docs/custom_domains.md`](docs/custom_domains.md)

### POS & medicine module
- POS terminal for in-store sales with order history
- Medicine POS with inventory, batch/expiry adjustments, inventory log and subscriber billing (free 60-day trial, then subscription)

### Platform / admin
- Django admin with 80+ configured models, one-page storefront control, drag-style nav menus (desktop vs mobile visibility)
- Celery + Redis background tasks (abandoned-cart checks, expired-trial/subscription cleanup, custom-domain checks & certificate renewal)
- Google/Facebook social login (django-allauth), rate-limited auth endpoints, media uploads + WeasyPrint PDF export
- Refer to [`ADMIN_GUIDE.md`](ADMIN_GUIDE.md) for a full admin walkthrough

## Tech stack

| Layer | Tech |
|---|----|
| Backend | Python 3.12 · Django 6.0 · DRF · Celery · Redis |
| DB | SQLite (dev) / PostgreSQL (prod, via `DATABASE_URL`) |
| Frontend | Bootstrap, jQuery, Owl Carousel, Nivo Slider, FlexSlider, meanmenu (responsive) |
| Payments | SSLCommerz (Bangladesh), Cash on Delivery, wallet |
| Infra | Gunicorn + WhiteNoise, Docker / Docker Compose, Nginx, Let’s Encrypt |

## Getting started (local development)

Requirements: **Python 3.12+**, optionally Redis.

```bash
git clone https://github.com/ashikceo/uddoktadokan.git
cd uddoktadokan

python -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env        # then edit with your values
venv/bin/python manage.py migrate
venv/bin/python seed.py     # optional: admin user + demo categories
venv/bin/python manage.py createsuperuser

venv/bin/python manage.py runserver 0.0.0.0:8000
```

Open http://127.0.0.1:8000 (customer store) and http://127.0.0.1:8000/admin (Django admin).

> **Note on environments:** `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` and all payment/email credentials are read from environment variables (`.env`). Never commit a real `.env`.

### Redis / Celery (optional)

```bash
redis-server
venv/bin/python -m celery -A config worker -l info
```

Background tasks (abandoned carts, custom-domain certificate checks, subscription expiry, etc.) are configured as Celery beat tasks in `config/settings.py`.

## Docker

```bash
# docker-compose.yml -> web + celery + redis + nginx + postgres
docker compose up -d --build

# compose.yaml     -> optional Defang cloud deployment
```

## Management commands

| Command | Purpose |
|---|---|
| `manage.py check_custom_domains` | Verify custom-domain DNS records & publish ACME orders |
| `manage.py provision_custom_domain_ssl` | Request/renew Let’s Encrypt certificates for custom domains |
| `manage.py import_categories` | Import category tree from a CSV |
| `manage.py migrate_medicine_products` | Migrate/seed medicine products from CSV into the inventory |

## Tests

```bash
venv/bin/python manage.py test store store/tests_custom_domain.py
```

## Project structure

```
config/            Django settings/urls/wsgi/celery
store/             main app: models, views, urls, migrations, middleware,
                   services (custom-domain/ACME/DNS), templatetags,
                   management commands, admin
templates/         base + store templates (admin overrides too)
static/            static assets (fonten_app theme + custom mobile CSS layer)
media/             user uploads
staticfiles/       collectstatic output (generated)
docs/              custom-domain guide
nginx/             Nginx site config
```

## Documentation

- [Admin use guide](ADMIN_GUIDE.md) — manage every section from the admin
- [Custom domain setup](docs/custom_domains.md) — point a custom domain at a store

## License

This is a production marketplace project. See repo history / author for licensing details; all images and third-party assets belong to their respective owners.