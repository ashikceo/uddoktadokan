import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import migrations


NAV_ITEMS = [
    ('Home', 'home', True, True),
    ('Product', 'shop_grid', True, True),
    ('Upazila Partner', 'partner_list', True, True),
    ('UNION PARTNER', 'union_list', True, True),
    ('Dealer', 'dealer_list', True, True),
    ('Seller', 'seller_list', True, True),
    ('Discount Card', 'discount_card', True, True),
    ('Blog', 'blog_list', False, True),
]

PROMO_CARDS = [
    ('Buy 2 items', 'Get one for free!', 'fa fa-gift', ''),
    ('Daily Sales', 'Today up to 45% off!', 'fa fa-bolt', ''),
    ('NEW ARRIVAL', 'Sale up to 75% off', 'fa fa-star', ''),
    ('UpTo 45% off', 'Your first purchase', 'fa fa-tags', ''),
]

BRAND_FILES = [
    ('brand1.png', 'Brand 1'),
    ('brand2.png', 'Brand 2'),
    ('brand3.png', 'Brand 3'),
    ('brand4.png', 'Brand 4'),
    ('brand5.png', 'Brand 5'),
    ('brand6.png', 'Brand 6'),
    ('brand7.png', 'Brand 7'),
]


def seed_data(apps, schema_editor):
    NavMenu = apps.get_model('store', 'NavMenu')
    HomepageSettings = apps.get_model('store', 'HomepageSettings')
    PromoCard = apps.get_model('store', 'PromoCard')
    BrandLogo = apps.get_model('store', 'BrandLogo')

    NavMenu.objects.all().delete()
    for order, (title, url_name, desktop, mobile) in enumerate(NAV_ITEMS):
        NavMenu.objects.create(
            title=title,
            url=url_name,
            url_type='named_url',
            order=order,
            is_active=True,
            show_desktop=desktop,
            show_mobile=mobile,
            login_required=False,
            logout_required=False,
        )

    if not HomepageSettings.objects.exists():
        HomepageSettings.objects.create()

    for order, (title, description, icon, link) in enumerate(PROMO_CARDS):
        PromoCard.objects.create(title=title, description=description, icon=icon, link=link, order=order, is_active=True)

    if not BrandLogo.objects.exists():
        for order, (filename, name) in enumerate(BRAND_FILES):
            source = settings.BASE_DIR / 'staticfiles' / 'fonten_app' / 'images' / filename
            if not os.path.exists(source):
                continue
            with open(source, 'rb') as f:
                logo = BrandLogo.objects.create(name=name, order=order, is_active=True)
                logo.image.save(filename.replace('-', '_'), ContentFile(f.read()), save=True)


def unseed_data(apps, schema_editor):
    NavMenu = apps.get_model('store', 'NavMenu')
    HomepageSettings = apps.get_model('store', 'HomepageSettings')
    PromoCard = apps.get_model('store', 'PromoCard')
    BrandLogo = apps.get_model('store', 'BrandLogo')
    NavMenu.objects.all().delete()
    BrandLogo.objects.all().delete()
    PromoCard.objects.all().delete()
    HomepageSettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0088_navmenu_desktop_mobile'),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]