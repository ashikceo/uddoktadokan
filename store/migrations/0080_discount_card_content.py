from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0079_populate_medicine_inventory'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscountCardContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=300)),
                ('content', models.TextField(blank=True, help_text='Main body text/HTML for the discount card page')),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Discount Card Content',
                'verbose_name_plural': 'Discount Card Contents',
                'ordering': ['sort_order', '-created'],
            },
        ),
    ]
