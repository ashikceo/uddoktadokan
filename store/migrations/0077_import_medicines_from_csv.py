import csv
import re
import os
from decimal import Decimal, InvalidOperation
from django.db import migrations


CSV_PATH = '/home/ashik/Videos/uddoktardokan v 9.7/medicine.csv'


def _parse_pack_count(pack_size):
    """Extract numeric pack count from pack_size string. e.g. "30's pack" -> 30, "1's pack" -> 1, "60ml bot" -> 1"""
    if not pack_size:
        return 1
    m = re.search(r'(\d+)', pack_size)
    if m:
        return int(m.group(1))
    return 1


def forwards(apps, schema_editor):
    MedicineProduct = apps.get_model('store', 'MedicineProduct')
    db_alias = schema_editor.connection.alias

    # Clear old medicines
    MedicineProduct.objects.using(db_alias).all().delete()

    batch = []
    sku_num = 1
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = (row.get('brand_name') or '').strip()
            if not brand:
                continue
            generic = (row.get('generic_name') or '').strip()
            strength = (row.get('strength') or '').strip()
            dosage = (row.get('dosage_form') or '').strip()
            manufacturer = (row.get('manufacturer') or '').strip()
            pack_size = (row.get('pack_size') or '').strip()
            price_raw = (row.get('price_bdt') or '0').strip().replace(',', '')

            try:
                unit_price = Decimal(price_raw)
            except InvalidOperation:
                unit_price = Decimal('0')

            pack_count = _parse_pack_count(pack_size)
            pack_price = (unit_price * pack_count).quantize(Decimal('0.01')) if pack_count > 1 else unit_price

            sku = f'MED-{sku_num:05d}'
            sku_num += 1

            batch.append(MedicineProduct(
                brand_name=brand,
                generic_name=generic,
                strength=strength,
                dosage_form=dosage,
                manufacturer=manufacturer,
                pack_size=pack_size,
                sku=sku,
                price=unit_price,
                pack_price=pack_price,
                stock=1,
                description='',
                is_approved=True,
            ))
            if len(batch) >= 2000:
                MedicineProduct.objects.using(db_alias).bulk_create(batch)
                batch = []

    if batch:
        MedicineProduct.objects.using(db_alias).bulk_create(batch)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0076_medicineproduct_manufacturer_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
