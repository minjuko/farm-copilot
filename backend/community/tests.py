import json

from django.test import TestCase
from django.urls import reverse

from login.models import User


class CommunitySmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='community@example.com',
            username='community-user',
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
