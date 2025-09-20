from flask import Flask, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app)

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())
    app.logger.debug('Request method: %s', request.method)
    data = request.json
    print(f"Request data: {data}")

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
        print(f"All books found: {books}")
        return books
    except requests.RequestException as e:
        app.logger.error(f"Error fetching URL: {e}")
        return None
    
def fetch_chapter(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    content = soup.find('div', class_='entry-content alignfull wp-block-post-content has-global-padding is-layout-constrained wp-block-post-content-is-layout-constrained').get_text(separator='\n')
    return content.strip()

@app.after_request
def log_response_info(response):
    app.logger.debug('Response status: %s', response.status)
    app.logger.debug('Response body: %s', response.get_data())
    print(f"Response: {response.json}")
    return response

@app.route('/process', methods=['POST', 'OPTIONS'])
def process():
    if validate_url(request.json):
        url = request.json['url']
        books = get_webpage_content(url)
        
        if books is None:
            return {"error": "Failed to fetch or parse the webpage"}, 500
        if request.json['format'] == 'PDF':
            print("PDF format requested, but not implemented.")
        if request.json['format'] == 'EPUB':
            print("EPUB format requested, but not implemented.")
        return {"books": books}, 200
    else:
        return {"error": "Invalid url"}, 200
    