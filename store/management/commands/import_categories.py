import json
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import Category


class Command(BaseCommand):
    help = 'Import the Daraz-style category hierarchy from categories.json.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', help='Path to categories.json')
        parser.add_argument('--max-depth', type=int, default=3,
                            help='Maximum nesting depth to import (default: 3)')

    def handle(self, *args, **options):
        json_path = options['json_path']
        max_depth = options['max_depth']

        try:
            with open(json_path, encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise CommandError(f'Could not read JSON file: {exc}')

        categories = data.get('categories') if isinstance(data, dict) else data
        if not isinstance(categories, list):
            raise CommandError('JSON must contain a "categories" list (or be a bare list).')

        counts = Counter()
        with transaction.atomic():
            self._recurse(categories, None, 0, max_depth, counts)

        self.stdout.write(self.style.SUCCESS(
            f'Done. created={counts["created"]} existing={counts["existing"]} '
            f'updated={counts["updated"]} total={counts["total"]}'))

    def _recurse(self, items, parent, depth, max_depth, counts):
        for index, item in enumerate(items):
            name, children = self._parse_entry(item)
            obj, created = Category.objects.get_or_create(
                name=name, parent=parent,
                defaults={'is_active': True, 'sort_order': index},
            )
            counts['total'] += 1
            if created:
                counts['created'] += 1
            else:
                counts['existing'] += 1
                changed = []
                if obj.parent_id != (parent.id if parent else None):
                    obj.parent = parent
                    changed.append('parent')
                if not obj.is_active:
                    obj.is_active = True
                    changed.append('is_active')
                if obj.sort_order != index:
                    obj.sort_order = index
                    changed.append('sort_order')
                if changed:
                    counts['updated'] += 1
                    obj.save(update_fields=changed + ['updated_at'])

            if depth < max_depth and children:
                self._recurse(children, obj, depth + 1, max_depth, counts)

    @staticmethod
    def _parse_entry(entry):
        if isinstance(entry, dict):
            name = (entry.get('name') or '').strip()
            children = entry.get('children') or []
        else:
            name = str(entry).strip()
            children = []
        if not name:
            raise CommandError(f'Empty category name found: {entry!r}')
        return name, children