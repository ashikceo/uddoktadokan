from django.db import migrations


def seed_nav_kinds(apps, schema_editor):
    NavMenu = apps.get_model('store', 'NavMenu')
    for item in NavMenu.objects.all().order_by('-order'):
        item.order += 1
        item.save(update_fields=['order'])
    NavMenu.objects.create(
        title='Categories',
        kind='categories',
        url='shop',
        url_type='named_url',
        order=0,
        is_active=True,
        show_desktop=True,
        show_mobile=True,
        login_required=False,
        logout_required=False,
    )
    max_order = NavMenu.objects.order_by('-order').values_list('order', flat=True).first() or 0
    NavMenu.objects.create(
        title='Account',
        kind='account',
        url='dashboard',
        url_type='named_url',
        order=max_order + 1,
        is_active=True,
        show_desktop=True,
        show_mobile=True,
        login_required=False,
        logout_required=False,
    )


def unseed_nav_kinds(apps, schema_editor):
    NavMenu = apps.get_model('store', 'NavMenu')
    NavMenu.objects.filter(kind__in=['categories', 'account']).delete()
    for item in NavMenu.objects.filter(kind='link').order_by('order'):
        if item.order > 0:
            item.order -= 1
            item.save(update_fields=['order'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0091_navmenu_kind_navmenu_open_new_tab_alter_navmenu_url'),
    ]

    operations = [
        migrations.RunPython(seed_nav_kinds, unseed_nav_kinds),
    ]