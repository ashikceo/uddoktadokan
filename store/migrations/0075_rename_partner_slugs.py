import re
from django.db import migrations


def new_slug(text):
    """generate_partner_slug: take text before 'Upazila', lowercase, remove hyphens, append 'uddoktardokan'."""
    text = text.strip()
    match = re.split(r'-?[Uu]pazila', text, maxsplit=1)
    base = match[0].replace('-', '').replace(' ', '').replace(',', '').replace('.', '').replace("'", '')
    if not base:
        base = text.replace('-', '').replace(' ', '').replace(',', '').replace('.', '').replace("'", '')
    base = base.lower()
    return f'{base}uddoktardokan'


def forwards(apps, schema_editor):
    Partner = apps.get_model('store', 'Partner')
    used = set()
    for p in Partner.objects.all().order_by('id'):
        slug = new_slug(p.name)
        if slug in used:
            suffix = 1
            while f'{slug}-{suffix}' in used:
                suffix += 1
            slug = f'{slug}-{suffix}'
        used.add(slug)
        Partner.objects.filter(pk=p.pk).update(slug=slug)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0074_partner_domain_name'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
