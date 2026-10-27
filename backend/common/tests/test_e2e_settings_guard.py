import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


class E2ESettingsGuardTests(SimpleTestCase):
    def setUp(self):
        self.temp_context = tempfile.TemporaryDirectory(prefix='farm-copilot-e2e-guard-')
        self.temp_root = Path(self.temp_context.name)
        self.e2e_root = self.temp_root
        (self.e2e_root / '.farm-copilot-e2e-root').write_text(
            'isolated-local-e2e\n', encoding='utf-8'
        )
        (self.e2e_root / 'db').mkdir()
        (self.e2e_root / 'media').mkdir()
        (self.e2e_root / 'private_media').mkdir()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                'DJANGO_SECRET_KEY': 'guard-test-placeholder',
                'DJANGO_USE_SQLITE': '1',
                'SQLITE_DATABASE_PATH': str(self.temp_root.parent / 'development.sqlite3'),
                'DJANGO_ALLOWED_HOSTS': '127.0.0.1,localhost',
                'FARM_COPILOT_E2E_MODE': '1',
                'FARM_COPILOT_E2E_ROOT': str(self.e2e_root),
            }
        )
        self.environment.pop('DJANGO_SETTINGS_MODULE', None)

    def tearDown(self):
        self.temp_context.cleanup()

    def _load_settings(self, environment=None):
        return subprocess.run(
            [
                sys.executable,
                '-c',
                'from django.conf import settings; '
                "print(settings.DATABASES['default']['NAME']); "
                'print(settings.MEDIA_ROOT); '
                'print(settings.DETECTION_IMAGE_ROOT); '
                'print(settings.DEBUG, settings.USE_S3, settings.CHATBOT_ENABLED, '
                'settings.EMAIL_BACKEND, settings.SESSION_COOKIE_SECURE, '
                'settings.CSRF_COOKIE_SECURE, settings.ALLOWED_HOSTS, '
                'settings.CORS_ALLOWED_ORIGINS, settings.CSRF_TRUSTED_ORIGINS)',
            ],
            cwd=Path(__file__).resolve().parents[2],
            env={
                **(environment or self.environment),
                'DJANGO_SETTINGS_MODULE': 'config.e2e_settings',
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def test_valid_fresh_root_uses_isolated_database_and_both_media_roots(self):
        result = self._load_settings()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines()[:3],
            [
                str(self.e2e_root / 'db' / 'e2e.sqlite3'),
                str(self.e2e_root / 'media'),
                str(self.e2e_root / 'private_media'),
            ],
        )
        self.assertEqual(
            result.stdout.splitlines()[3],
            'True False False django.core.mail.backends.console.EmailBackend False False '
            "['127.0.0.1', 'localhost'] ['http://localhost:3000'] "
            "['http://localhost:3000']",
        )

    def test_missing_mode_root_or_marker_fails_closed(self):
        scenarios = (
            ({'FARM_COPILOT_E2E_MODE': None}, 'FARM_COPILOT_E2E_MODE=1'),
            ({'FARM_COPILOT_E2E_ROOT': None}, 'FARM_COPILOT_E2E_ROOT'),
            (
                {'FARM_COPILOT_E2E_ROOT': str(self.temp_root.parent / 'farm-copilot-e2e-missing')},
                'marker',
            ),
        )
        for overrides, expected_message in scenarios:
            with self.subTest(expected_message=expected_message):
                environment = self.environment.copy()
                for name, value in overrides.items():
                    if value is None:
                        environment.pop(name, None)
                    else:
                        environment[name] = value
                result = self._load_settings(environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_message, result.stderr)

    def test_repository_root_and_populated_root_are_rejected(self):
        repo_root = Path(__file__).resolve().parents[2].parent
        scenarios = (
            (repo_root / 'farm-copilot-e2e-invalid', 'outside the repository'),
            (self.e2e_root, 'real, empty directories'),
        )
        (self.e2e_root / 'media' / 'keep.txt').write_text('preserve', encoding='utf-8')
        for root, expected_message in scenarios:
            with self.subTest(root=root):
                self.environment['FARM_COPILOT_E2E_ROOT'] = str(root)
                result = self._load_settings()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_message, result.stderr)

    def test_development_database_collision_is_rejected(self):
        self.environment['FARM_COPILOT_E2E_ROOT'] = str(self.e2e_root)
        self.environment['SQLITE_DATABASE_PATH'] = str(self.e2e_root / 'db' / 'e2e.sqlite3')
        result = self._load_settings()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('differ from the configured development database', result.stderr)
