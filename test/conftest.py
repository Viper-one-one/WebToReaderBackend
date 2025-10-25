import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app

@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    return flask_app

@pytest.fixture
def client():
    return flask_app.test_client()

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