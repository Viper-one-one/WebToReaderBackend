from flask import Flask, request, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os
import urllib.parse
from urllib.request import urlretrieve
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
from datetime import datetime
from PIL import Image as PILImage
import zipfile
import shutil

app = Flask(__name__)
CORS(app, resources={
    r"/process": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    r"/get_books": {"origins": "*", "methods": ["GET", "OPTIONS"]},
    r"/download": {"origins": "*", "methods": ["POST", "OPTIONS"]}
})
def validate_url(data):
    if data is None:
        return False
    if 'url' not in data:
        return False
    url = data['url']
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return False
    return True

def get_webpage_content(url):
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
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
        books = {}
        for h3 in soup.find_all('h3'):
            if re.match(r"Volume\s+\d+", h3.text.strip()):
                volume_title = h3.text.strip()
                container = h3.find_next_sibling('div')
                if container:
                    inner_div = container.find('div')
                    if inner_div:
                        chapter_data = []
                        for p in inner_div.find_all('p'):
                            for a in p.find_all('a', href=True):
                                chapter_name = a.get_text(strip=True)
                                chapter_url = a['href']
                                chapter_data.append({
                                    'name': chapter_name,
                                    'url': chapter_url
                                })
                        books[volume_title] = chapter_data
        return books
    except requests.RequestException as e:
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
        return None
    
def fetch_chapter(url):
    print(f"Fetching chapter from URL: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    content = soup.find('div', class_='entry-content alignfull wp-block-post-content has-global-padding is-layout-constrained wp-block-post-content-is-layout-constrained')
    if content:
        comments_divs = content.find_all('div', class_='wp-block-comments')
        
        for comments_div in comments_divs:
            prev_sibling = comments_div.find_previous_sibling()
            while prev_sibling and prev_sibling.name in ['p', 'div']:
                if (prev_sibling.name == 'p' and 
                    prev_sibling.get('class') and 
                    'has-text-align-center' in prev_sibling.get('class')):
                    prev_sibling.decompose()
                    break
                prev_sibling = prev_sibling.find_previous_sibling()
            
            next_sibling = comments_div.find_next_sibling()
            while next_sibling and next_sibling.name in ['p', 'div']:
                if (next_sibling.name == 'p' and 
                    next_sibling.get('class') and 
                    'has-text-align-center' in next_sibling.get('class')):
                    next_sibling.decompose()
                    break
                next_sibling = next_sibling.find_next_sibling()
            
            comments_div.decompose()
    
    structured_content = {
        'paragraphs': [],
        'inline_images': [],
        'tables': []
    }
    
    if content:
        for element in content.children:
            if element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    structured_content['paragraphs'].append(text)
            
            elif element.name == 'figure':
                if element.get('class') and 'wp-block-table' in element.get('class'):
                    table_elem = element.find('table')
                    if table_elem:
                        table_data = []
                        rows = table_elem.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = []
                            for cell in cells:
                                for br in cell.find_all('br'):
                                    br.replace_with('\n')
                                cell_text = cell.get_text()
                                row_data.append(cell_text)
                            if row_data:
                                table_data.append(row_data)
                        if table_data:
                            structured_content['tables'].append(table_data)
                
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
        return None

def process_chapters(books):
    processed_books = {}
    for volume, chapter_list in books.items():
        chapters = []
        text_chapter_num = 0
        for i, chapter_data in enumerate(chapter_list, start=1):
            try:
                link = chapter_data['url']
                name = chapter_data['name']
                
                if '/illustrations/' in link or link.endswith('-illustrations/'):
                    illustrations = fetch_illustrations(link)
                    chapters.append({
                        'chapter_num': None,
                        'chapter_name': name,
                        'url': link,
                        'type': 'illustrations',
                        'images': illustrations
                    })
                else:
                    text_chapter_num += 1
                    content = fetch_chapter(link)
                    chapters.append({
                        'chapter_num': text_chapter_num,
                        'chapter_name': name,
                        'url': link,
                        'type': 'text',
                        'content': content
                    })
            except Exception as e:
                continue

            processed_books[volume] = chapters
    return processed_books

def create_epub(books):
    pass

def create_single_pdf(volume_name: str, chapters: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    
    page_width = A4[0] - 108
    max_width = page_width
    max_height = A4[1] - 108

    content.append(Paragraph(volume_name, title_style))
    content.append(Spacer(1, 12))

    for chapter in chapters:
        if chapter['type'] == 'text':
            chapter_title = chapter.get('chapter_name', f"Chapter {chapter['chapter_num']}")
            content.append(Paragraph(chapter_title, chapter_style))
            
            chapter_content = chapter['content']
            
            if chapter_content:
                if 'paragraphs' in chapter_content and chapter_content['paragraphs']:
                    for para in chapter_content['paragraphs']:
                        if para.strip():
                            content.append(Paragraph(para.strip(), body_style))
                            content.append(Spacer(1, 6))
                
                if 'inline_images' in chapter_content and chapter_content['inline_images']:
                    for img_info in chapter_content['inline_images']:
                        img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_chapter{chapter['chapter_num']}_inline_{chapter_content['inline_images'].index(img_info)+1}")
                        if img_path and os.path.exists(img_path):
                            try:
                                with PILImage.open(img_path) as pil_img:
                                    orig_width, orig_height = pil_img.size
                                    aspect_ratio = orig_width / orig_height
                                
                                if orig_width > max_width or orig_height > max_height:
                                    if orig_width > orig_height:
                                        img_width = max_width
                                        img_height = img_width / aspect_ratio
                                        if img_height > max_height:
                                            img_height = max_height
                                            img_width = img_height * aspect_ratio
                                    else:
                                        img_height = max_height
                                        img_width = img_height * aspect_ratio
                                        if img_width > max_width:
                                            img_width = max_width
                                            img_height = img_width / aspect_ratio
                                else:
                                    img_width = orig_width
                                    img_height = orig_height
                                
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
                                content.append(Paragraph(f"[Image: {img_info.get('alt', 'No description')}]", body_style))
                                content.append(Spacer(1, 6))
                
                if 'tables' in chapter_content and chapter_content['tables']:
                    for table_data in chapter_content['tables']:
                        if table_data:
                            wrapped_table_data = []
                            cell_style = ParagraphStyle(
                                name='TableCellStyle',
                                parent=body_style,
                                fontSize=9,
                                leading=11,
                                alignment=TA_JUSTIFY
                            )
                            
                            for row in table_data:
                                wrapped_row = []
                                for cell in row:
                                    cell_html = str(cell).replace('\n', '<br/>')
                                    wrapped_row.append(Paragraph(cell_html, cell_style))
                                wrapped_table_data.append(wrapped_row)
                            
                            num_cols = len(table_data[0])
                            col_width = page_width / num_cols
                            
                            table = Table(wrapped_table_data, colWidths=[col_width] * num_cols)
                            
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 10),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('TOPPADDING', (0, 0), (-1, -1), 6),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ]))
                            
                            content.append(table)
                            content.append(Spacer(1, 12))
            
            content.append(PageBreak())
        elif chapter['type'] == 'illustrations':
            illustrations_title = chapter.get('chapter_name', 'Illustrations')
            content.append(Paragraph(illustrations_title, chapter_style))
            
            first_img_max_height = max_height - 84
            
            for img_info in chapter['images']:
                img_index = chapter['images'].index(img_info)
                is_first_image = (img_index == 0)
                
                img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_illustrations_{img_index+1}")
                if img_path and os.path.exists(img_path):
                    try:
                        with PILImage.open(img_path) as pil_img:
                            orig_width, orig_height = pil_img.size
                            aspect_ratio = orig_width / orig_height
                        
                        img_max_height = first_img_max_height if is_first_image else max_height
                        
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
                        
                        img = Image(img_path, width=img_width_points, height=img_height_points)
                        content.append(img)
                        
                        if img_info['caption']:
                            content.append(Paragraph(img_info['caption'], body_style))
                        content.append(Spacer(1, 12))
                        
                    except Exception as e:
                        content.append(Paragraph(f"[Image could not be loaded: {img_info.get('alt', 'No description')}]", body_style))
                        content.append(Spacer(1, 12))
            content.append(PageBreak())
    
    try:
        doc.build(content)
        return filepath
    except Exception as e:
        return None

def create_pdf(books: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    
    page_width = A4[0] - 108
    max_width = page_width
    max_height = A4[1] - 108

    for volume, chapters in books.items():
        content.append(Paragraph(volume, title_style))
        content.append(Spacer(1, 12))

        for chapter in chapters:
            if chapter['type'] == 'text':
                chapter_title = chapter.get('chapter_name', f"Chapter {chapter['chapter_num']}")
                content.append(Paragraph(chapter_title, chapter_style))
                
                chapter_content = chapter['content']
                
                if chapter_content:
                    if 'paragraphs' in chapter_content and chapter_content['paragraphs']:
                        for para in chapter_content['paragraphs']:
                            if para.strip():
                                content.append(Paragraph(para.strip(), body_style))
                                content.append(Spacer(1, 6))
                    
                    if 'inline_images' in chapter_content and chapter_content['inline_images']:
                        for img_info in chapter_content['inline_images']:
                            safe_volume_name = volume.replace(' ', '_').replace('Volume_', 'Vol')
                            img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_chapter{chapter['chapter_num']}_inline_{chapter_content['inline_images'].index(img_info)+1}")
                            if img_path and os.path.exists(img_path):
                                try:
                                    with PILImage.open(img_path) as pil_img:
                                        orig_width, orig_height = pil_img.size
                                        aspect_ratio = orig_width / orig_height
                                    
                                    if orig_width > max_width or orig_height > max_height:
                                        if orig_width > orig_height:
                                            img_width = max_width
                                            img_height = img_width / aspect_ratio
                                            if img_height > max_height:
                                                img_height = max_height
                                                img_width = img_height * aspect_ratio
                                        else:
                                            img_height = max_height
                                            img_width = img_height * aspect_ratio
                                            if img_width > max_width:
                                                img_width = max_width
                                                img_height = img_width / aspect_ratio
                                    else:
                                        img_width = orig_width
                                        img_height = orig_height
                                    
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
                                    content.append(Paragraph(f"[Image: {img_info.get('alt', 'No description')}]", body_style))
                                    content.append(Spacer(1, 6))
                    
                    if 'tables' in chapter_content and chapter_content['tables']:
                        for table_data in chapter_content['tables']:
                            if table_data:
                                wrapped_table_data = []
                                cell_style = ParagraphStyle(
                                    name='TableCellStyle',
                                    parent=body_style,
                                    fontSize=9,
                                    leading=11,
                                    alignment=TA_JUSTIFY
                                )
                                
                                for row in table_data:
                                    wrapped_row = []
                                    for cell in row:
                                        cell_html = str(cell).replace('\n', '<br/>')
                                        wrapped_row.append(Paragraph(cell_html, cell_style))
                                    wrapped_table_data.append(wrapped_row)
                                
                                num_cols = len(table_data[0])
                                col_width = page_width / num_cols
                                
                                table = Table(wrapped_table_data, colWidths=[col_width] * num_cols)
                                
                                table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ]))
                                
                                content.append(table)
                                content.append(Spacer(1, 12))
                
                content.append(PageBreak())
            elif chapter['type'] == 'illustrations':
                illustrations_title = chapter.get('chapter_name', 'Illustrations')
                content.append(Paragraph(illustrations_title, chapter_style))
                
                first_img_max_height = max_height - 84
                
                for img_info in chapter['images']:
                    img_index = chapter['images'].index(img_info)
                    is_first_image = (img_index == 0)
                    
                    safe_volume_name = volume.replace(' ', '_').replace('Volume_', 'Vol')
                    img_path = download_image(img_info['src'], "temp_images", f"{safe_volume_name}_illustrations_{img_index+1}")
                    if img_path and os.path.exists(img_path):
                        try:
                            with PILImage.open(img_path) as pil_img:
                                orig_width, orig_height = pil_img.size
                                aspect_ratio = orig_width / orig_height
                            
                            img_max_height = first_img_max_height if is_first_image else max_height
                            
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
                            
                            img = Image(img_path, width=img_width_points, height=img_height_points)
                            content.append(img)
                            
                            if img_info['caption']:
                                content.append(Paragraph(img_info['caption'], body_style))
                            content.append(Spacer(1, 12))
                            
                        except Exception as e:
                            content.append(Paragraph(f"[Image could not be loaded: {img_info.get('alt', 'No description')}]", body_style))
                            content.append(Spacer(1, 12))
                content.append(PageBreak())
    
    try:
        doc.build(content)
        
        try:
            import shutil
            if os.path.exists("temp_images"):
                shutil.rmtree("temp_images")
        except Exception as e:
            pass
        
        return filepath
    except Exception as e:
        return None
    
def cleanup_directories():
    import shutil
    try:
        if os.path.exists("downloads"):
            shutil.rmtree("downloads")
    except Exception as e:
        pass
    
    try:
        if os.path.exists("temp_images"):
            shutil.rmtree("temp_images")
    except Exception as e:
        pass
    

@app.route('/process', methods=['POST', 'OPTIONS'])
def process():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response
    
    if validate_url(request.json):
        url = request.json['url']
        books = get_book_names(url)
        
        if books is None:
            return {"error": "Failed to fetch or parse the webpage"}, 500

        volumes = [{"id": i, "title": volume} for i, volume in enumerate(books, start=1)]
        return {"books": volumes}, 200
    else:
        return {"error": "Invalid url"}, 400

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        headers = response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response

    selected_books = request.json.get('selectedBooks')
    selected_format = request.json.get('format')
    url = request.json.get('url')

    if not selected_books:
        return {"error": "No books selected"}, 400
    if not selected_format:
        return {"error": "No format selected"}, 400
    if not url:
        return {"error": "No URL provided"}, 400

    books = get_webpage_content(url)
    if books is None:
        return {"error": "Failed to fetch or parse the webpage"}, 500
    selected_books = [str(i) for i in selected_books]
    filtered_books = {}
    for volume_key, chapters in books.items():
        match = re.match(r"Volume\s+(\d+)", volume_key)
        if match:
            volume_num = match.group(1)
            if volume_num in selected_books:
                filtered_books[volume_key] = chapters
    processed_books = process_chapters(filtered_books)
    if not processed_books:
        return {"error": "No valid books to process"}, 400
    
    pdf_paths = []
    if selected_format == 'PDF' or selected_format == 'pdf':
        for volume_name, chapters in processed_books.items():
            pdf_path = create_single_pdf(volume_name, chapters)
            if pdf_path:
                pdf_paths.append(pdf_path)
        
        if not pdf_paths:
            return {"error": "Failed to create PDFs"}, 500
        
        try:
            if os.path.exists("temp_images"):
                shutil.rmtree("temp_images")
        except Exception as e:
            pass
        
        if len(pdf_paths) == 1:
            return send_file(pdf_paths[0], as_attachment=True, download_name=os.path.basename(pdf_paths[0]), mimetype='application/pdf')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"books_{timestamp}.zip"
        zip_filepath = os.path.join("downloads", zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_path in pdf_paths:
                zipf.write(pdf_path, os.path.basename(pdf_path))
        
        for pdf_path in pdf_paths:
            try:
                os.remove(pdf_path)
            except Exception as e:
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
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = request.json
            pass
        except Exception as e:
            pass
    else:
        pass

@app.after_request
def log_response_info(response):
    try:
        response_data = response.get_data(as_text=True)
    except Exception as e:
        pass
    return response
