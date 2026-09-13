from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0077_import_medicines_from_csv'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicineInventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock', models.IntegerField(default=0, help_text='Current stock count for this partner')),
                ('low_stock_threshold', models.IntegerField(default=5, help_text='Alert when stock falls below this number')),
                ('is_active', models.BooleanField(default=True, help_text='Show this product in Medicine POS')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('partner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medicine_inventory', to='store.partner')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_entries', to='store.medicineproduct')),
            ],
            options={
                'verbose_name': 'Medicine Inventory',
                'verbose_name_plural': 'Medicine Inventories',
                'ordering': ['product__brand_name'],
                'unique_together': {('partner', 'product')},
            },
        ),
        migrations.CreateModel(
            name='MedicineInventoryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adjustment_type', models.CharField(choices=[('sale', 'Sale'), ('refund', 'Refund'), ('stock_in', 'Stock In'), ('stock_out', 'Stock Out'), ('adjustment', 'Manual Adjustment'), ('initial', 'Initial Stock')], max_length=20)),
                ('quantity', models.IntegerField(help_text='Positive for in, negative for out')),
                ('balance_after', models.IntegerField(help_text='Stock count after this change')),
                ('reason', models.CharField(blank=True, max_length=300)),
                ('reference', models.CharField(blank=True, help_text='e.g. order number', max_length=200)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='store.medicineinventory')),
            ],
            options={
                'verbose_name': 'Medicine Inventory Log',
                'verbose_name_plural': 'Medicine Inventory Logs',
                'ordering': ['-created'],
            },
        ),
    ]
