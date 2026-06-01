"""Shared pytest fixtures for ResearchGPT tests."""

import os

os.environ["FLASK_ENV"] = "testing"

import pytest

from app import create_app
from config import TestingConfig
from extensions import db as _db
from models import User


@pytest.fixture()
def app():
    """Create a fresh Flask application for each test."""
    app = create_app(TestingConfig)

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture()
def logged_in_client(app):
    """Test client with a pre-registered and logged-in user."""
    client = app.test_client()

    with app.app_context():
        user = User(name="Test User", email="test@example.com")
        user.set_password("password123")
        _db.session.add(user)
        _db.session.commit()

    # Log in via the register flow
    client.post("/login", data={
        "email": "test@example.com",
        "password": "password123",
    }, follow_redirects=True)

    return client
