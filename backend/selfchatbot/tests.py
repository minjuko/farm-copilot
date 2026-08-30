from unittest.mock import Mock, patch
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.core.management.base import CommandError

from aivle_big.exceptions import ServiceUnavailableError
from . import views
from .management.commands.build_chatbot_index import Command


class OptionalChatbotRuntimeTests(SimpleTestCase):
    def tearDown(self):
        views._rag_chain = None

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_openai_key_is_isolated_to_chatbot_feature(self):
        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_rag_chain()

        self.assertEqual(context.exception.status_code, 503)

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}, clear=True)
    @patch.object(views, 'vector_index_available', return_value=False)
    @override_settings(CHATBOT_ENABLED=True)
    def test_missing_vector_database_is_not_created(self, _index_available):
        with self.assertRaises(ServiceUnavailableError):
            views.get_rag_chain()

    def test_relative_vector_database_path_is_based_on_base_dir(self):
        with patch.dict('os.environ', {'CHROMA_DB_PATH': 'artifacts/chroma'}):
            self.assertEqual(
                views.resolve_vector_db_path(),
                views.VECTOR_DB_PATH.parent / 'artifacts' / 'chroma',
            )

    def test_vector_index_requires_chroma_database_file(self):
        with TemporaryDirectory() as directory:
            index_path = Path(directory)
            self.assertFalse(views.vector_index_available(index_path))
            (index_path / 'chroma.sqlite3').touch()
            self.assertFalse(views.vector_index_available(index_path))
            (index_path / views.INDEX_MANIFEST_NAME).write_text(json.dumps({
                'embedding_model': 'text-embedding-3-small',
                'collection_name': 'agriculture-knowledge',
                'document_count': 1,
                'source_sha256': 'a' * 64,
            }), encoding='utf-8')
            self.assertTrue(views.vector_index_available(index_path))

    @override_settings(CHATBOT_EMBEDDING_MODEL='expected-model')
    def test_vector_index_rejects_mismatched_embedding_contract(self):
        with TemporaryDirectory() as directory:
            index_path = Path(directory)
            (index_path / 'chroma.sqlite3').touch()
            (index_path / views.INDEX_MANIFEST_NAME).write_text(json.dumps({
                'embedding_model': 'another-model',
                'collection_name': 'agriculture-knowledge',
                'document_count': 1,
                'source_sha256': 'a' * 64,
            }), encoding='utf-8')
            self.assertFalse(views.vector_index_available(index_path))

    @patch.object(views, 'CHATBOT_DEPENDENCIES_AVAILABLE', False)
    @override_settings(CHATBOT_ENABLED=True)
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}, clear=True)
    @patch.object(views, 'vector_index_available', return_value=True)
    def test_missing_optional_dependencies_are_controlled(self, _index_available):
        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_rag_chain()

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('Traceback', context.exception.message)

    @patch.object(views, 'CHATBOT_DEPENDENCIES_AVAILABLE', True)
    @override_settings(CHATBOT_ENABLED=True)
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}, clear=True)
    @patch.object(views, 'vector_index_available', return_value=True)
    @patch.object(views, 'OpenAIEmbeddings', create=True)
    def test_initialization_failure_is_controlled(
        self, embeddings, _index_available
    ):
        embeddings.side_effect = RuntimeError('provider unavailable')

        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_rag_chain()

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('provider unavailable', context.exception.message)

    def test_provider_output_remains_plain_text(self):
        answer = '<img src=x onerror=alert(1)>\n**안전한 답변**'
        self.assertEqual(views.format_answer(answer), answer)

    @override_settings(CHATBOT_ENABLED=False)
    def test_status_reports_archived_without_provider_details(self):
        response = views.chatbot_status(RequestFactory().get('/selfchatbot/status/'))
        self.assertJSONEqual(response.content, {
            'status': 'archived',
            'available': False,
        })


class ChatbotSourceContractTests(SimpleTestCase):
    class Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    def test_source_csv_requires_attribution_and_https_url(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'chatbot.csv'
            source.write_text(
                '질문,답변,출처,출처URL\n질문,답변,농촌진흥청,http://example.com\n',
                encoding='utf-8',
            )
            with self.assertRaisesMessage(CommandError, 'HTTPS source URL'):
                Command._load_documents(source, self.Document)

    def test_source_csv_preserves_provenance_metadata(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'chatbot.csv'
            source.write_text(
                '질문,답변,출처,출처URL\n재배 질문,검증된 답변,농촌진흥청,https://www.rda.go.kr/\n',
                encoding='utf-8',
            )
            documents = Command._load_documents(source, self.Document)
            self.assertEqual(len(documents), 1)
            self.assertIn('출처: 농촌진흥청', documents[0].page_content)
            self.assertIn('https://www.rda.go.kr/', documents[0].page_content)
            self.assertEqual(documents[0].metadata, {
                'source_file': 'chatbot.csv',
                'source_name': '농촌진흥청',
                'source_url': 'https://www.rda.go.kr/',
                'row': 2,
            })


class ChatbotCsrfBoundaryTests(TestCase):
    def setUp(self):
        from login.models import User

        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            email='chatbot-security@example.com',
            username='chatbot-security',
            password='test-password',
        )

    def csrf_token(self):
        return self.client.get("/login/auth_check/").cookies["csrftoken"].value

    @patch.dict('os.environ', {}, clear=True)
    def test_chatbot_write_requires_csrf_and_preserves_archive_boundary(self):
        anonymous = self.client.post(
            "/selfchatbot/chatbot/",
            data=b'{"question":"test","session_id":"session-1"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_login(self.user)
        without_token = self.client.post(
            "/selfchatbot/chatbot/",
            data=b'{"question":"test","session_id":"session-1"}',
            content_type="application/json",
        )
        self.assertEqual(without_token.status_code, 403)

        with_token = self.client.post(
            "/selfchatbot/chatbot/",
            data=b'{"question":"test","session_id":"session-1"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(with_token.status_code, 503)
