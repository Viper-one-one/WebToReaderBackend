import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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