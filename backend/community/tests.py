import json

from django.test import Client, TestCase
from django.urls import reverse

from login.models import User
from .models import Comment, Post


class CommunitySmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='community@example.com',
            username='community-user',
            password='runtime-password-123',
        )
        self.other_user = User.objects.create_user(
            email='other-community@example.com',
            username='other-community-user',
            password='runtime-password-123',
        )
        self.client.force_login(self.user)

    def test_post_and_comment_crud_flow(self):
        create_response = self.client.post(
            reverse('community:post_create'),
            data={'title': 'Runtime post', 'content': 'Initial content', 'post_type': 'buy'},
        )
        self.assertEqual(create_response.status_code, 201)
        post_id = create_response.json()['id']

        self.assertEqual(self.client.get(reverse('community:post_list')).status_code, 200)
        detail_url = reverse('community:post_detail', args=[post_id])
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        edit_response = self.client.post(
            reverse('community:post_edit', args=[post_id]),
            data={'title': 'Updated post', 'content': 'Updated content', 'post_type': 'sell'},
        )
        self.assertEqual(edit_response.status_code, 200)

        comment_response = self.client.post(
            reverse('community:comment_create', args=[post_id]),
            data=json.dumps({'content': 'Runtime comment'}),
            content_type='application/json',
        )
        self.assertEqual(comment_response.status_code, 201)
        comment_id = comment_response.json()['id']

        self.assertEqual(
            self.client.post(reverse('community:comment_delete', args=[comment_id])).status_code,
            204,
        )
        self.assertEqual(
            self.client.post(reverse('community:post_delete', args=[post_id])).status_code,
            204,
        )

    def test_unauthenticated_post_creation_is_rejected(self):
        self.client.logout()
        response = self.client.post(
            reverse('community:post_create'),
            data={'title': 'Unauthenticated', 'content': 'Blocked', 'post_type': 'buy'},
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_post_input_returns_bad_request(self):
        response = self.client.post(
            reverse('community:post_create'),
            data={'title': '', 'content': '', 'post_type': 'invalid'},
        )
        self.assertEqual(response.status_code, 400)

    def test_other_user_cannot_edit_or_delete_post(self):
        post_id = self.client.post(
            reverse('community:post_create'),
            data={'title': 'Owner post', 'content': 'Edit target', 'post_type': 'buy'},
        ).json()['id']
        self.client.force_login(self.other_user)

        edit_response = self.client.post(
            reverse('community:post_edit', args=[post_id]),
            data={'title': 'Tampered', 'content': 'Tampered', 'post_type': 'sell'},
        )
        delete_response = self.client.post(
            reverse('community:post_delete', args=[post_id])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)


class CommunityCsrfBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='csrf-community@example.com',
            username='csrf-community-user',
            password='runtime-password-123',
        )
        self.other_user = User.objects.create_user(
            email='csrf-other@example.com',
            username='csrf-other-user',
            password='runtime-password-123',
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def csrf_token(self):
        response = self.client.get(reverse('login:auth_check'))
        return response.cookies['csrftoken'].value

    def test_post_create_requires_csrf_and_accepts_valid_token(self):
        without_token = self.client.post(
            reverse('community:post_create'),
            data={'title': 'Blocked', 'content': 'No token', 'post_type': 'buy'},
        )
        self.assertEqual(without_token.status_code, 403)

        token = self.csrf_token()
        with_token = self.client.post(
            reverse('community:post_create'),
            data={'title': 'Allowed', 'content': 'Valid token', 'post_type': 'buy'},
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(with_token.status_code, 201)

    def test_valid_csrf_does_not_bypass_post_ownership(self):
        token = self.csrf_token()
        post = Post.objects.create(
            user=self.user,
            title='Owner post',
            content='Owner content',
            post_type='buy',
        )
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('community:post_edit', args=[post.id]),
            data={'title': 'Tampered', 'content': 'Tampered', 'post_type': 'sell'},
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=post.id, user=self.user).exists())

    def test_other_user_cannot_edit_or_delete_comment(self):
        token = self.csrf_token()
        post_id = self.client.post(
            reverse('community:post_create'),
            data={'title': 'Comment owner post', 'content': 'Content', 'post_type': 'buy'},
            HTTP_X_CSRFTOKEN=token,
        ).json()['id']
        comment_id = self.client.post(
            reverse('community:comment_create', args=[post_id]),
            data=json.dumps({'content': 'Owner comment'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        ).json()['id']
        self.client.force_login(self.other_user)

        edit_response = self.client.post(
            reverse('community:comment_edit', args=[comment_id]),
            data=json.dumps({'content': 'Tampered'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        delete_response = self.client.post(
            reverse('community:comment_delete', args=[comment_id]),
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
