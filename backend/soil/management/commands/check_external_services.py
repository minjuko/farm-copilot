import os
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


SERVICE_ENV = {
    'kakao': ('KAKAO_REST_API_KEY',),
    'soil': ('DATA_GO_KR_SOIL_SERVICE_KEY',),
    'fertilizer': ('DATA_GO_KR_FERTILIZER_V2_SERVICE_KEY',),
    'weather': ('DATA_GO_KR_WEATHER_SERVICE_KEY',),
    'market': ('DATA_GO_KR_MARKET_SERVICE_KEY',),
}
SAMPLE_ADDRESS = '전북특별자치도 전주시 덕진구 농생명로 300'


class Command(BaseCommand):
    help = (
        'Check external-service configuration without printing credentials. '
        'Provider calls run only when explicitly selected with --live.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--live',
            nargs='*',
            choices=tuple(SERVICE_ENV),
            default=[],
            help='Explicit providers to call: kakao soil fertilizer weather market.',
        )

    def handle(self, *args, **options):
        selected = options['live']
        self._print_configuration()
        failures = []
        for service in selected:
            try:
                summary = getattr(self, f'_check_{service}')()
                self.stdout.write(self.style.SUCCESS(f'{service}: ok ({summary})'))
            except Exception as exc:
                failures.append(service)
                self.stderr.write(self.style.ERROR(
                    f'{service}: failed ({exc.__class__.__name__})'
                ))
        if failures:
            raise CommandError(
                f'External service checks failed: {", ".join(failures)}'
            )

    def _print_configuration(self):
        for service, names in SERVICE_ENV.items():
            configured = all(bool(os.getenv(name, '').strip()) for name in names)
            self.stdout.write(f'{service}: {"configured" if configured else "missing"}')
        self.stdout.write(
            f'chatbot: {"enabled" if settings.CHATBOT_ENABLED else "disabled"}'
        )
        self.stdout.write(f'storage: {"s3" if settings.USE_S3 else "local"}')

    @staticmethod
    def _check_kakao():
        from soil.services import find_address_codes

        codes = find_address_codes(SAMPLE_ADDRESS)
        return f'legal district and {len(codes["pnu_code"])}-digit PNU resolved'

    @staticmethod
    def _check_soil():
        from soil.services import fetch_soil_exam, find_legal_district_code

        code = find_legal_district_code(SAMPLE_ADDRESS)
        rows = fetch_soil_exam(code)
        return f'{len(rows)} rows'

    @staticmethod
    def _check_fertilizer():
        from aivle_big.exceptions import NotFoundError
        from soil.services import fetch_fertilizer, fetch_soil_exam, find_address_codes

        address_codes = find_address_codes(SAMPLE_ADDRESS)
        soil_rows = fetch_soil_exam(address_codes['stdg_code'])
        candidates = [row for row in soil_rows if row.get('PNU_Nm')][:5]
        for soil_row in candidates:
            try:
                parcel_codes = find_address_codes(soil_row['PNU_Nm'])
            except NotFoundError:
                continue
            for crop_name in ('고구마', '고추(노지)', '벼'):
                try:
                    rows, _ = fetch_fertilizer(
                        crop_name, soil_row, parcel_codes['pnu_code']
                    )
                    return f'{len(rows)} rows'
                except NotFoundError:
                    continue
        return 'reachable; no rows for bounded sample candidates'

    @staticmethod
    def _check_weather():
        from prediction.views import fetch_weather_data

        rows = fetch_weather_data('서울')
        return f'{len(rows)} rows'

    @staticmethod
    def _check_market():
        from prediction.views import fetch_market_prices

        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=365)
        rows = fetch_market_prices(
            '고구마', '서울', start_date.isoformat(), end_date.isoformat()
        )
        return f'{len(rows)} rows'
