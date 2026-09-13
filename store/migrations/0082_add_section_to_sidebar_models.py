from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0081_add_medicine_inventory_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopsidebarslider',
            name='section',
            field=models.CharField(blank=True, default='', help_text='Which section this slider appears in. Leave blank for all sections.', max_length=30),
        ),
        migrations.AddField(
            model_name='shopsidebarbottombanner',
            name='section',
            field=models.CharField(blank=True, default='', help_text='Which section this banner appears in. Leave blank for all sections.', max_length=30),
        ),
    ]
