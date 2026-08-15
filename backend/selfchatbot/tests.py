from unittest.mock import patch

from django.test import SimpleTestCase

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
