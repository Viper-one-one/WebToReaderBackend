from flask import Flask, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import logging
import os
import urllib.parse
from urllib.request import urlretrieve
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
CORS(app, resources={
    r"/process": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    r"/get_books": {"origins": "*", "methods": ["GET", "OPTIONS"]},
    r"/download": {"origins": "*", "methods": ["POST", "OPTIONS"]}
})

app.debug = True
app.logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler("debug.log", maxBytes=0, backupCount=1)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

class LineCountHandler(logging.Handler):
    def __init__(self, filename, max_lines=500):
        super().__init__()
        self.filename = filename
        self.max_lines = max_lines
        self.line_count = 0
        
    def emit(self, record):
        try:
            msg = self.format(record)
            with open(self.filename, 'a') as f:
                f.write(msg + '\n')
            self.line_count += 1
            
            if self.line_count >= self.max_lines:
                self._trim_file()
                self.line_count = 0
        except Exception:
            self.handleError(record)
    
    def _trim_file(self):
        try:
            with open(self.filename, 'r') as f:
                lines = f.readlines()
            with open(self.filename, 'w') as f:
                f.writelines(lines[-self.max_lines:])
        except Exception:
            pass

line_handler = LineCountHandler("debug.log", max_lines=500)
line_handler.setLevel(logging.DEBUG)
line_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(line_handler)

# utility functions
def validate_url(data):
    app.logger.debug('Validating URL data: %s', data)
    if data is None:
        app.logger.error("Request data is None")
        return False
    if 'url' not in data:
        app.logger.error("Missing 'url' in request data")
        return False
    url = data['url']
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        app.logger.error("Invalid URL format (requires http:// or https://): %s", url)
        return False
    app.logger.debug('URL validation passed for: %s', url)
    return True

def get_webpage_content(url):
    print(f"Fetching webpage content from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        books = {}
        for h3 in soup.find_all('h3'):
            if re.match(r"Volume\s+\d+", h3.text.strip()):
                volume_title = h3.text.strip()
                container = h3.find_next_sibling('div')
                if container:
                    inner_div = container.find('div')
                    if inner_div:
                        chapter_links = [a['href'] for p in inner_div.find_all('p') for a in p.find_all('a', href=True)]
                        books[volume_title] = chapter_links
        #print(f"All books found: {books}")
        return books
    except requests.RequestException as e:
        app.logger.error(f"Error fetching URL: {e}")
        return None
    
def get_book_names(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        book_titles = {}
        for h3 in soup.find_all('h3'):
            if re.match(r"Volume\s+\d+", h3.text.strip()):
                volume_title = h3.text.strip()
                book_titles[volume_title] = True
        return list(book_titles.keys())
    except requests.RequestException as e:
        app.logger.error(f"Error fetching URL: {e}")
        return None
    
def fetch_chapter(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    content = soup.find('div', class_='entry-content alignfull wp-block-post-content has-global-padding is-layout-constrained wp-block-post-content-is-layout-constrained').get_text(separator='\n')
    return content.strip()

def fetch_illustrations(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    images = []
    
    content_div = soup.find('div', class_='entry-content alignfull wp-block-post-content has-global-padding is-layout-constrained wp-block-post-content-is-layout-constrained')
    if content_div:
        img_figures = content_div.find_all('figure', class_='wp-block-image')
        for figure in img_figures:
            img = figure.find('img')
            if img and img.get('src'):
                images.append({
                    'src': img['src'],
                    'alt': img.get('alt', ''),
                    'caption': figure.find('figcaption').get_text(strip=True) if figure.find('figcaption') else ''
                })
    
    return images

def download_image(img_url, save_dir, filename):
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        parsed_url = urllib.parse.urlparse(img_url)
        ext = os.path.splitext(parsed_url.path)[1]
        if not ext:
            ext = '.jpg'
        
        filepath = os.path.join(save_dir, f"{filename}{ext}")
        urlretrieve(img_url, filepath)
        return filepath
    except Exception as e:
        app.logger.error(f"Error downloading image {img_url}: {e}")
        return None

def process_chapters(books):
    processed_books = {}
    for volume, links in books.items():
        print(f"Processing {volume} with {len(links)} chapters")
        chapters = []
        
        for i, link in enumerate(links, start=1):
            pass
    return processed_books

def create_epub(books):
    # Placeholder for EPUB creation logic
    pass

def create_pdf(books):
    # Placeholder for PDF creation logic
    pass

# Flask routes and request handlers
@app.route('/process', methods=['POST', 'OPTIONS'])
def process():
    app.logger.debug('Received /process request - Method: %s', request.method)
    
    if request.method == 'OPTIONS':
        app.logger.debug('Handling OPTIONS request')
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response
    
    app.logger.debug('Request JSON: %s', request.json)
    if validate_url(request.json):
        url = request.json['url']
        app.logger.debug('Processing URL: %s', url)
        books = get_book_names(url)
        
        if books is None:
            app.logger.error('Failed to get webpage content')
            return {"error": "Failed to fetch or parse the webpage"}, 500

        volumes = [{"id": i, "title": volume} for i, volume in enumerate(books, start=1)]
        app.logger.debug('Found %d volumes: %s', len(volumes), [v['title'] for v in volumes])
        return {"books": volumes}, 200
    else:
        app.logger.error('URL validation failed')
        return {"error": "Invalid url"}, 400

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    app.logger.debug('Received /download request - Method: %s', request.method)
    if request.method == 'OPTIONS':
        app.logger.debug('Handling OPTIONS request for /download')
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response

    app.logger.debug('Request JSON: %s', request.json)
    print(f"Request JSON: {request.json}")

    selected_books = request.json.get('selectedBooks')
    selected_format = request.json.get('format')
    url = request.json.get('url')
    print(f"URL for download: {url}")
    print(f"Selected books for download: {selected_books}")
    print(f"Selected format for download: {selected_format}")

    if not selected_books:
        return {"error": "No books selected"}, 400
    if not selected_format:
        return {"error": "No format selected"}, 400
    if not url:
        return {"error": "No URL provided"}, 400

    books = get_webpage_content(url)
    if books is None:
        app.logger.error('Failed to get webpage content for download')
        return {"error": "Failed to fetch or parse the webpage"}, 500
    print(f"All books fetched: {books}")
    
    processed_books = process_chapters({k: books[k] for k in selected_books if k in books})
    # error here no valid books returned
    if not processed_books:
        return {"error": "No valid books to process"}, 400
    print(f"Processed books: {processed_books}")
    
    if processed_books:
        first_book = next(iter(processed_books.values()))
        content_preview = str(first_book)[:500]
        print(f"First book content (first 500 chars): {content_preview}")
    return {"message": "Download endpoint"}, 200

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())
    app.logger.debug('Request method: %s', request.method)
    
    # Only try to access JSON for POST requests with JSON content type
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = request.json
            print(f"Request data: {data}")
        except Exception as e:
            app.logger.debug('Could not parse JSON: %s', e)
    else:
        app.logger.debug('Skipping JSON parsing for %s request', request.method)

@app.after_request
def log_response_info(response):
    app.logger.debug('Response status: %s', response.status)
    app.logger.debug('Response headers: %s', response.headers)
    try:
        response_data = response.get_data(as_text=True)
        app.logger.debug('Response body: %s', response_data)
        print(f"Response body: {response_data}")
    except Exception as e:
        app.logger.debug('Could not log response body: %s', e)
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)