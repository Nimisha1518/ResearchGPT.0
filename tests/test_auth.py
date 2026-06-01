"""Authentication flow tests: register, login, logout, protected routes."""


class TestAuthPages:
    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"login" in resp.data.lower() or b"Login" in resp.data

    def test_register_page_renders(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_home_requires_login(self, client):
        resp = client.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


class TestRegisterFlow:
    def test_register_creates_user_and_logs_in(self, client):
        resp = client.post("/register", data={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "securepass8",
        }, follow_redirects=True)
        assert resp.status_code == 200
        # After register, user is redirected to home
        assert b"Dashboard" in resp.data or b"ResearchGPT" in resp.data

    def test_register_rejects_short_password(self, client):
        resp = client.post("/register", data={
            "name": "Bob",
            "email": "bob@example.com",
            "password": "short",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"at least 8 characters" in resp.data

    def test_register_rejects_duplicate_email(self, client):
        # First registration
        client.post("/register", data={
            "name": "Charlie",
            "email": "charlie@example.com",
            "password": "password123",
        })
        # Logout
        client.get("/logout")
        # Second registration with same email
        resp = client.post("/register", data={
            "name": "Charlie2",
            "email": "charlie@example.com",
            "password": "password456",
        }, follow_redirects=True)
        assert b"already exists" in resp.data


class TestLoginFlow:
    def test_login_with_valid_credentials(self, client):
        # Register first
        client.post("/register", data={
            "name": "Diana",
            "email": "diana@example.com",
            "password": "password123",
        })
        client.get("/logout")

        # Login
        resp = client.post("/login", data={
            "email": "diana@example.com",
            "password": "password123",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_with_wrong_password(self, client):
        # Register first
        client.post("/register", data={
            "name": "Eve",
            "email": "eve@example.com",
            "password": "password123",
        })
        client.get("/logout")

        resp = client.post("/login", data={
            "email": "eve@example.com",
            "password": "wrongpassword",
        }, follow_redirects=True)
        assert b"Invalid" in resp.data


class TestLogout:
    def test_logout_redirects_to_login(self, logged_in_client):
        resp = logged_in_client.get("/logout")
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


class TestProtectedRoutes:
    def test_upload_requires_login(self, client):
        resp = client.get("/upload")
        assert resp.status_code == 302

    def test_chat_requires_login(self, client):
        resp = client.get("/chat")
        assert resp.status_code == 302

    def test_api_status_requires_login(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 302
