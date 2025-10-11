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
CORS(app)
handler = RotatingFileHandler("debug.log", maxBytes=0, backupCount=1)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Custom handler that limits to 500 lines
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

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())
    app.logger.debug('Request method: %s', request.method)
    data = request.json
    print(f"Request data: {data}")

@app.after_request
def log_response_info(response):
    app.logger.debug('Response status: %s', response.status)
    app.logger.debug('Response body: %s', response.get_data())
    print(f"Response: {response.json}")
    return response

def validate_url(data):
    if 'url' not in data:
        app.logger.error("Missing 'url' in request data")
        return False
    url = data['url']
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        app.logger.error("Invalid URL format (requires http:// or https://)")
        return False
    return True

def get_webpage_content(url):
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
        
        # Get file extension from URL
        parsed_url = urllib.parse.urlparse(img_url)
        ext = os.path.splitext(parsed_url.path)[1]
        if not ext:
            ext = '.jpg'  # Default extension
        
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

@app.route('/process', methods=['POST', 'OPTIONS'])
def process():
    if validate_url(request.json):
        url = request.json['url']
        books = get_webpage_content(url)
        
        if books is None:
            return {"error": "Failed to fetch or parse the webpage"}, 500
        volumes = [{"id": i, "title": volume} for i, volume in enumerate(books.keys(), start=1)]
        return {"books": volumes}, 200
    else:
        return {"error": "Invalid url"}, 200
    
@app.route('/get_books', methods=['GET', 'OPTIONS'])
def get_books():
    if validate_url(request.json):
        url = request.json['url']
        books = get_webpage_content(url)
        
        if books is None:
            return {"error": "Failed to fetch or parse the webpage"}, 500
        volumes = [{"id": i, "title": volume} for i, volume in enumerate(books.keys(), start=1)]
        return {"books": volumes}, 200

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    # Placeholder for download logic
    return {"message": "Download endpoint"}, 200