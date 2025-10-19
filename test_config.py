import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def sample_books_data():
    return {
        "Volume 1": [
            "https://example.com/chapter1",
            "https://example.com/chapter2"
        ],
        "Volume 2": [
            "https://example.com/chapter3",
            "https://example.com/chapter4"
        ]
    }

@pytest.fixture
def sample_request_data():
    return {
        "url": "https://example.com/books",
        "format": "pdf"
    }