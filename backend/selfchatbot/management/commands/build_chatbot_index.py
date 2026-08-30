import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from selfchatbot.views import INDEX_MANIFEST_NAME


class Command(BaseCommand):
    help = 'Build the agriculture chatbot Chroma index from a question/answer CSV.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            default=os.getenv('CHATBOT_SOURCE_CSV', 'artifacts/chatbot.csv'),
            help='CSV containing 질문 and 답변 columns.',
        )
        parser.add_argument(
            '--output',
            default=os.getenv('CHROMA_DB_PATH', 'artifacts/chroma'),
            help='A new or empty Chroma persistence directory.',
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Validate source rows without API credentials or AI dependencies.',
        )

    def handle(self, *args, **options):
        source = self._resolve_path(options['source'])
        if not source.is_file():
            raise CommandError(f'Chatbot source CSV was not found: {source}')

        if options['validate_only']:
            documents = self._load_documents(source, self._ValidationDocument)
            if not documents:
                raise CommandError('The chatbot source CSV contains no usable rows.')
            self.stdout.write(self.style.SUCCESS(
                f'Validated {len(documents)} chatbot source rows in {source}'
            ))
            return

        if not os.getenv('OPENAI_API_KEY'):
            raise CommandError('OPENAI_API_KEY is required to create embeddings.')

        output = self._resolve_path(options['output'])
        if output.exists() and any(output.iterdir()):
            raise CommandError(
                f'Output directory must be empty to avoid mixing indexes: {output}'
            )

        try:
            from langchain_community.vectorstores import Chroma
            from langchain_core.documents import Document
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise CommandError(
                'Install requirements-ai.txt before building the chatbot index.'
            ) from exc

        documents = self._load_documents(source, Document)
        if not documents:
            raise CommandError('The chatbot source CSV contains no usable rows.')

        output.mkdir(parents=True, exist_ok=True)
        embeddings = OpenAIEmbeddings(
            model=settings.CHATBOT_EMBEDDING_MODEL,
            api_key=os.environ['OPENAI_API_KEY'],
        )
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=settings.CHATBOT_COLLECTION_NAME,
            persist_directory=str(output),
        )
        persist = getattr(vector_store, 'persist', None)
        if callable(persist):
            persist()
        manifest = {
            'schema_version': 1,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'source_name': source.name,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'document_count': len(documents),
            'embedding_model': settings.CHATBOT_EMBEDDING_MODEL,
            'collection_name': settings.CHATBOT_COLLECTION_NAME,
            'required_columns': ['질문', '답변', '출처', '출처URL'],
        }
        (output / INDEX_MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        self.stdout.write(self.style.SUCCESS(
            f'Built chatbot index with {len(documents)} documents at {output}'
        ))

    @staticmethod
    def _resolve_path(value):
        path = Path(value)
        return path if path.is_absolute() else Path(settings.BASE_DIR) / path

    class _ValidationDocument:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    @staticmethod
    def _load_documents(source, document_class):
        documents = []
        with source.open(encoding='utf-8-sig', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {'질문', '답변', '출처', '출처URL'}
            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise CommandError(
                    'CSV must contain 질문, 답변, 출처, and 출처URL columns.'
                )
            for row_number, row in enumerate(reader, start=2):
                question = (row.get('질문') or '').strip()
                answer = (row.get('답변') or '').strip()
                source_name = (row.get('출처') or '').strip()
                source_type = (row.get('출처유형') or '').strip()
                source_url = (row.get('출처URL') or '').strip()
                if not question and not answer and not source_name and not source_url:
                    continue
                if not question or not answer or not source_name:
                    raise CommandError(f'CSV row {row_number} has missing required content.')
                if not source_url.startswith('https://'):
                    raise CommandError(
                        f'CSV row {row_number} must have an HTTPS source URL.'
                    )
                documents.append(document_class(
                    page_content=(
                        f'질문: {question}\n답변: {answer}\n'
                        f'출처: {source_name}\n'
                        f'출처유형: {source_type}\n출처URL: {source_url}'
                    ),
                    metadata={
                        'source_file': source.name,
                        'source_name': source_name,
                        'source_type': source_type,
                        'source_url': source_url,
                        'row': row_number,
                    },
                ))
        return documents
