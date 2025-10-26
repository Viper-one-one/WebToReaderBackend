from flask import Flask, request, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import logging
import os
import urllib.parse
from urllib.request import urlretrieve
from logging.handlers import RotatingFileHandler
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
import io
from datetime import datetime
from PIL import Image as PILImage
import tempfile
import zipfile
import shutil

app = Flask(__name__)
CORS(app, resources={
    r"/process": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    r"/get_books": {"origins": "*", "methods": ["GET", "OPTIONS"]},
    r"/download": {"origins": "*", "methods": ["POST", "OPTIONS"]}
})

# app.logger.setLevel(logging.DEBUG)

# log_dir = "app/logs" if os.path.exists("app/logs") else "."

# handler = RotatingFileHandler(os.path.join(log_dir, "debug.log"), maxBytes=0, backupCount=1)
# handler.setLevel(logging.DEBUG)
# handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# class LineCountHandler(logging.Handler):
#     def __init__(self, filename, max_lines=500):
#         super().__init__()
#         self.filename = filename
#         self.max_lines = max_lines
#         self.line_count = 0
        
#     def emit(self, record):
#         try:
#             msg = self.format(record)
#             with open(self.filename, 'a') as f:
#                 f.write(msg + '\n')
#             self.line_count += 1
            
#             if self.line_count >= self.max_lines:
#                 self._trim_file()
#                 self.line_count = 0
#         except Exception:
#             self.handleError(record)
    
#     def _trim_file(self):
#         try:
#             with open(self.filename, 'r') as f:
#                 lines = f.readlines()
#             with open(self.filename, 'w') as f:
#                 f.writelines(lines[-self.max_lines:])
#         except Exception:
#             pass

# line_handler = LineCountHandler("debug.log", max_lines=500)
# line_handler.setLevel(logging.DEBUG)
# line_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
# app.logger.addHandler(line_handler)

# utility functions
def validate_url(data):
    # app.logger.debug('Validating URL data: %s', data)
    if data is None:
        # app.logger.error("Request data is None")
        return False
    if 'url' not in data:
        # app.logger.error("Missing 'url' in request data")
        return False
    url = data['url']
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        # app.logger.error("Invalid URL format (requires http:// or https://): %s", url)
        return False
    # app.logger.debug('URL validation passed for: %s', url)
    return True

def get_webpage_content(url):
    # print(f"Fetching webpage content from URL: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Charsets': 'utf-8'
        }
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        response.encoding = 'utf-8'
        # app.logger.debug(f"Response encoding: {response.encoding}")
        # app.logger.debug(f"Apparent encoding: {response.apparent_encoding}")
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
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
        # print(f"All books found: {books}")
        return books
    except requests.RequestException as e:
        # app.logger.error(f"Error fetching URL: {e}")
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
        # app.logger.error(f"Error fetching URL: {e}")
        return None
    
def fetch_chapter(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    content = soup.find('div', class_='entry-content alignfull wp-block-post-content has-global-padding is-layout-constrained wp-block-post-content-is-layout-constrained')
    if content:
        # Find wp-block-comments divs first
        comments_divs = content.find_all('div', class_='wp-block-comments')
        
        for comments_div in comments_divs:
            # Look for sibling p elements with has-text-align-center class near this comments div
            # Check previous siblings
            prev_sibling = comments_div.find_previous_sibling()
            while prev_sibling and prev_sibling.name in ['p', 'div']:
                if (prev_sibling.name == 'p' and 
                    prev_sibling.get('class') and 
                    'has-text-align-center' in prev_sibling.get('class')):
                    prev_sibling.decompose()
                    break
                prev_sibling = prev_sibling.find_previous_sibling()
            
            # Check next siblings
            next_sibling = comments_div.find_next_sibling()
            while next_sibling and next_sibling.name in ['p', 'div']:
                if (next_sibling.name == 'p' and 
                    next_sibling.get('class') and 
                    'has-text-align-center' in next_sibling.get('class')):
                    next_sibling.decompose()
                    break
                next_sibling = next_sibling.find_next_sibling()
            
            # Remove the comments div itself
            comments_div.decompose()
    
    # Extract structured content
    structured_content = {
        'paragraphs': [],
        'inline_images': [],
        'tables': []
    }
    
    if content:
        # Process all children to preserve order and extract different content types
        for element in content.children:
            if element.name == 'p':
                # Regular paragraph
                text = element.get_text(strip=True)
                if text:
                    structured_content['paragraphs'].append(text)
            
            elif element.name == 'figure':
                # Check if it's a table
                if element.get('class') and 'wp-block-table' in element.get('class'):
                    table_elem = element.find('table')
                    if table_elem:
                        table_data = []
                        rows = table_elem.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            if row_data:
                                table_data.append(row_data)
                        if table_data:
                            structured_content['tables'].append(table_data)
                
                # Check if it's an inline image (not illustration chapter)
                elif element.get('class') and 'wp-block-image' in element.get('class'):
                    img = element.find('img')
                    if img and img.get('src'):
                        figcaption = element.find('figcaption')
                        structured_content['inline_images'].append({
                            'src': img['src'],
                            'alt': img.get('alt', ''),
                            'caption': figcaption.get_text(strip=True) if figcaption else ''
                        })
            
            elif element.name == 'img':
                # Standalone image without figure wrapper
                if element.get('src'):
                    structured_content['inline_images'].append({
                        'src': element['src'],
                        'alt': element.get('alt', ''),
                        'caption': ''
                    })
        
        return structured_content
    return None

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
        # app.logger.error(f"Error downloading image {img_url}: {e}")
        return None

def process_chapters(books):
    processed_books = {}
    for volume, links in books.items():
        # print(f"Processing {volume} with {len(links)} chapters")
        chapters = []
        text_chapter_num = 0  # Separate counter for text chapters only
        for i, link in enumerate(links, start=1):
            try:
                # Check if this is the illustrations chapter
                if '/illustrations/' in link or link.endswith('-illustrations/'):
                    # print(f"Fetching illustrations from chapter {i}: {link}")
                    illustrations = fetch_illustrations(link)
                    chapters.append({
                        'chapter_num': None,  # Illustrations don't get a number
                        'url': link,
                        'type': 'illustrations',
                        'images': illustrations
                    })
                else:
                    # print(f"Fetching chapter {i}: {link}")
                    text_chapter_num += 1  # Increment only for text chapters
                    content = fetch_chapter(link)
                    chapters.append({
                        'chapter_num': text_chapter_num,
                        'url': link,
                        'type': 'text',
                        'content': content
                    })
            except Exception as e:
                # app.logger.error(f"Error processing chapter {i} ({link}): {e}")
                continue

            processed_books[volume] = chapters
    # Log chapter 2 content for all processed books
        # for volume, chapters in processed_books.items():
        #     if len(chapters) >= 2:
        #         chapter_2 = chapters[1]  # Index 1 is chapter 2
        #         if chapter_2['type'] == 'text':
        #             app.logger.debug(f"Chapter 2 content for {volume}: {chapter_2['content'][:10]}...")
        #         elif chapter_2['type'] == 'illustrations':
        #             app.logger.debug(f"Chapter 2 for {volume} is illustrations with {len(chapter_2['images'])} images")
    return processed_books

def create_epub(books):
    # Placeholder for EPUB creation logic
    pass

def create_single_pdf(volume_name: str, chapters: list):
    """Create a PDF for a single volume."""
    # print(f"Creating PDF for volume: {volume_name}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create filename based on volume name
    safe_volume_name = volume_name.replace(' ', '_').replace('Volume_', 'Vol')
    pdf_filename = f"{safe_volume_name}_{timestamp}.pdf"
    filepath = os.path.join("downloads", pdf_filename)
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=18)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=TA_CENTER
    )

    chapter_style = ParagraphStyle(
        name='ChapterStyle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        name='BodyStyle',
        parent=styles['BodyText'],
        fontSize=12,
        spaceAfter=3
    )

    content = []
    
    # Calculate available width (page width minus margins)
    page_width = A4[0] - 108  # 54 points margin on each side = 108 total
    max_width = page_width  # Use 100% of available width
    max_height = A4[1] - 108  # Use 100% of available height

    # Add volume title
    # print(f"Adding {volume_name} to PDF")
    content.append(Paragraph(volume_name, title_style))
    content.append(Spacer(1, 12))

    for chapter in chapters:
        if chapter['type'] == 'text':
            content.append(Paragraph(f"Chapter {chapter['chapter_num']}", chapter_style))
            
            # Handle structured content with paragraphs, inline images, and tables
            chapter_content = chapter['content']
            
            if chapter_content:
                # Process paragraphs
                if 'paragraphs' in chapter_content and chapter_content['paragraphs']:
                    for para in chapter_content['paragraphs']:
                        if para.strip():
                            content.append(Paragraph(para.strip(), body_style))
                            content.append(Spacer(1, 6))
                
                # Process inline images
                if 'inline_images' in chapter_content and chapter_content['inline_images']:
                    for img_info in chapter_content['inline_images']:
                        img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_chapter{chapter['chapter_num']}_inline_{chapter_content['inline_images'].index(img_info)+1}")
                        if img_path and os.path.exists(img_path):
                            try:
                                # Get original image dimensions
                                with PILImage.open(img_path) as pil_img:
                                    orig_width, orig_height = pil_img.size
                                    aspect_ratio = orig_width / orig_height
                                
                                # Calculate dimensions while preserving aspect ratio
                                # Use smaller max size for inline images (60% of page width)
                                inline_max_width = page_width * 0.6
                                inline_max_height = max_height * 0.4
                                
                                if orig_width > orig_height:
                                    img_width = min(inline_max_width, orig_width)
                                    img_height = img_width / aspect_ratio
                                    if img_height > inline_max_height:
                                        img_height = inline_max_height
                                        img_width = img_height * aspect_ratio
                                else:
                                    img_height = min(inline_max_height, orig_height)
                                    img_width = img_height * aspect_ratio
                                    if img_width > inline_max_width:
                                        img_width = inline_max_width
                                        img_height = img_width / aspect_ratio
                                
                                img = Image(img_path, width=img_width, height=img_height)
                                content.append(img)
                                
                                if img_info.get('caption'):
                                    caption_style = ParagraphStyle(
                                        name='CaptionStyle',
                                        parent=body_style,
                                        fontSize=10,
                                        textColor=colors.grey,
                                        alignment=TA_CENTER,
                                        spaceAfter=12
                                    )
                                    content.append(Paragraph(img_info['caption'], caption_style))
                                content.append(Spacer(1, 12))
                                
                            except Exception as e:
                                # app.logger.error(f"Error processing inline image: {e}")
                                content.append(Paragraph(f"[Image: {img_info.get('alt', 'No description')}]", body_style))
                                content.append(Spacer(1, 6))
                
                # Process tables
                if 'tables' in chapter_content and chapter_content['tables']:
                    for table_data in chapter_content['tables']:
                        if table_data:  # Make sure table has rows
                            # Create ReportLab Table
                            table = Table(table_data, colWidths=[page_width / len(table_data[0])] * len(table_data[0]))
                            
                            # Apply table styling
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 10),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 1), (-1, -1), 9),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ]))
                            
                            content.append(table)
                            content.append(Spacer(1, 12))
            
            content.append(PageBreak())
        elif chapter['type'] == 'illustrations':
            content.append(Paragraph("Illustrations", chapter_style))
            
            # Calculate space available for first image (accounting for title and spacing)
            # Title takes approximately: fontSize (18) + spaceAfter (12) + some padding = ~40 points
            first_img_max_height = max_height - 84
            
            for img_info in chapter['images']:
                img_index = chapter['images'].index(img_info)
                is_first_image = (img_index == 0)
                
                img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_illustrations_{img_index+1}")
                if img_path and os.path.exists(img_path):
                    try:
                        # Get original image dimensions
                        with PILImage.open(img_path) as pil_img:
                            orig_width, orig_height = pil_img.size
                            aspect_ratio = orig_width / orig_height
                        
                        # Use reduced height for first image to fit on first page
                        img_max_height = first_img_max_height if is_first_image else max_height
                        
                        # Calculate dimensions while preserving aspect ratio
                        if orig_width > orig_height:
                            img_width = min(max_width, orig_width)
                            img_height = img_width / aspect_ratio
                            if img_height > img_max_height:
                                img_height = img_max_height
                                img_width = img_height * aspect_ratio
                        else:
                            img_height = min(img_max_height, orig_height)
                            img_width = img_height * aspect_ratio
                            if img_width > max_width:
                                img_width = max_width
                                img_height = img_width / aspect_ratio
                        
                        img_width_points = min(img_width, max_width)
                        img_height_points = min(img_height, img_max_height)
                        
                        # app.logger.debug(f"Original image size: {orig_width}x{orig_height}, PDF size: {img_width_points}x{img_height_points}")
                        
                        img = Image(img_path, width=img_width_points, height=img_height_points)
                        content.append(img)
                        
                        if img_info['caption']:
                            content.append(Paragraph(img_info['caption'], body_style))
                        content.append(Spacer(1, 12))
                        
                    except Exception as e:
                        # app.logger.error(f"Error processing image {img_path}: {e}")
                        content.append(Paragraph(f"[Image could not be loaded: {img_info.get('alt', 'No description')}]", body_style))
                        content.append(Spacer(1, 12))
            content.append(PageBreak())
    
    try:
        doc.build(content)
        # app.logger.info(f"Created PDF: {filepath}")
        return filepath
    except Exception as e:
        # app.logger.error(f"Error creating PDF for {volume_name}: {e}")
        return None

def create_pdf(books: dict):
    # print(f"Creating PDF for books: {list(books.keys())}")
    
    # Create a single PDF with all selected volumes
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create filename based on selected volumes
    volume_names = '_'.join([vol.replace(' ', '_').replace('Volume_', 'Vol') for vol in books.keys()])
    pdf_filename = f"{volume_names}_{timestamp}.pdf"
    filepath = os.path.join("downloads", pdf_filename)
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=18)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=TA_CENTER
    )

    chapter_style = ParagraphStyle(
        name='ChapterStyle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        name='BodyStyle',
        parent=styles['BodyText'],
        fontSize=12,
        spaceAfter=3
    )

    content = []
    
    # Calculate available width (page width minus margins)
    page_width = A4[0] - 108  # 54 points margin on each side = 108 total
    max_width = page_width  # Use 100% of available width
    max_height = A4[1] - 108  # Use 100% of available height

    # Process all volumes in a single PDF
    for volume, chapters in books.items():
        # print(f"Adding {volume} to PDF")
        content.append(Paragraph(volume, title_style))
        content.append(Spacer(1, 12))

        for chapter in chapters:
            if chapter['type'] == 'text':
                content.append(Paragraph(f"Chapter {chapter['chapter_num']}", chapter_style))
                
                # Handle structured content with paragraphs, inline images, and tables
                chapter_content = chapter['content']
                
                if chapter_content:
                    # Process paragraphs
                    if 'paragraphs' in chapter_content and chapter_content['paragraphs']:
                        for para in chapter_content['paragraphs']:
                            if para.strip():
                                content.append(Paragraph(para.strip(), body_style))
                                content.append(Spacer(1, 6))
                    
                    # Process inline images
                    if 'inline_images' in chapter_content and chapter_content['inline_images']:
                        for img_info in chapter_content['inline_images']:
                            safe_volume_name = volume.replace(' ', '_').replace('Volume_', 'Vol')
                            img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_chapter{chapter['chapter_num']}_inline_{chapter_content['inline_images'].index(img_info)+1}")
                            if img_path and os.path.exists(img_path):
                                try:
                                    # Get original image dimensions
                                    with PILImage.open(img_path) as pil_img:
                                        orig_width, orig_height = pil_img.size
                                        aspect_ratio = orig_width / orig_height
                                    
                                    # Calculate dimensions while preserving aspect ratio
                                    # Use smaller max size for inline images (60% of page width)
                                    inline_max_width = page_width * 0.6
                                    inline_max_height = max_height * 0.4
                                    
                                    if orig_width > orig_height:
                                        img_width = min(inline_max_width, orig_width)
                                        img_height = img_width / aspect_ratio
                                        if img_height > inline_max_height:
                                            img_height = inline_max_height
                                            img_width = img_height * aspect_ratio
                                    else:
                                        img_height = min(inline_max_height, orig_height)
                                        img_width = img_height * aspect_ratio
                                        if img_width > inline_max_width:
                                            img_width = inline_max_width
                                            img_height = img_width / aspect_ratio
                                    
                                    img = Image(img_path, width=img_width, height=img_height)
                                    content.append(img)
                                    
                                    if img_info.get('caption'):
                                        caption_style = ParagraphStyle(
                                            name='CaptionStyle',
                                            parent=body_style,
                                            fontSize=10,
                                            textColor=colors.grey,
                                            alignment=TA_CENTER,
                                            spaceAfter=12
                                        )
                                        content.append(Paragraph(img_info['caption'], caption_style))
                                    content.append(Spacer(1, 12))
                                    
                                except Exception as e:
                                    # app.logger.error(f"Error processing inline image: {e}")
                                    content.append(Paragraph(f"[Image: {img_info.get('alt', 'No description')}]", body_style))
                                    content.append(Spacer(1, 6))
                    
                    # Process tables
                    if 'tables' in chapter_content and chapter_content['tables']:
                        for table_data in chapter_content['tables']:
                            if table_data:  # Make sure table has rows
                                # Create ReportLab Table
                                table = Table(table_data, colWidths=[page_width / len(table_data[0])] * len(table_data[0]))
                                
                                # Apply table styling
                                table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ]))
                                
                                content.append(table)
                                content.append(Spacer(1, 12))
                
                content.append(PageBreak())
            elif chapter['type'] == 'illustrations':
                content.append(Paragraph("Illustrations", chapter_style))
                
                # Calculate space available for first image (accounting for title and spacing)
                # Title takes approximately: fontSize (18) + spaceAfter (12) + some padding = ~40 points
                first_img_max_height = max_height - 84
                
                for img_info in chapter['images']:
                    img_index = chapter['images'].index(img_info)
                    is_first_image = (img_index == 0)
                    
                    safe_volume_name = volume.replace(' ', '_').replace('Volume_', 'Vol')
                    img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_illustrations_{img_index+1}")
                    if img_path and os.path.exists(img_path):
                        try:
                            # Get original image dimensions
                            with PILImage.open(img_path) as pil_img:
                                orig_width, orig_height = pil_img.size
                                aspect_ratio = orig_width / orig_height
                            
                            # Use reduced height for first image to fit on first page
                            img_max_height = first_img_max_height if is_first_image else max_height
                            
                            # Calculate dimensions while preserving aspect ratio
                            if orig_width > orig_height:
                                # Landscape image - limit by width
                                img_width = min(max_width, orig_width)
                                img_height = img_width / aspect_ratio
                                
                                # If height is still too big, limit by height
                                if img_height > img_max_height:
                                    img_height = img_max_height
                                    img_width = img_height * aspect_ratio
                            else:
                                # Portrait image - limit by height
                                img_height = min(img_max_height, orig_height)
                                img_width = img_height * aspect_ratio
                                
                                # If width is still too big, limit by width
                                if img_width > max_width:
                                    img_width = max_width
                                    img_height = img_width / aspect_ratio
                            

                            # Convert pixels to points (assuming 72 DPI)
                            img_width_points = min(img_width, max_width)
                            img_height_points = min(img_height, img_max_height)
                            

                            # app.logger.debug(f"Original image size: {orig_width}x{orig_height}, PDF size: {img_width_points}x{img_height_points}")
                            

                            # Create image with preserved aspect ratio
                            img = Image(img_path, width=img_width_points, height=img_height_points)
                            content.append(img)
                            
                            if img_info['caption']:
                                content.append(Paragraph(img_info['caption'], body_style))
                            content.append(Spacer(1, 12))
                            
                        except Exception as e:
                            # app.logger.error(f"Error processing image {img_path}: {e}")
                            # Fallback: add a placeholder or skip the image
                            content.append(Paragraph(f"[Image could not be loaded: {img_info.get('alt', 'No description')}]", body_style))
                            content.append(Spacer(1, 12))
                content.append(PageBreak())
    
    try:
        doc.build(content)
        # app.logger.info(f"Created PDF: {filepath}")
        
        # Clean up temp images
        try:
            import shutil
            if os.path.exists("temp_images"):
                shutil.rmtree("temp_images")
                # app.logger.debug("Cleaned up temp images directory")
        except Exception as e:
            # app.logger.warning(f"Could not clean up temp images: {e}")
            pass
        
        return filepath
    except Exception as e:
        # app.logger.error(f"Error creating PDF: {e}")
        return None
    
def cleanup_directories():
    """Clean up downloads and temp_images directories after sending files"""
    import shutil
    try:
        if os.path.exists("downloads"):
            shutil.rmtree("downloads")
            # app.logger.debug("Cleaned up downloads directory")
    except Exception as e:
        # app.logger.warning(f"Could not clean up downloads directory: {e}")
        pass
    
    try:
        if os.path.exists("temp_images"):
            shutil.rmtree("temp_images")
            # app.logger.debug("Cleaned up temp_images directory")
    except Exception as e:
        # app.logger.warning(f"Could not clean up temp_images directory: {e}")
        pass
    

# Flask routes and request handlers
@app.route('/process', methods=['POST', 'OPTIONS'])
def process():
    # app.logger.debug('Received /process request - Method: %s', request.method)
    
    if request.method == 'OPTIONS':
        # app.logger.debug('Handling OPTIONS request')
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response
    
    # app.logger.debug('Request JSON: %s', request.json)
    if validate_url(request.json):
        url = request.json['url']
        # app.logger.debug('Processing URL: %s', url)
        books = get_book_names(url)
        
        if books is None:
            # app.logger.error('Failed to get webpage content')
            return {"error": "Failed to fetch or parse the webpage"}, 500

        volumes = [{"id": i, "title": volume} for i, volume in enumerate(books, start=1)]
        # app.logger.debug('Found %d volumes: %s', len(volumes), [v['title'] for v in volumes])
        return {"books": volumes}, 200
    else:
        # app.logger.error('URL validation failed')
        return {"error": "Invalid url"}, 400

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    # app.logger.debug('Received /download request - Method: %s', request.method)
    if request.method == 'OPTIONS':
        # app.logger.debug('Handling OPTIONS request for /download')
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response

    # app.logger.debug('Request JSON: %s', request.json)
    # print(f"Request JSON: {request.json}")

    selected_books = request.json.get('selectedBooks')
    selected_format = request.json.get('format')
    url = request.json.get('url')
    # print(f"URL for download: {url}")
    # print(f"Selected books for download: {selected_books}")
    # print(f"Selected format for download: {selected_format}")

    if not selected_books:
        return {"error": "No books selected"}, 400
    if not selected_format:
        return {"error": "No format selected"}, 400
    if not url:
        return {"error": "No URL provided"}, 400

    books = get_webpage_content(url)
    if books is None:
        # app.logger.error('Failed to get webpage content for download')
        return {"error": "Failed to fetch or parse the webpage"}, 500
    # print(f"All books fetched: {books}")
    # selected_books = ['1'] books = {'Volume 1': [...], 'Volume 2': [...]}
    selected_books = [str(i) for i in selected_books]
    filtered_books = {}
    for volume_key, chapters in books.items():
        match = re.match(r"Volume\s+(\d+)", volume_key)
        if match:
            volume_num = match.group(1)
            if volume_num in selected_books:
                filtered_books[volume_key] = chapters
    # print(f"Filtered books for processing: {filtered_books}")
    processed_books = process_chapters(filtered_books)
    # print(f"Processed books for download: {processed_books}.")
    if not processed_books:
        return {"error": "No valid books to process"}, 400
    
    # Create separate PDFs for each book
    pdf_paths = []
    if selected_format == 'PDF' or selected_format == 'pdf':
        # print("Creating separate PDFs for each book...")
        for volume_name, chapters in processed_books.items():
            pdf_path = create_single_pdf(volume_name, chapters)
            if pdf_path:
                pdf_paths.append(pdf_path)
        
        if not pdf_paths:
            return {"error": "Failed to create PDFs"}, 500
        
        # Clean up temp images after all PDFs are created
        try:
            if os.path.exists("temp_images"):
                shutil.rmtree("temp_images")
                # app.logger.debug("Cleaned up temp images directory")
        except Exception as e:
            # app.logger.warning(f"Could not clean up temp images: {e}")
            pass
        
        # If only one book, send it directly
        if len(pdf_paths) == 1:
            return send_file(pdf_paths[0], as_attachment=True, download_name=os.path.basename(pdf_paths[0]), mimetype='application/pdf')
        
        # If multiple books, create a zip file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"books_{timestamp}.zip"
        zip_filepath = os.path.join("downloads", zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_path in pdf_paths:
                zipf.write(pdf_path, os.path.basename(pdf_path))
        
        # Clean up individual PDFs after zipping
        for pdf_path in pdf_paths:
            try:
                os.remove(pdf_path)
            except Exception as e:
                # app.logger.warning(f"Could not remove {pdf_path}: {e}")
                pass
        
        return send_file(zip_filepath, as_attachment=True, download_name=zip_filename, mimetype='application/zip')
        
    elif selected_format == 'EPUB' or selected_format == 'epub':
        path = create_epub(processed_books)
        if not path:
            return {"error": "Failed to create EPUB"}, 500
        return send_file(path, as_attachment=True, download_name=os.path.basename(path))
    
    return {"error": "Unsupported format"}, 400
    

@app.before_request
def log_request_info():
    # app.logger.debug('Headers: %s', request.headers)
    # app.logger.debug('Body: %s', request.get_data())
    # app.logger.debug('Request method: %s', request.method)
    
    # Only try to access JSON for POST requests with JSON content type
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = request.json
            # print(f"Request data: {data}")
            pass
        except Exception as e:
            # app.logger.debug('Could not parse JSON: %s', e)
            pass
    else:
        # app.logger.debug('Skipping JSON parsing for %s request', request.method)
        pass

@app.after_request
def log_response_info(response):
    # app.logger.debug('Response status: %s', response.status)
    # app.logger.debug('Response headers: %s', response.headers)
    try:
        response_data = response.get_data(as_text=True)
        # app.logger.debug('Response body: %s', response_data)
        # print(f"Response body: {response_data}")
    except Exception as e:
        # app.logger.debug('Could not log response body: %s', e)
        pass
    return response
