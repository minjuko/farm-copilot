from unittest.mock import Mock, patch
from types import SimpleNamespace

from django.test import Client, RequestFactory, SimpleTestCase

from aivle_big.exceptions import ServiceUnavailableError
from . import views


class OptionalChatbotRuntimeTests(SimpleTestCase):
    def tearDown(self):
        views._rag_chain = None

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_openai_key_is_isolated_to_chatbot_feature(self):
        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_rag_chain()

        self.assertEqual(context.exception.status_code, 503)

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}, clear=True)
    @patch.object(views, 'VECTOR_DB_PATH')
    def test_missing_vector_database_is_not_created(self, vector_db_path):
        vector_db_path.exists.return_value = False

        with self.assertRaises(ServiceUnavailableError):
            views.get_rag_chain()

    def test_relative_vector_database_path_is_based_on_base_dir(self):
        with patch.dict('os.environ', {'CHROMA_DB_PATH': 'artifacts/chroma'}):
            self.assertEqual(
                views.resolve_vector_db_path(),
                views.VECTOR_DB_PATH.parent / 'artifacts' / 'chroma',
            )

    @patch.object(views, 'CHATBOT_DEPENDENCIES_AVAILABLE', False)
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}, clear=True)
    @patch.object(views, 'VECTOR_DB_PATH')
    def test_missing_optional_dependencies_are_controlled(self, vector_db_path):
        vector_db_path.exists.return_value = True

        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_rag_chain()

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('Traceback', context.exception.message)

    @patch.object(views, 'CHATBOT_DEPENDENCIES_AVAILABLE', True)
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}, clear=True)
    @patch.object(views, 'VECTOR_DB_PATH')
    @patch.object(views, 'OpenAIEmbeddings', create=True)
    def test_initialization_failure_is_controlled(
        self, embeddings, vector_db_path
    ):
        vector_db_path.exists.return_value = True
        embeddings.side_effect = RuntimeError('provider unavailable')

        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_rag_chain()

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('provider unavailable', context.exception.message)

    @patch.object(views, 'get_rag_chain')
    def test_endpoint_invocation_failure_is_controlled_503(self, get_rag_chain):
        chain = SimpleNamespace(invoke=Mock(side_effect=RuntimeError('provider traceback')))
        get_rag_chain.return_value = chain

        request = RequestFactory().post(
            '/selfchatbot/chatbot/',
            data=b'{"question":"test"}',
            content_type='application/json',
        )
        request.user = SimpleNamespace(is_authenticated=False)

        with self.assertRaises(ServiceUnavailableError) as context:
            views.chatbot(request)

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('provider traceback', context.exception.message)


class ChatbotCsrfBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def csrf_token(self):
        return self.client.get("/login/auth_check/").cookies["csrftoken"].value

    @patch.dict('os.environ', {}, clear=True)
    def test_chatbot_write_requires_csrf_and_preserves_archive_boundary(self):
        without_token = self.client.post(
            "/selfchatbot/chatbot/",
            data=b'{"question":"test"}',
            content_type="application/json",
        )
        self.assertEqual(without_token.status_code, 403)

        with_token = self.client.post(
            "/selfchatbot/chatbot/",
            data=b'{"question":"test"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(with_token.status_code, 503)
