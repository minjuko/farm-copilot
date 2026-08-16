import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

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
        cache.clear()
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
        cache.clear()
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
    def test_password_reset_token_is_one_time_and_does_not_change_password_on_request(self, send_mail):
        old_hash = self.user.password
        response = self.client.post(
            reverse('login:password_reset_request'),
            data=json.dumps({'email': self.user.email}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, old_hash)
        body = send_mail.call_args.args[1]
        self.assertIn('password-reset-confirm', body)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirmed = self.client.post(
            reverse('login:password_reset_confirm_api'),
            data=json.dumps({'uid': uid, 'token': token, 'new_password': 'new-runtime-password-123'}),
            content_type='application/json',
        )
        self.assertEqual(confirmed.status_code, 200)
        reused = self.client.post(
            reverse('login:password_reset_confirm_api'),
            data=json.dumps({'uid': uid, 'token': token, 'new_password': 'another-runtime-password-123'}),
            content_type='application/json',
        )
        self.assertEqual(reused.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-runtime-password-123'))
        self.assertNotEqual(self.user.password, old_hash)

    def test_password_reset_rate_limit(self):
        payload = json.dumps({'email': 'missing@example.com'})
        responses = [self.client.post(reverse('login:password_reset_request'), data=payload, content_type='application/json') for _ in range(6)]
        self.assertEqual([response.status_code for response in responses[:5]], [200] * 5)
        self.assertEqual(responses[5].status_code, 429)

    def test_invalid_reset_token_and_uid_are_controlled(self):
        response = self.client.post(
            reverse('login:password_reset_confirm_api'),
            data=json.dumps({'uid': 'not-valid', 'token': 'invalid', 'new_password': 'new-runtime-password-123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('Traceback', response.content.decode())

    def test_password_reset_invalidates_existing_session(self):
        self.client.force_login(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.post(
            reverse('login:password_reset_confirm_api'),
            data=json.dumps({'uid': uid, 'token': token, 'new_password': 'session-reset-password-123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.get(reverse('login:auth_check')).json()['is_authenticated'])

    def test_login_failures_are_rate_limited_without_account_disclosure(self):
        payload = json.dumps({'email': self.user.email, 'password': 'wrong-password'})
        responses = [self.client.post(reverse('login:login'), data=payload, content_type='application/json') for _ in range(11)]
        self.assertEqual([response.status_code for response in responses[:10]], [403] * 10)
        self.assertEqual(responses[10].status_code, 429)
        self.assertNotIn(self.user.email, responses[10].content.decode())

    def test_successful_login_clears_failure_counter(self):
        self.client.post(
            reverse('login:login'),
            data=json.dumps({'email': self.user.email, 'password': 'wrong-password'}),
            content_type='application/json',
        )
        success = self.client.post(
            reverse('login:login'),
            data=json.dumps({'email': self.user.email, 'password': 'runtime-password-123'}),
            content_type='application/json',
        )
        self.assertEqual(success.status_code, 200)
        after_success_failure = self.client.post(
            reverse('login:login'),
            data=json.dumps({'email': self.user.email, 'password': 'wrong-password'}),
            content_type='application/json',
        )
        self.assertEqual(after_success_failure.status_code, 403)

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

    def test_verification_code_is_discarded_after_failure_limit(self):
        session = self.client.session
        session['verification_code'] = '1234'
        session['verification_code_sent_at'] = timezone.now().timestamp()
        session.save()
        payload = {
            'username': 'limit-user',
            'email': 'limit@example.com',
            'password1': 'runtime-password-123',
            'password2': 'runtime-password-123',
            'verification_code': '0000',
        }
        responses = [
            self.client.post(reverse('login:signup'), data=json.dumps(payload), content_type='application/json')
            for _ in range(5)
        ]
        self.assertEqual([response.status_code for response in responses[:4]], [400] * 4)
        self.assertEqual(responses[4].status_code, 429)
        self.assertNotIn('verification_code', self.client.session)

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
