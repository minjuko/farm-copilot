import json

from django.test import TestCase
from django.urls import reverse


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

        auth_response = self.client.get(reverse('login:auth_check'))
        self.assertEqual(auth_response.status_code, 200)
        self.assertTrue(auth_response.json()['is_authenticated'])

        logout_response = self.client.post(reverse('login:logout'))
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(
            self.client.get(reverse('login:auth_check')).json()['is_authenticated']
        )
