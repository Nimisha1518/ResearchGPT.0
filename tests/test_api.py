"""API endpoint tests: health check, status, chat, search validation."""

import json


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_health_does_not_require_auth(self, client):
        """Health check must be accessible without login for cloud probes."""
        resp = client.get("/health")
        assert resp.status_code == 200


class TestStatusEndpoint:
    def test_status_returns_config_keys(self, logged_in_client):
        resp = logged_in_client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "gemini_configured" in data
        assert "storage_backend" in data
        assert "vector_backend" in data
        assert "queue_backend" in data


class TestChatEndpoint:
    def test_chat_requires_query(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/chat",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "Query is required" in data["error"]

    def test_chat_empty_query(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/chat",
            data=json.dumps({"query": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestSearchEndpoint:
    def test_search_requires_query(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/search",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Query is required" in data["error"]


class TestSummarizeEndpoint:
    def test_summarize_requires_filename(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/summarize",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Filename is required" in data["error"]

    def test_summarize_nonexistent_file(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/summarize",
            data=json.dumps({"filename": "nonexistent.pdf"}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestDeleteEndpoint:
    def test_delete_requires_filename(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/delete",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_delete_nonexistent_file(self, logged_in_client):
        resp = logged_in_client.post(
            "/api/delete",
            data=json.dumps({"filename": "ghost.pdf"}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestErrorHandlers:
    def test_404_api_returns_json(self, logged_in_client):
        resp = logged_in_client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False

    def test_404_page_returns_html(self, logged_in_client):
        resp = logged_in_client.get("/nonexistent-page")
        assert resp.status_code == 404
        assert b"404" in resp.data
