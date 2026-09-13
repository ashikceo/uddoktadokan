import csv
import io
import json
import re
from decimal import Decimal
from celery import shared_task
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.template.loader import render_to_string
from django.db.models import Q
from .models import Order, Contact, Cart, Product, Category, Partner, MedicineSubscription


@shared_task
def send_order_confirmation_email(order_id):
    order = Order.objects.get(id=order_id)
    subject = f'Order Confirmation - #{order.id}'
    html_msg = render_to_string('emails/order_confirmation.html', {'order': order})
    text_msg = f'Dear {order.name},\n\nYour order #{order.id} has been placed successfully.\nTotal: ৳{order.total}\nStatus: {order.get_status_display()}\n\nThank you for shopping with us!'
    send_mail(subject, text_msg, settings.DEFAULT_FROM_EMAIL, [order.user.email], html_message=html_msg)


@shared_task
def send_contact_auto_reply(contact_id):
    contact = Contact.objects.get(id=contact_id)
    subject = 'Thank you for contacting us'
    html_msg = render_to_string('emails/contact_auto_reply.html', {'contact': contact})
    text_msg = f'Dear {contact.name},\n\nWe have received your message and will get back to you shortly.\n\nBest regards,\nUddoktar Dokan'
    send_mail(subject, text_msg, settings.DEFAULT_FROM_EMAIL, [contact.email], html_message=html_msg)


@shared_task
def send_abandoned_cart_reminder(cart_id):
    cart = Cart.objects.get(id=cart_id, is_active=True)
    user = cart.user
    if not user or not user.email:
        return
    items = cart.items.select_related('product').all()[:5]
    subject = 'You left items in your cart!'
    html_msg = render_to_string('emails/abandoned_cart.html', {'cart': cart, 'items': items})
    text_msg = f'Hi {user.username},\n\nYou have {cart.total_items()} items in your cart. Complete your order now!'
    send_mail(subject, text_msg, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_msg)


@shared_task
def cleanup_expired_carts():
    cutoff = timezone.now() - timezone.timedelta(days=7)
    Cart.objects.filter(is_active=True, created__lt=cutoff).update(is_active=False)


@shared_task
def check_abandoned_carts():
    cutoff = timezone.now() - timezone.timedelta(hours=6)
    reminder_cutoff = timezone.now() - timezone.timedelta(hours=24)
    carts = Cart.objects.filter(is_active=True, created__lte=cutoff, abandoned_reminder_sent=False, user__isnull=False)
    for cart in carts:
        send_abandoned_cart_reminder.delay(cart.id)
        cart.abandoned_reminder_sent = True
        cart.save(update_fields=['abandoned_reminder_sent'])


def _parse_medicine_price(text):
    if not text:
        return Decimal('0')
    match = re.search(r'[\u09F3৳]\s*([\d,]+\.?\d*)', str(text))
    if match:
        return Decimal(match.group(1).replace(',', ''))
    match = re.search(r'(\d+\.?\d*)', str(text))
    if match:
        return Decimal(match.group(1))
    return Decimal('0')


def _next_medicine_sku():
    last = Product.objects.filter(sku__startswith='MED-').order_by('sku').last()
    if last and last.sku:
        try:
            num = int(last.sku.replace('MED-', ''))
            return f'MED-{num + 1:05d}'
        except ValueError:
            pass
    return 'MED-10001'


def _get_or_create_category(name):
    if not name:
        return None
    name = name.strip().title()
    slug = slugify(name)[:50]
    cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
    return cat


@shared_task
def process_medicine_csv_chunk(rows_json, partner_id, batch_id, chunk_index):
    partner = Partner.objects.get(id=partner_id)
    rows = json.loads(rows_json)
    created = 0
    errors = []
    sku_prefix = _next_medicine_sku()

    for i, row in enumerate(rows):
        try:
            brand = (row.get('brand name') or row.get('brand_name') or '').strip()
            strength = (row.get('strength') or '').strip()
            dosage = (row.get('dosage form') or row.get('dosage_form') or '').strip()
            generic = (row.get('generic') or '').strip()
            container = (row.get('package container') or row.get('package_container') or row.get('container') or '').strip()

            parts = [p for p in [brand, strength, dosage] if p]
            name = ' '.join(parts) if parts else (row.get('name') or '').strip()
            if not name:
                errors.append(f'Chunk {chunk_index} row {i}: could not build name')
                continue

            price = _parse_medicine_price(container)
            category = _get_or_create_category(dosage)

            # Generate unique SKU
            global_sku = sku_prefix
            while Product.objects.filter(sku=global_sku).exists():
                num = int(global_sku.replace('MED-', ''))
                global_sku = f'MED-{num + 1:05d}'
            sku_prefix = global_sku

            # Store as global catalog (no partner) — admin-managed, shared across medicine shops
            Product.objects.create(
                partner=None,
                name=name,
                sku=sku_prefix,
                category=category,
                price=price,
                old_price=None,
                cost_price=None,
                stock=0,
                available=True,
                medicine_brand_name=brand,
                medicine_generic_name=generic,
                medicine_strength=strength,
                medicine_dosage_form=dosage,
            )
            # Advance SKU for next product
            num = int(sku_prefix.replace('MED-', ''))
            sku_prefix = f'MED-{num + 1:05d}'
            created += 1
        except Exception as e:
            errors.append(f'Chunk {chunk_index} row {i}: {e}')

    # Update progress
    cache_key = f'med_import_{batch_id}'
    current = cache.get(cache_key, {'processed': 0, 'errors': []})
    current['processed'] += len(rows)
    current['errors'].extend(errors)
    cache.set(cache_key, current, 3600)

    return {'created': created, 'errors': len(errors)}


@shared_task
def expire_expired_trials():
    now = timezone.now()
    expired = MedicineSubscription.objects.filter(
        status='trial', trial_ends_at__lte=now
    ).update(status='expired')
    if expired:
        logger = __import__('logging').getLogger(__name__)
        logger.info(f'Expired {expired} medicine trial subscriptions.')
    return f'Expired {expired} subscriptions.'


@shared_task
def expire_expired_active_subscriptions():
    now = timezone.now()
    expired = MedicineSubscription.objects.filter(
        status='active', current_period_end__lte=now
    ).update(status='expired')
    if expired:
        logger = __import__('logging').getLogger(__name__)
        logger.info(f'Expired {expired} medicine active subscriptions.')
    return f'Expired {expired} subscriptions.'


@shared_task
def check_custom_domains_task():
    """Celery beat entry point (every 5 minutes) — advance all pending domains."""
    from .services.custom_domain import check_pending_domains
    summary = check_pending_domains(limit=200)
    if summary.get('activated'):
        logger = __import__('logging').getLogger(__name__)
        logger.info('Custom domain check complete: %s', summary)
    return summary


@shared_task
def renew_custom_domain_certificates():
    """Daily task — renew custom-domain SSL certificates near expiry."""
    from .services.custom_domain import renew_ssl_if_needed
    renewed = renew_ssl_if_needed()
    return {'renewed': renewed}
