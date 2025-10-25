import pytest
import json
from unittest.mock import patch, MagicMock
from app import  validate_url, get_book_names, get_webpage_content

class TestURLValidation:
    """Test URL validation functions."""
    
    def test_validate_url_valid(self):
        """Test valid URL validation."""
        data = {"url": "https://example.com"}
        assert validate_url(data) == True
    
    def test_validate_url_invalid_protocol(self):
        """Test invalid protocol URL validation."""
        data = {"url": "ftp://example.com"}
        assert validate_url(data) == False
    
    def test_validate_url_missing_url_key(self):
        """Test validation with missing url key."""
        data = {"format": "pdf"}
        assert validate_url(data) == False

    def test_validate_url_empty_url(self):
        """Test validation with empty URL."""
        data = {"url": ""}
        assert validate_url(data) == False

    def test_validate_url_malformed_url(self):
        """Test validation with malformed URL."""
        data = {"url": "htp:/example"}
        assert validate_url(data) == False
    
    def test_validate_url_none_data(self):
        """Test validation with None data."""
        assert validate_url(None) == False

class TestProcessEndpoint:
    """Test the /process endpoint."""
    
    @patch('app.get_book_names')
    def test_process_endpoint_success(self, mock_get_books, client):
        """Test successful processing of valid URL."""
        # Mock the get_book_names function
        mock_get_books.return_value = ["Volume 1", "Volume 2"]
        
        response = client.post('/process', 
                             json={"url": "https://example.com", "format": "pdf"},
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "books" in data
        assert len(data["books"]) == 2
        assert data["books"][0]["title"] == "Volume 1"
    
    def test_process_endpoint_invalid_url(self, client):
        """Test processing with invalid URL."""
        response = client.post('/process', 
                             json={"url": "invalid-url"},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    @patch('app.get_book_names')
    def test_process_endpoint_fetch_failure(self, mock_get_books, client):
        """Test processing when webpage fetching fails."""
        mock_get_books.return_value = None
        
        response = client.post('/process', 
                             json={"url": "https://example.com"},
                             content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data

class TestDownloadEndpoint:
    """Test the /download endpoint."""
    
    @patch('app.get_webpage_content')
    @patch('app.process_chapters')
    def test_download_endpoint_success(self, mock_process, mock_get_content, client, sample_books_data):
        """Test successful download request."""
        mock_get_content.return_value = sample_books_data
        mock_process.return_value = {"Volume 1": "processed_content"}
        
        response = client.post('/download',
                             json={
                                 "selectedBooks": ["Volume 1"],
                                 "format": "pdf",
                                 "url": "https://example.com"
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data
    
    def test_download_endpoint_no_books(self, client):
        """Test download with no books selected."""
        response = client.post('/download',
                             json={
                                 "selectedBooks": [],
                                 "format": "pdf",
                                 "url": "https://example.com"
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "No books selected"
    
    def test_download_endpoint_no_format(self, client):
        """Test download with no format specified."""
        response = client.post('/download',
                             json={
                                 "selectedBooks": ["Volume 1"],
                                 "url": "https://example.com"
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "No format selected"

class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('requests.get')
    def test_get_book_names_success(self, mock_get):
        """Test successful book name extraction."""
        # Mock HTML response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'''
        <html>
            <h3>Volume 1</h3>
            <h3>Volume 2</h3>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = get_book_names("https://example.com")
        assert result == ["Volume 1", "Volume 2"]
    
    @patch('requests.get')
    def test_get_book_names_request_failure(self, mock_get):
        """Test book name extraction with request failure."""
        mock_get.side_effect = Exception("Network error")
        
        result = get_book_names("https://example.com")
        assert result is None