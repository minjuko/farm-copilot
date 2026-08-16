import json

from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthenticationSmokeTests(TestCase):
    def test_signup_session_auth_check_and_logout(self):
        session = self.client.session
        session['verification_code'] = '1234'
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
