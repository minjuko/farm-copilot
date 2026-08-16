import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import User


class AuthenticationSmokeTests(TestCase):
    def test_signup_session_auth_check_and_logout(self):
        session = self.client.session
        session['verification_code'] = '1234'
        session['verification_code_sent_at'] = timezone.now().timestamp()
        session.save()

        signup_response = self.client.post(
            reverse('login:signup'),
            data=json.dumps({
                'username': 'runtime-user',
                'email': 'runtime@example.com',
                'password1': 'runtime-password-123',
                'password2': 'runtime-password-123',
                'verification_code': '1234',
            }),
            content_type='application/json',
        )
        self.assertEqual(signup_response.status_code, 200)
        self.assertIn('sessionid', signup_response.cookies)
        user = User.objects.get(email='runtime@example.com')
        self.assertNotEqual(user.password, 'runtime-password-123')
        self.assertTrue(user.password.startswith('pbkdf2_'))

        auth_response = self.client.get(reverse('login:auth_check'))
        self.assertEqual(auth_response.status_code, 200)
        self.assertTrue(auth_response.json()['is_authenticated'])

        logout_response = self.client.post(reverse('login:logout'))
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(
            self.client.get(reverse('login:auth_check')).json()['is_authenticated']
        )

    def test_account_deletion_ends_authenticated_session(self):
        user = User.objects.create_user(
            email='delete@example.com',
            username='delete-user',
            password='runtime-password-123',
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('login:delete_account'),
            data=json.dumps({'password': 'runtime-password-123'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.get(reverse('login:auth_check')).json()['is_authenticated'])


class AuthenticationCsrfBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='csrf-login@example.com',
            username='csrf-login-user',
            password='runtime-password-123',
        )
        self.client = Client(enforce_csrf_checks=True)

    def csrf_token(self):
        response = self.client.get(reverse('login:auth_check'))
        return response.cookies['csrftoken'].value

    def test_login_requires_csrf_and_valid_token_allows_login(self):
        without_token = self.client.post(
            reverse('login:login'),
            data=json.dumps({'email': self.user.email, 'password': 'runtime-password-123'}),
            content_type='application/json',
        )
        self.assertEqual(without_token.status_code, 403)

        token = self.csrf_token()
        with_token = self.client.post(
            reverse('login:login'),
            data=json.dumps({'email': self.user.email, 'password': 'runtime-password-123'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(with_token.status_code, 200)

    def test_logout_requires_csrf(self):
        self.client.force_login(self.user)
        without_token = self.client.post(reverse('login:logout'))
        self.assertEqual(without_token.status_code, 403)

        token = self.csrf_token()
        with_token = self.client.post(
            reverse('login:logout'),
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(with_token.status_code, 200)


class RecoverySecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='recovery@example.com',
            username='recovery-user',
            password='runtime-password-123',
        )

    @patch('login.views.send_mail')
    def test_password_reset_does_not_enumerate_accounts(self, send_mail):
        known = self.client.post(
            reverse('login:password_reset_request'),
            data=json.dumps({'email': self.user.email}),
            content_type='application/json',
        )
        unknown = self.client.post(
            reverse('login:password_reset_request'),
            data=json.dumps({'email': 'missing@example.com'}),
            content_type='application/json',
        )
        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        send_mail.assert_called_once()
        self.user.refresh_from_db()
        self.assertTrue(self.user.password.startswith('pbkdf2_'))

    @patch('login.views.send_mail')
    def test_verification_email_does_not_enumerate_and_has_cooldown(self, send_mail):
        first = self.client.post(
            reverse('login:send_verification_email'),
            data=json.dumps({'email': 'missing@example.com'}),
            content_type='application/json',
        )
        second = self.client.post(
            reverse('login:send_verification_email'),
            data=json.dumps({'email': 'missing@example.com'}),
            content_type='application/json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        send_mail.assert_called_once()

    def test_invalid_and_reused_verification_code_are_rejected(self):
        session = self.client.session
        session['verification_code'] = '1234'
        session['verification_code_sent_at'] = timezone.now().timestamp()
        session.save()
        payload = {
            'username': 'new-recovery-user',
            'email': 'new-recovery@example.com',
            'password1': 'runtime-password-123',
            'password2': 'runtime-password-123',
            'verification_code': '0000',
        }
        invalid = self.client.post(
            reverse('login:signup'), data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(invalid.status_code, 400)
        payload['verification_code'] = '1234'
        valid = self.client.post(
            reverse('login:signup'), data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(valid.status_code, 200)
        self.assertNotIn('verification_code', self.client.session)
        reused = self.client.post(
            reverse('login:signup'), data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(reused.status_code, 400)

    def test_expired_verification_code_is_rejected(self):
        session = self.client.session
        session['verification_code'] = '1234'
        session['verification_code_sent_at'] = (timezone.now() - timedelta(minutes=11)).timestamp()
        session.save()
        response = self.client.post(
            reverse('login:signup'),
            data=json.dumps({
                'username': 'expired-user',
                'email': 'expired@example.com',
                'password1': 'runtime-password-123',
                'password2': 'runtime-password-123',
                'verification_code': '1234',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    @patch('login.views.send_mail', side_effect=RuntimeError('smtp unavailable'))
    def test_smtp_failure_is_generic_and_does_not_change_password(self, send_mail):
        response = self.client.post(
            reverse('login:password_reset_request'),
            data=json.dumps({'email': self.user.email}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('smtp unavailable', response.content.decode())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('runtime-password-123'))
