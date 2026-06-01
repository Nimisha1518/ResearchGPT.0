import logging

from flask import current_app

from extensions import db
from models import Document

logger = logging.getLogger(__name__)


def _get_app():
    """Return the current Flask app, or create one for RQ worker processes."""
    try:
        return current_app._get_current_object()
    except RuntimeError:
        # Running inside an RQ worker — no app context exists yet.
        from app import create_app
        return create_app()


def process_document(document_id):
    """Process a single document: load PDF → embed → store in vector DB."""
    app = _get_app()

    with app.app_context():
        from rag_engine import ResearchPaperRAG

        document = Document.query.get(document_id)
        if not document:
            logger.warning("Document %d not found, skipping.", document_id)
            return

        document.status = "processing"
        document.error_message = None
        db.session.commit()
        logger.info("Processing document %d (%s)...", document.id, document.original_filename)

        try:
            rag = ResearchPaperRAG.from_config(app.config)
            storage = app.extensions["storage_service"]
            local_path = storage.get_local_path(
                document.storage_key,
                user_id=document.user_id,
                stored_filename=document.stored_filename,
            )

            chunk_count = rag.process_pdf(
                local_path,
                document_id=document.id,
                user_id=document.user_id,
                source_filename=document.original_filename,
            )
            document.status = "ready"
            logger.info(
                "Document %d processed successfully (%d chunks).",
                document.id, chunk_count,
            )
        except Exception as exc:
            document.status = "failed"
            document.error_message = str(exc)
            logger.exception("Failed to process document %d: %s", document.id, exc)
        finally:
            db.session.commit()


def enqueue_document_processing(document_id):
    """Enqueue document processing via RQ, or process synchronously."""
    if current_app.config.get("QUEUE_BACKEND") == "rq" and current_app.config.get("REDIS_URL"):
        from redis import Redis
        from rq import Queue

        queue = Queue(connection=Redis.from_url(current_app.config["REDIS_URL"]))
        queue.enqueue("jobs.process_document", document_id)
        logger.info("Enqueued document %d for background processing.", document_id)
        return "queued"

    process_document(document_id)
    return "processed"
