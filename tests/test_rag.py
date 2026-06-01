"""RAG engine unit tests — no real embeddings or Gemini calls needed."""

import pytest
from unittest.mock import patch, MagicMock


class TestBuildFilter:
    """Test the _build_filter helper on ResearchPaperRAG."""

    def _make_rag_instance(self):
        """Create a RAG instance with mocked embeddings and vector store."""
        with patch("rag_engine.HuggingFaceEmbeddings"), \
             patch("rag_engine.create_vector_store"):
            from rag_engine import ResearchPaperRAG
            config = {
                "VECTOR_BACKEND": "chroma",
                "PINECONE_API_KEY": "",
                "PINECONE_INDEX_NAME": "",
                "CHROMA_DB_DIR": "/tmp/test_chroma",
                "GEMINI_API_KEY": "",
            }
            rag = ResearchPaperRAG(config)
        return rag

    def test_no_filters_returns_none(self):
        rag = self._make_rag_instance()
        assert rag._build_filter() is None

    def test_single_user_id_filter(self):
        rag = self._make_rag_instance()
        result = rag._build_filter(user_id=42)
        assert result == {"user_id": 42}

    def test_single_filename_filter(self):
        rag = self._make_rag_instance()
        result = rag._build_filter(filename="paper.pdf")
        assert result == {"source": "paper.pdf"}

    def test_combined_filters_use_and(self):
        rag = self._make_rag_instance()
        result = rag._build_filter(user_id=1, filename="test.pdf")
        assert "$and" in result
        assert {"user_id": 1} in result["$and"]
        assert {"source": "test.pdf"} in result["$and"]

    def test_triple_filter(self):
        rag = self._make_rag_instance()
        result = rag._build_filter(user_id=1, filename="a.pdf", document_id=99)
        assert "$and" in result
        assert len(result["$and"]) == 3


class TestAnswerQueryWithoutApiKey:
    """Ensure answer_query returns a clean error without crashing when the API key is missing."""

    def test_returns_error_message(self):
        with patch("rag_engine.HuggingFaceEmbeddings"), \
             patch("rag_engine.create_vector_store"):
            from rag_engine import ResearchPaperRAG
            config = {
                "VECTOR_BACKEND": "chroma",
                "PINECONE_API_KEY": "",
                "PINECONE_INDEX_NAME": "",
                "CHROMA_DB_DIR": "/tmp/test_chroma",
                "GEMINI_API_KEY": "",
            }
            rag = ResearchPaperRAG(config)

        result = rag.answer_query("What is machine learning?", [])
        assert "Error" in result["answer"] or "missing" in result["answer"].lower()
        assert result["sources"] == []

    def test_returns_standalone_query(self):
        with patch("rag_engine.HuggingFaceEmbeddings"), \
             patch("rag_engine.create_vector_store"):
            from rag_engine import ResearchPaperRAG
            config = {
                "VECTOR_BACKEND": "chroma",
                "PINECONE_API_KEY": "",
                "PINECONE_INDEX_NAME": "",
                "CHROMA_DB_DIR": "/tmp/test_chroma",
                "GEMINI_API_KEY": "",
            }
            rag = ResearchPaperRAG(config)

        result = rag.answer_query("test query", [])
        assert result["standalone_query"] == "test query"


class TestSummarizeWithoutApiKey:
    """Ensure summarize_paper returns an error string, never crashes."""

    def test_returns_error_string(self):
        with patch("rag_engine.HuggingFaceEmbeddings"), \
             patch("rag_engine.create_vector_store"):
            from rag_engine import ResearchPaperRAG
            config = {
                "VECTOR_BACKEND": "chroma",
                "PINECONE_API_KEY": "",
                "PINECONE_INDEX_NAME": "",
                "CHROMA_DB_DIR": "/tmp/test_chroma",
                "GEMINI_API_KEY": "",
            }
            rag = ResearchPaperRAG(config)

        result = rag.summarize_paper("fake.pdf")
        assert isinstance(result, str)
        assert "error" in result.lower() or "missing" in result.lower()
