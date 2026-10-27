"""Safely initialize only the canonical pest catalog and YOLO class mappings."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from detect.models import Pest, PestModelClass

FIXTURE_PATH = Path(__file__).resolve().parents[2] / 'fixtures' / 'model_classes.json'
PEST_FIELDS = (
    'code',
    'pest_name',
    'occurrence_environment',
    'symptom_description',
    'prevention_methods',
    'pesticide_name',
    'image_url',
    'information_source',
    'information_source_url',
)


def load_catalog():
    rows = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    pests_by_fixture_pk = {}
    mappings = []
    for row in rows:
        fields = row['fields']
        if row['model'] == 'detect.pest':
            record = {field: fields.get(field) for field in PEST_FIELDS}
            if any(not record[field] for field in PEST_FIELDS):
                raise CommandError(f'Catalog Pest fixture {row["pk"]} has incomplete details.')
            pests_by_fixture_pk[row['pk']] = record
        elif row['model'] == 'detect.pestmodelclass':
            mappings.append(
                {
                    'class_id': fields['class_id'],
                    'model_label': fields['model_label'],
                    'pest_fixture_pk': fields['pest'],
                }
            )
    expected = {
        0: 'PEPPER_ANTHRACNOSE',
        1: 'PEPPER_POWDERY_MILDEW',
        2: 'CUCUMBER_DOWNY_MILDEW',
        3: 'TOMATO_POWDERY_MILDEW',
        4: 'CUCUMBER_DOWNY_MILDEW',
        5: 'CUCUMBER_POWDERY_MILDEW',
    }
    actual = {
        row['class_id']: pests_by_fixture_pk[row['pest_fixture_pk']]['code'] for row in mappings
    }
    if actual != expected or len(pests_by_fixture_pk) != 5:
        raise CommandError('Catalog fixture does not match the six-class service contract.')
    return pests_by_fixture_pk, mappings


class Command(BaseCommand):
    help = 'Create missing canonical pest details and model-class mappings without touching other data.'

    def handle(self, *args, **options):
        pests_by_fixture_pk, mappings = load_catalog()
        created_pests = 0
        created_mappings = 0
        with transaction.atomic():
            existing_pests = {
                pest.code: pest
                for pest in Pest.objects.filter(
                    code__in=[p['code'] for p in pests_by_fixture_pk.values()]
                )
            }
            planned_pests = {}
            conflicts = []
            for record in pests_by_fixture_pk.values():
                pest = existing_pests.get(record['code'])
                if pest is None:
                    planned_pests[record['code']] = None
                    continue
                if any(getattr(pest, field) != record[field] for field in PEST_FIELDS):
                    conflicts.append(
                        f'Pest code {record["code"]} already exists with different details'
                    )
                else:
                    planned_pests[record['code']] = pest

            existing_mappings = {
                mapping.class_id: mapping
                for mapping in PestModelClass.objects.select_related('pest').filter(
                    class_id__in=[row['class_id'] for row in mappings]
                )
            }
            for row in mappings:
                record = pests_by_fixture_pk[row['pest_fixture_pk']]
                mapping = existing_mappings.get(row['class_id'])
                if mapping and (
                    mapping.model_label != row['model_label'] or mapping.pest.code != record['code']
                ):
                    conflicts.append(
                        f'Model class ID {row["class_id"]} is already mapped differently'
                    )
            if conflicts:
                raise CommandError(
                    'Catalog conflicts found; no changes were made. ' + '; '.join(conflicts)
                )

            pests_by_code = dict(existing_pests)
            for record in pests_by_fixture_pk.values():
                if record['code'] not in pests_by_code:
                    pests_by_code[record['code']] = Pest.objects.create(**record)
                    created_pests += 1
            for row in mappings:
                if row['class_id'] in existing_mappings:
                    continue
                record = pests_by_fixture_pk[row['pest_fixture_pk']]
                PestModelClass.objects.create(
                    class_id=row['class_id'],
                    model_label=row['model_label'],
                    pest=pests_by_code[record['code']],
                )
                created_mappings += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Detection catalog ready: {created_pests} Pest and {created_mappings} mappings created; '
                f'{Pest.objects.count()} Pest and {PestModelClass.objects.count()} mappings total.'
            )
        )
