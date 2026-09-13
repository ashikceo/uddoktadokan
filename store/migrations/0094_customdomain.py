from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0093_shopsliderconfig_delete_shopslidersettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomDomain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(help_text='e.g. mystore.com', max_length=253, verbose_name='Custom Domain')),
                ('normalized_domain', models.CharField(db_index=True, editable=False, max_length=253, unique=True)),
                ('account_type', models.CharField(blank=True, choices=[('SELLER', 'Seller'), ('PARTNER', 'Partner'), ('DEALER', 'Dealer')], default='PARTNER', max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('dns_verified', 'DNS Verified'), ('ssl_provisioning', 'SSL Provisioning'), ('active', 'Active'), ('failed', 'Failed'), ('disconnected', 'Disconnected')], db_index=True, default='pending', max_length=20)),
                ('dns_status', models.CharField(choices=[('pending', 'Waiting for DNS'), ('connected', 'Connected'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('ssl_status', models.CharField(choices=[('waiting', 'Waiting'), ('provisioning', 'Provisioning'), ('active', 'Active'), ('failed', 'Failed'), ('not_configured', 'Not Configured')], default='waiting', max_length=20)),
                ('is_active', models.BooleanField(default=False, help_text='When ON, requests to this domain are routed to the connected store.', verbose_name='Active')),
                ('is_primary', models.BooleanField(default=False, verbose_name='Primary domain')),
                ('verification_method', models.CharField(default='dns', editable=False, max_length=20)),
                ('dns_verified_at', models.DateTimeField(blank=True, null=True)),
                ('ssl_issued_at', models.DateTimeField(blank=True, null=True)),
                ('ssl_expires_at', models.DateTimeField(blank=True, null=True)),
                ('last_dns_check', models.DateTimeField(blank=True, null=True)),
                ('last_ssl_check', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_domains', to='store.partner', verbose_name='Store / Account')),
            ],
            options={
                'verbose_name': 'Custom Domain',
                'verbose_name_plural': 'Custom Domains',
                'ordering': ['-is_primary', '-created_at'],
            },
        ),
    ]