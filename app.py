import logging
import os
from uuid import uuid4

from flask import Flask, current_app, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from config import Config
from extensions import db, login_manager
from jobs import enqueue_document_processing
from models import Document, User
from storage_service import create_storage_service

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf"}


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # ── Logging ──────────────────────────────────────────────────────
    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        app.extensions["storage_service"] = create_storage_service(app.config)

    register_routes(app)
    register_error_handlers(app)
    return app


def get_rag():
    from rag_engine import ResearchPaperRAG

    rag = current_app.extensions.get("rag_engine")
    if not rag:
        rag = ResearchPaperRAG.from_config(current_app.config)
        current_app.extensions["rag_engine"] = rag
    return rag


def get_user_documents():
    if not current_user.is_authenticated:
        return []

    documents = (
        Document.query
        .filter_by(user_id=current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [document.to_dict() for document in documents]


def _get_file_size(file_storage):
    """Get file size in bytes without consuming the stream."""
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    return size


def register_error_handlers(app):
    """Register centralized error handlers for clean JSON/HTML responses."""

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Resource not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) / (1024 * 1024)
        msg = f"File too large. Maximum upload size is {max_mb:.0f} MB."
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": msg}), 413
        flash(msg, "danger")
        return redirect(request.referrer or url_for("upload_page"))

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error: %s", error)
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "An internal server error occurred."}), 500
        return render_template("errors/500.html"), 500


def register_routes(app):
    # ── Health Check ─────────────────────────────────────────────────
    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok"})

    # ── Auth Routes ──────────────────────────────────────────────────
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("home"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or len(password) < 8:
                flash("Enter your name, email, and a password with at least 8 characters.", "danger")
                return render_template("register.html")

            if User.query.filter_by(email=email).first():
                flash("An account already exists for that email.", "danger")
                return render_template("register.html")

            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            logger.info("New user registered: %s (id=%d)", email, user.id)
            return redirect(url_for("home"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("home"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()

            if not user or not user.check_password(password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html")

            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("home"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # ── Page Routes ──────────────────────────────────────────────────
    @app.route("/")
    @login_required
    def home():
        return render_template("home.html", files=get_user_documents())

    @app.route("/upload")
    @login_required
    def upload_page():
        return render_template("upload.html", files=get_user_documents())

    @app.route("/chat")
    @login_required
    def chat_page():
        return render_template("chat.html", files=get_user_documents())

    # ── API Routes ───────────────────────────────────────────────────
    @app.route("/api/status", methods=["GET"])
    @login_required
    def api_status():
        return jsonify({
            "success": True,
            "gemini_configured": bool(app.config["GEMINI_API_KEY"]),
            "storage_backend": app.config["STORAGE_BACKEND"],
            "vector_backend": app.config["VECTOR_BACKEND"],
            "queue_backend": app.config["QUEUE_BACKEND"],
        })

    @app.route("/api/upload", methods=["POST"])
    @login_required
    def api_upload():
        if "files" not in request.files:
            return jsonify({"success": False, "error": "No file part in request"}), 400

        uploaded_files = request.files.getlist("files")
        if not uploaded_files or uploaded_files[0].filename == "":
            return jsonify({"success": False, "error": "No files selected"}), 400

        storage = app.extensions["storage_service"]
        processed = []
        errors = []

        for file in uploaded_files:
            if not file or not file.filename:
                continue

            # Extension check
            if not file.filename.lower().endswith(".pdf"):
                errors.append(f"Ignored {file.filename} (only PDF files are supported)")
                continue

            # MIME type check
            if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
                errors.append(
                    f"Ignored {file.filename} (invalid content type: {file.content_type})"
                )
                continue

            original_filename = secure_filename(file.filename)
            stored_filename = f"{uuid4().hex}_{original_filename}"

            # Measure file size before saving (works for both local and S3)
            file_size = _get_file_size(file)

            try:
                saved = storage.save_upload(file, current_user.id, stored_filename)
                document = Document(
                    user_id=current_user.id,
                    original_filename=original_filename,
                    stored_filename=stored_filename,
                    storage_key=saved["storage_key"],
                    size_bytes=file_size,
                    status="uploaded",
                )
                db.session.add(document)
                db.session.commit()

                queue_result = enqueue_document_processing(document.id)
                db.session.refresh(document)

                document_data = document.to_dict()
                processed.append(document_data)

                if queue_result == "processed" and document.status == "failed":
                    errors.append(
                        f"Indexing failed for {document.original_filename}: {document.error_message or 'Unknown error'}"
                    )

                logger.info(
                    "Uploaded document '%s' (%d bytes) for user %d → %s",
                    original_filename, file_size, current_user.id, queue_result,
                )
            except Exception as exc:
                db.session.rollback()
                logger.exception("Failed to process upload %s: %s", file.filename, exc)
                errors.append(f"Failed to process {file.filename}: {str(exc)}")

        ready_or_pending_documents = [
            document for document in processed
            if document["status"] in {"uploaded", "processing", "ready"}
        ]

        if ready_or_pending_documents:
            return jsonify({
                "success": True,
                "message": f"Uploaded {len(ready_or_pending_documents)} paper(s). Indexing has started.",
                "documents": processed,
                "errors": errors,
            })

        return jsonify({
            "success": False,
            "error": "Failed to index any uploaded files.",
            "details": errors,
            "documents": processed,
        }), 400

    @app.route("/api/files", methods=["GET"])
    @login_required
    def api_get_files():
        return jsonify({"success": True, "files": get_user_documents()})

    @app.route("/api/delete", methods=["POST"])
    @login_required
    def api_delete_file():
        data = request.json or {}
        filename = secure_filename(data.get("filename", ""))

        if not filename:
            return jsonify({"success": False, "error": "Filename is required"}), 400

        document = Document.query.filter_by(user_id=current_user.id, original_filename=filename).first()
        if not document:
            return jsonify({"success": False, "error": "Document was not found."}), 404

        try:
            get_rag().delete_paper(filename=document.original_filename, user_id=current_user.id, document_id=document.id)
            app.extensions["storage_service"].delete(document.storage_key)
            db.session.delete(document)
            db.session.commit()
            logger.info("Deleted document '%s' for user %d", filename, current_user.id)
        except Exception as exc:
            db.session.rollback()
            logger.exception("Error deleting paper '%s': %s", filename, exc)
            return jsonify({"success": False, "error": f"Error deleting paper: {str(exc)}"}), 500

        return jsonify({"success": True, "message": f"Successfully deleted paper: {filename}"})

    @app.route("/api/chat", methods=["POST"])
    @login_required
    def api_chat():
        data = request.json or {}
        query = data.get("query")
        chat_history = data.get("chat_history", [])
        filter_filename = data.get("filename")

        if not query:
            return jsonify({"success": False, "error": "Query is required"}), 400

        rag = get_rag()
        if not rag.gemini_api_key:
            rag.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

        result = rag.answer_query(query, chat_history, filter_filename, user_id=current_user.id)
        return jsonify({"success": True, **result})

    @app.route("/api/summarize", methods=["POST"])
    @login_required
    def api_summarize():
        data = request.json or {}
        filename = secure_filename(data.get("filename", ""))

        if not filename:
            return jsonify({"success": False, "error": "Filename is required"}), 400

        document = Document.query.filter_by(user_id=current_user.id, original_filename=filename).first()
        if not document:
            return jsonify({"success": False, "error": "Document was not found."}), 404

        summary = get_rag().summarize_paper(filename, user_id=current_user.id)
        return jsonify({"success": True, "summary": summary})

    @app.route("/api/search", methods=["POST"])
    @login_required
    def api_search():
        data = request.json or {}
        query = data.get("query")

        if not query:
            return jsonify({"success": False, "error": "Query is required"}), 400

        results = get_rag().semantic_search(query, user_id=current_user.id)
        return jsonify({"success": True, "results": results})


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=app.config["DEBUG"])
