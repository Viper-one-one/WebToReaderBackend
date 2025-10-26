# WebToReader Backend

A Flask-based backend service that scrapes web novel content and converts it into downloadable PDF and EPUB formats. This service extracts chapters, illustrations, inline images, and tables from web pages and formats them into properly structured eBooks.

## Features

- 📚 **Multi-Volume Support**: Process single or multiple volumes of web novels
- 📄 **PDF Generation**: Create professionally formatted PDFs with:
  - Custom page margins (19mm left/right/top, 6.35mm bottom)
  - Bold chapter titles
  - Inline images with original sizing (scaled to fit page boundaries)
  - Tables with proper text wrapping and left alignment
  - Illustrations chapters with optimized image sizing
- 📖 **EPUB Generation**: Convert content to EPUB format for eReader compatibility
- 🖼️ **Image Handling**: 
  - Downloads and embeds illustrations
  - Processes inline images with aspect ratio preservation
  - Automatic scaling for page fit
- 📊 **Table Support**: Preserves table formatting from source HTML with proper text wrapping
- 🔄 **Batch Processing**: Download multiple volumes as separate PDFs or combined in a ZIP file
- 🌐 **CORS Support**: Full CORS support for cross-origin requests

## Tech Stack

- **Framework**: Flask 3.x
- **PDF Generation**: ReportLab 4.2.5
- **HTML Parsing**: BeautifulSoup4 4.12.3
- **Image Processing**: Pillow
- **EPUB Creation**: EbookLib
- **HTTP Requests**: Requests library

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Viper-one-one/WebToReaderBackend.git
cd WebToReaderBackend/web-to-reader-backend
```

2. Install dependencies:
```bash
pip install -r Docker/requirements.txt
```

3. Run the Flask application:
```bash
flask run --debug
```

The server will start on `http://127.0.0.1:5000`

## API Endpoints

### POST `/process`

Validates a URL and retrieves available volumes.

**Request Body:**
```json
{
  "url": "https://example.com/book-page"
}
```

**Response:**
```json
{
  "success": true,
  "volumes": [
    {
      "id": 1,
      "title": "Volume 1"
    }
  ]
}
```

### POST `/download`

Downloads selected volumes in the specified format.

**Request Body:**
```json
{
  "url": "https://example.com/book-page",
  "selectedBooks": [1, 2],
  "format": "PDF"
}
```

**Response:**
- Single PDF file (if one volume selected)
- ZIP file containing multiple PDFs (if multiple volumes selected)
- EPUB file (if format is "EPUB")

**Supported Formats:**
- `PDF` - Portable Document Format
- `EPUB` - Electronic Publication

## Project Structure

```
WebToReaderBackend/
├── web-to-reader-backend/
│   ├── app.py                 # Main Flask application
│   ├── downloads/             # Generated PDF/EPUB files (auto-created)
│   ├── temp_images/           # Temporary image storage (auto-created)
│   ├── logging/
│   │   └── logger.py          # Logging configuration
│   ├── test/
│   │   ├── conftest.py        # Pytest configuration
│   │   ├── pytest.ini         # Pytest settings
│   │   └── test.py            # Test suite
│   └── Docker/
│       ├── compose.yaml       # Docker Compose configuration
│       ├── Dockerfile         # Docker image definition
│       ├── README.Docker.md   # Docker setup instructions
│       └── requirements.txt   # Python dependencies
└── README.md                  # This file
```

## Core Functions

### `validate_url(request_json)`
Validates the URL format in incoming requests.

### `get_webpage_content(url)`
Fetches and parses webpage content using BeautifulSoup4.

### `get_book_names(url)`
Extracts volume names and chapter information from the webpage.

### `fetch_chapter(chapter_url)`
Scrapes individual chapter content including:
- Paragraphs
- Inline images (with src, alt, and caption)
- Tables (preserving multi-line cell content)

### `process_chapters(books)`
Processes all chapters and categorizes them as:
- **Text chapters**: Numbered sequentially (1, 2, 3...)
- **Illustration chapters**: Labeled as "Illustrations"

### `create_single_pdf(volume_name, chapters)`
Generates a PDF for a single volume with:
- A4 page size
- Custom margins (54pt left/right/top, 18pt bottom)
- Chapter titles in bold (18pt Helvetica-Bold)
- Body text in 12pt Helvetica
- Inline images at original size (scaled if exceeding page boundaries)
- Tables with automatic column width distribution
- Illustration images with first image sized to fit on title page

### `create_pdf(books)`
Generates a combined PDF for multiple volumes.

### `create_epub(books)`
Generates an EPUB file from the extracted content.

### `cleanup_directories()`
Removes temporary files and directories after processing.

## PDF Formatting Details

### Page Layout
- **Page Size**: A4 (210mm × 297mm)
- **Margins**: 
  - Left/Right/Top: 54 points (19mm)
  - Bottom: 18 points (6.35mm)

### Typography
- **Volume Title**: 24pt Helvetica, centered
- **Chapter Title**: 18pt Helvetica-Bold
- **Body Text**: 12pt Helvetica
- **Table Cells**: 9pt Helvetica with TA_JUSTIFY alignment

### Image Sizing
- **Inline Images**: Original size, scaled down proportionally if exceeding page boundaries
- **Illustration Images**: 
  - First image: Limited to (page_height - 84pt) to fit with title
  - Subsequent images: Use full available page height
- **Aspect Ratio**: Always preserved during scaling

### Tables
- **Column Widths**: Distributed evenly across page width
- **Cell Wrapping**: Automatic text wrapping using Paragraph objects
- **Styling**: Alternating row colors (whitesmoke header, beige body)
- **Alignment**: Left-aligned content
- **Grid**: 1pt black borders

## Docker Support

The project includes Docker configuration for containerized deployment.

### Build and Run with Docker

```bash
cd web-to-reader-backend/Docker
docker compose up
```

See `Docker/README.Docker.md` for detailed Docker instructions.

## Development

### Running Tests

```bash
cd web-to-reader-backend/test
pytest
```

### Debug Mode

Run Flask in debug mode for development:

```bash
flask run --debug
```

## Error Handling

The application includes comprehensive error handling for:
- Invalid URLs
- Failed webpage fetches
- Image download failures
- PDF/EPUB generation errors
- File I/O operations

All errors return appropriate HTTP status codes and JSON error messages.

## Temporary File Management

- **Downloads Directory**: Created automatically, stores generated PDFs/EPUBs
- **Temp Images Directory**: Created automatically, stores downloaded images
- **Cleanup**: Temporary files are automatically removed after successful delivery

## CORS Configuration

The backend supports CORS with the following configuration:
- **Allowed Origins**: `*` (all origins)
- **Allowed Methods**: `POST`, `OPTIONS`
- **Allowed Headers**: `Content-Type`, `Accept`

## Limitations

- Requires valid HTML structure from source website
- Image URLs must be accessible
- Large books may take longer to process
- Memory usage scales with image count and size

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is provided as-is for educational purposes.

## Acknowledgments

- ReportLab for PDF generation capabilities
- BeautifulSoup4 for HTML parsing
- Flask community for the excellent web framework

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.

---

**Note**: This tool is designed for personal use with content you have the right to download and convert. Please respect copyright laws and website terms of service.
