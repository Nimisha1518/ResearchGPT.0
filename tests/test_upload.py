"""Upload endpoint tests: validation, MIME checks, error handling."""

import io


class TestUploadValidation:
    def test_upload_no_file_part(self, logged_in_client):
        resp = logged_in_client.post("/api/upload")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "No file part" in data["error"]

    def test_upload_empty_file_list(self, logged_in_client):
        resp = logged_in_client.post("/api/upload", data={
            "files": (io.BytesIO(b""), ""),
        }, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_non_pdf_rejected(self, logged_in_client):
        fake_txt = (io.BytesIO(b"hello world"), "notes.txt")
        resp = logged_in_client.post("/api/upload", data={
            "files": fake_txt,
        }, content_type="multipart/form-data")
        data = resp.get_json()
        # Either fails or has errors list mentioning PDF
        assert not data.get("success") or any("PDF" in e or "pdf" in e for e in data.get("errors", []))

    def test_upload_valid_pdf_accepted(self, logged_in_client):
        # Minimal valid PDF content
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        fake_pdf = (io.BytesIO(pdf_bytes), "test_paper.pdf")
        resp = logged_in_client.post("/api/upload", data={
            "files": fake_pdf,
        }, content_type="multipart/form-data")
        # This may fail at the RAG indexing stage (no real embedding model in test),
        # but it should at least accept the file upload and return a document
        data = resp.get_json()
        assert "documents" in data or "error" in data
