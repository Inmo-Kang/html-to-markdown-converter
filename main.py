# main.py (텍스트 파싱 강화 + 이미지 하단 목록화 유지)

import time
import os
import re
import argparse
from urllib.parse import urljoin, urlparse

print("진단: 스크립트 최상단 - 기본 모듈 임포트 시작") 

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup, NavigableString, Tag 
import requests

print("진단: 스크립트 최상단 - 모든 모듈 임포트 완료")

# --- 유틸리티 함수 ---
def sanitize_text_for_filename(text: str, replacement: str = "_", max_length: int = 50) -> str:
    if not text:
        return ""
    sanitized = re.sub(r'[^\w\s\-\u3131-\uD7A3]', replacement, str(text).strip())
    sanitized = re.sub(r'\s+', replacement, sanitized) 
    return sanitized[:max_length].rstrip(replacement).strip('_')

print("진단: 스크립트 최상단 - 유틸리티 함수 정의 완료")

# --- Selenium 및 이미지 정보 추출 ---
def fetch_html_and_image_data(url: str, driver_service: Service, base_page_url: str) -> tuple[str | None, list[dict], str | None]:
    # (이전 답변의 함수 내용과 동일 - 변경 없음)
    print(f"  진단: fetch_html_and_image_data 함수 시작 - URL: {url}")
    print(f"[{url}] Selenium으로 접속 및 이미지 정보 추출 시도...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
    driver = None
    images_to_download = []
    page_title_from_tag = None
    try:
        driver = webdriver.Chrome(service=driver_service, options=chrome_options)
        print(f"    진단: Chrome 드라이버 생성 완료")
        driver.set_page_load_timeout(60)
        driver.get(url)
        print(f"    진단: 페이지 GET 요청 완료: {url}")
        try:
            page_title_from_tag = driver.title
            if not page_title_from_tag:
                 h1_element_for_title = driver.find_element(By.CSS_SELECTOR, "h1.page-title")
                 if h1_element_for_title: page_title_from_tag = h1_element_for_title.text
            print(f"    진단: 페이지 제목 태그에서 가져온 제목: {page_title_from_tag}")
        except Exception as title_e:
            print(f"    진단: 페이지 제목 가져오기 실패 (오류 무시): {title_e}")
            pass 
        if page_title_from_tag and \
           any(err_keyword in page_title_from_tag.lower() for err_keyword in ["404", "page not found", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다."]):
            print(f"  경고: [{url}] 페이지가 404 또는 오류 페이지일 수 있습니다. (제목: {page_title_from_tag})")
            html_content_for_404 = driver.page_source
            return html_content_for_404, [], page_title_from_tag
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located(( By.CSS_SELECTOR, "h1.page-title, div.content, main, div.dexter-FlexContainer-Items > div.position")))
        print(f"    진단: 주요 콘텐츠 영역/요소 대기 완료")
        main_content_selectors_for_selenium = [
            'div.dexter-FlexContainer-Items > div.position div.aem-Grid[class*="aem-Grid--default"]',
            'main div.content div.aem-Grid[class*="aem-Grid--default"]',
            'div.dexter-FlexContainer-Items > div.position', 'main' ]
        container_element_for_imgs = None
        for selector in main_content_selectors_for_selenium:
            try:
                container_element_for_imgs = driver.find_element(By.CSS_SELECTOR, selector)
                if container_element_for_imgs:
                    print(f"  - 이미지 검색을 위한 컨테이너 찾음 (Selenium): {selector}")
                    break
            except: continue
        selenium_images = []
        if container_element_for_imgs:
            selenium_images = container_element_for_imgs.find_elements(By.TAG_NAME, 'img')
        else:
            print(f"  - 경고: 주요 이미지 컨테이너를 찾지 못했습니다 (Selenium). 페이지 전체에서 이미지를 검색합니다.")
            selenium_images = driver.find_elements(By.TAG_NAME, 'img')
        print(f"    진단: 찾은 <img> 태그 수 (필터링 전): {len(selenium_images)}")
        for idx, img_element in enumerate(selenium_images):
            try:
                src = img_element.get_attribute('src')
                if not src or src.startswith('data:image'): continue
                parsed_src = urlparse(src)
                if not parsed_src.scheme and not parsed_src.netloc and not src.startswith('/'):
                    print(f"  - 유효하지 않은 이미지 src 건너뜀: {src}")
                    continue
                width = 0
                try: 
                    width_str = img_element.get_attribute('naturalWidth')
                    if width_str and width_str.isdigit(): width = int(width_str)
                except Exception: pass                 
                if width < 200:
                    try:
                        style_width_str = img_element.value_of_css_property('width')
                        if style_width_str and 'px' in style_width_str:
                            width = int(float(style_width_str.replace('px','').strip()))
                    except Exception: pass                
                if width < 200:
                    try:
                        attr_width_str = img_element.get_attribute('width')
                        if attr_width_str and attr_width_str.isdigit():
                            width = int(attr_width_str)
                    except Exception: pass                            
                if width >= 200:
                    alt = img_element.get_attribute('alt') or ""
                    absolute_src = urljoin(base_page_url, src) 
                    images_to_download.append({'original_src': src, 'absolute_src': absolute_src,'alt': alt})
            except Exception as e_img_loop: print(f"  - 개별 이미지 요소 처리 중 오류: {e_img_loop}")
        html_content = driver.page_source
        print(f"[{url}] HTML 가져오기 및 이미지 후보 {len(images_to_download)}개 목록화 성공!")
        return html_content, images_to_download, page_title_from_tag
    except Exception as e_main_fetch:
        print(f"[{url}] 오류: Selenium으로 페이지를 가져오는 데 실패했습니다 - {e_main_fetch}")
        return None, [], page_title_from_tag
    finally:
        if driver:
            print(f"    진단: Chrome 드라이버 종료 시도")
            driver.quit()
            print(f"    진단: Chrome 드라이버 종료 완료")

# --- 이미지 다운로드 및 처리 ---
def download_and_save_images(images_data: list, page_title_main: str, page_images_folder_abs_path: str, md_page_images_folder_name: str) -> dict:
    # (이전 답변의 함수 내용과 동일 - 변경 없음)
    if not images_data: return {}
    os.makedirs(page_images_folder_abs_path, exist_ok=True)
    image_references = {} 
    page_title_for_filename = sanitize_text_for_filename(page_title_main, max_length=40)
    for i, img_data in enumerate(images_data):
        original_src = img_data['original_src']
        absolute_src = img_data['absolute_src']
        alt_text = img_data['alt']
        sanitized_alt = sanitize_text_for_filename(alt_text if alt_text else "image", max_length=25)
        if not sanitized_alt: sanitized_alt = "image"
        try:
            response = requests.get(absolute_src, stream=True, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get('content-type')
            extension = '.jpg' 
            if content_type:
                ct_lower = content_type.lower()
                if 'jpeg' in ct_lower: extension = '.jpg'
                elif 'png' in ct_lower: extension = '.png'
                elif 'gif' in ct_lower: extension = '.gif'
                elif 'webp' in ct_lower: extension = '.webp'
                elif 'svg' in ct_lower: extension = '.svg'
            else:
                parsed_url_path = urlparse(absolute_src).path
                _, ext_from_url = os.path.splitext(parsed_url_path)
                if ext_from_url and ext_from_url.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                    extension = ext_from_url.lower()
            local_filename_base = f"{page_title_for_filename}_{sanitized_alt}_{i+1:02d}"
            local_filename = local_filename_base + extension
            local_filepath_abs = os.path.join(page_images_folder_abs_path, local_filename)
            md_relative_image_path = f"{md_page_images_folder_name}/{local_filename}"
            with open(local_filepath_abs, 'wb') as f:
                for chunk in response.iter_content(8192): f.write(chunk)
            print(f"    성공: '{local_filename}' 저장됨 ({page_images_folder_abs_path})")
            image_references[original_src] = { 
                'md_relative_path': md_relative_image_path, 'alt': alt_text, 
                'original_url': absolute_src, 'download_failed': False }
        except Exception as e_download:
            print(f"    실패: 이미지 다운로드 중 오류 - {absolute_src} ({e_download})")
            image_references[original_src] = {
                'md_relative_path': IMAGE_DOWNLOAD_FAILED_PLACEHOLDER, 'alt': alt_text, 
                'original_url': absolute_src, 'download_failed': True }
    return image_references


# --- 마크다운 파싱 및 생성 (사용자님이 제공한 이전 텍스트 파서 기반) ---
def parse_adobe_content_blocks(selected_blocks_or_container: BeautifulSoup | list) -> str:
    output_lines = []
    if not selected_blocks_or_container:
        print("    경고: 파싱할 콘텐츠 컨테이너 또는 블록 리스트가 없습니다.")
        return ""

    blocks_to_iterate = []
    if isinstance(selected_blocks_or_container, list):
        blocks_to_iterate = selected_blocks_or_container
    elif hasattr(selected_blocks_or_container, 'name'): 
        # find_all의 recursive 기본값은 True입니다. Adobe 페이지는 중첩 div가 많으므로,
        # 주요 콘텐츠 블록(div.text, div.procedure 등)을 찾을 때는 recursive=False로 하여
        # 컨테이너의 직계 자식 div들만 우선 고려하는 것이 좋을 수 있습니다.
        # 사용자 제공 코드에서는 block.find_all(True, recursive=False) 였는데,
        # 이는 block의 직계 자식 중 모든 타입의 태그를 의미합니다.
        # 여기서는 Adobe 페이지 구조에 맞춰 div.text, div.procedure 등을 찾습니다.
        candidate_blocks = selected_blocks_or_container.find_all(
            lambda tag: tag.name == 'div' and \
                        any(cls in tag.get('class', []) for cls in ['text', 'procedure', 'imagepar', 'internalBanner', 'reference', 'titleBar']),
            recursive=False # 컨테이너의 직계 자식들 중에서만 찾도록 수정
        )
        if not candidate_blocks: # 직계 자식 div 블록이 없으면, 컨테이너 내부를 좀 더 넓게 탐색
             candidate_blocks = selected_blocks_or_container.find_all(
                lambda tag: tag.name == 'div' and \
                            any(cls in tag.get('class', []) for cls in ['text', 'procedure'])
            )
        # 그래도 없으면, 컨테이너 자체를 하나의 블록으로 간주하여 그 안의 내용을 직접 파싱
        blocks_to_iterate = candidate_blocks if candidate_blocks else [selected_blocks_or_container]
    else:
        print(f"    오류: parse_adobe_content_blocks에 잘못된 타입의 인자가 전달되었습니다: {type(selected_blocks_or_container)}")
        return ""
    
    if not blocks_to_iterate:
         print("    경고: 최종 파싱할 콘텐츠 블록이 없습니다 (내부 로직).")
         return ""

    globally_processed_elements_ids = set() # 이미 처리한 요소의 id 저장

    for block_element in blocks_to_iterate: 
        if not hasattr(block_element, 'find_all') or id(block_element) in globally_processed_elements_ids: 
            continue
        
        # 각 블록 내의 모든 관련 태그들을 순서대로 처리 (사용자 제공 코드의 방식과 유사하게)
        # H2, H3, P, UL, OL, 그리고 노트/주의사항 div를 찾습니다. 이미지는 여기서 처리하지 않습니다.
        for element in block_element.find_all(['h2', 'h3', 'p', 'ul', 'ol', 'div'], recursive=True):
            if id(element) in globally_processed_elements_ids: continue # 이미 처리된 요소면 건너뜀
            if not element.name: continue # NavigableString 등은 여기서 처리 안 함

            # 중첩된 리스트나 노트 내부 요소가 상위에서 이미 전체 처리되었다면 건너뜀
            is_already_handled_by_parent = False
            for parent in element.parents:
                if id(parent) in globally_processed_elements_ids and parent != element:
                    is_already_handled_by_parent = True
                    break
            if is_already_handled_by_parent:
                continue

            if element.name == 'h2':
                # section-title 클래스가 있거나, div.cmp-text 바로 아래 h2인 경우 등을 고려
                text = element.get_text(strip=True)
                if text:
                    if output_lines and output_lines[-1].strip(): output_lines.append("")
                    output_lines.append(f"## {text}\n")
                globally_processed_elements_ids.add(id(element))

            elif element.name == 'h3':
                text = element.get_text(strip=True)
                if text:
                    if output_lines and output_lines[-1].strip(): output_lines.append("")
                    output_lines.append(f"### {text}\n")
                globally_processed_elements_ids.add(id(element))
            
            elif element.name == 'div' and 'variable' in element.get('class', []):
                 var_title_span = element.find('span', class_='help-variable-title')
                 if var_title_span and not var_title_span.find_parent('li', class_='step'):
                     text = var_title_span.get_text(strip=True)
                     if text:
                         if output_lines and output_lines[-1].strip(): output_lines.append("")
                         output_lines.append(f"### {text}") 
                 globally_processed_elements_ids.add(id(element)) # div.variable 전체를 처리한 것으로 간주
            
            elif element.name == 'p':
                # p 태그 내 이미지 처리는 현재 하지 않음 (이미지는 하단 목록화)
                text = element.get_text(strip=True)
                if text:
                    # 이전 줄이 제목/리스트/인용구가 아니면 공백 후 이어붙이거나, 새 문단으로 추가
                    if output_lines and output_lines[-1].strip() and \
                       not output_lines[-1].strip().startswith(("#", ">", "*", "-")) and \
                       not re.match(r"^\d+\.\s", output_lines[-1].strip()):
                         output_lines.append("") 
                    output_lines.append(text)
                globally_processed_elements_ids.add(id(element))

            elif element.name in ['ul', 'ol'] and not element.find_parent('li'): # 최상위 리스트만 직접 처리
                list_items_md = []
                for i, li in enumerate(element.find_all('li', recursive=False)): 
                    item_text = li.get_text(strip=True) # li 내부의 모든 텍스트 (이미지 alt 포함 가능성)
                    if item_text:
                        prefix = '* ' if element.name == 'ul' else f"{i + 1}. "
                        # li 내용이 여러 줄일 경우, 다음 줄부터는 들여쓰기
                        lines = item_text.splitlines()
                        if lines:
                            list_items_md.append(f"{prefix}{lines[0]}")
                            for line_idx in range(1, len(lines)):
                                list_items_md.append(f"  {lines[line_idx]}")
                if list_items_md:
                    if output_lines and output_lines[-1].strip() != "": output_lines.append("")
                    output_lines.extend(list_items_md)
                    output_lines.append("") # 리스트 뒤에 공백
                globally_processed_elements_ids.add(id(element)) # 이 리스트 전체는 처리됨
            
            elif element.name == 'div' and ('helpx-note' in element.get('class', []) or 'helpx-caution' in element.get('class', [])):
                note_title_span = element.find('span', class_='note-title')
                title_text = note_title_span.get_text(strip=True) if note_title_span else ("참고:" if "helpx-note" in element.get('class',[]) else "주의:")                
                note_body_text_parts = []
                for p_tag_in_note in element.find_all('p'): 
                    p_text = p_tag_in_note.get_text(strip=True)
                    if p_text: note_body_text_parts.append(p_text)
                note_body_text = "\n".join(filter(None, note_body_text_parts))
                if note_body_text:
                    if output_lines and output_lines[-1].strip() != "": output_lines.append("")
                    output_lines.append(f"> **{title_text}**")
                    for line in note_body_text.splitlines():
                        if line.strip(): output_lines.append(f"> {line.strip()}")
                    output_lines.append("")
                globally_processed_elements_ids.add(id(element))
        
        # 블록 처리 후, output_lines의 마지막이 빈 줄이 아니면 빈 줄 추가 (블록 간 간격)
        if output_lines and output_lines[-1].strip() != "":
            output_lines.append("")
            
    # 최종 결과에서 연속된 빈 줄을 하나로 압축하고, 시작/끝의 불필요한 빈 줄 제거
    final_output_cleaned = []
    if output_lines:
        was_empty_line = False 
        for line_content in output_lines:
            current_line_empty = (line_content.strip() == "")
            if current_line_empty and was_empty_line: continue
            final_output_cleaned.append(line_content)
            was_empty_line = current_line_empty
            
    return "\n".join(final_output_cleaned).strip()


# --- save_to_markdown 함수 ---
def save_to_markdown(title: str, content: str, md_dir: str):
    safe_title = sanitize_text_for_filename(title)
    if not safe_title: 
        safe_title = f"무제_문서_{int(time.time())}"
    filename = f"{safe_title}.md"
    filepath = os.path.join(md_dir, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"성공: '{filepath}' (마크다운) 파일이 저장되었습니다.")
    except Exception as e:
        print(f"오류: '{filepath}' (마크다운) 파일 저장에 실패했습니다 - {e}")

# --- 전역 변수 및 초기화 ---
IMAGE_DOWNLOAD_FAILED_PLACEHOLDER = "이미지_다운로드_실패"
md_output_dir = "md" 

# --- 프로그램 실행 부분 ---
if __name__ == "__main__":
    print("진단: 메인 실행 블록 시작됨")
    parser = argparse.ArgumentParser(description="Selenium을 사용하여 웹 페이지 URL을 마크다운 문서로 변환하고, 이미지를 다운로드합니다.")
    parser.add_argument('-u', '--urls', nargs='+', required=True, help="변환할 하나 이상의 URL 목록 (공백으로 구분)")
    args = parser.parse_args() 
    print(f"진단: 커맨드라인 인자 파싱 완료: {args.urls}")

    EXPORT_DISK_CD_URL_IDENTIFIER = "export-files-disk-or-cd.html" 
    SPECIFIC_CONTENT_START_PHRASE = "사진을 하드 디스크, CD 또는 DVD로 내보내려면, 다음 절차를 따르십시오."
    SPECIFIC_CONTENT_END_PHRASE = "Export Actions 만들기를 참조하십시오."
    
    os.makedirs(md_output_dir, exist_ok=True)
    
    print("진단: Selenium 서비스 객체 생성 시도...")
    try:
        selenium_service = Service() 
        print("진단: Selenium 서비스 객체 생성 완료.")
    except Exception as e_service:
        print(f"치명적 오류: Selenium Service 시작 중 오류: {e_service}")
        print("ChromeDriver가 PATH에 설정되어 있는지 또는 selenium Service 객체 생성 시 올바른 경로를 사용하는지 확인하세요.")
        exit()

    try:
        for url_to_process in args.urls:
            print("-" * 50)
            print(f"처리 중인 URL: {url_to_process}")
            
            parsed_uri = urlparse(url_to_process)
            base_page_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"

            html_content, image_candidates, page_title_from_fetch = fetch_html_and_image_data(url_to_process, selenium_service, base_page_url)
            
            if not html_content:
                print(f"[{url_to_process}] HTML 내용을 가져오지 못했습니다. 다음 URL로 넘어갑니다.")
                continue

            soup = BeautifulSoup(html_content, 'lxml')
            for unwanted_tag in soup.find_all(['style', 'script']):
                unwanted_tag.decompose()

            page_overall_title_tag = soup.find('title') 
            page_overall_title = page_overall_title_tag.get_text(strip=True) if page_overall_title_tag else page_title_from_fetch or f"제목_없음_{int(time.time())}"
            
            if any(err_keyword in page_overall_title.lower() for err_keyword in ["404", "page not found", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다."]):
                 print(f"경고: [{url_to_process}] 제목 기반으로 404 또는 오류 페이지로 판단되어 마크다운 생성을 건너뜁니다.")
                 continue

            page_title_safe_for_folder = sanitize_text_for_filename(page_overall_title)
            if not page_title_safe_for_folder: page_title_safe_for_folder = f"무제_{int(time.time())}"

            # 원본 HTML 저장 기능 (주석 처리됨)
            # if soup: 
            #     # save_raw_html 함수가 정의되어 있어야 함
            #     # save_raw_html(page_overall_title, soup.prettify()) 
            #     pass


            page_images_folder_name = f"{page_title_safe_for_folder}_images"
            page_images_abs_folder_path = os.path.join(md_output_dir, page_images_folder_name)

            image_references_map = download_and_save_images(image_candidates, page_overall_title, page_images_abs_folder_path, page_images_folder_name)

            main_content_column = soup.select_one('div.dexter-FlexContainer-Items > div.position')
            actual_article_blocks_container = None
            if main_content_column:
                temp_container = main_content_column.find('div', class_=lambda x: x and x.startswith('aem-Grid aem-Grid--12'), recursive=False)
                if temp_container: actual_article_blocks_container = temp_container
                else: actual_article_blocks_container = main_content_column
            if not actual_article_blocks_container: 
                 actual_article_blocks_container = soup.find('main')

            if actual_article_blocks_container:
                h1_tag = actual_article_blocks_container.find('h1', class_='page-title') 
                if not h1_tag : h1_tag = soup.find('h1', class_='page-title')
                doc_main_title = h1_tag.get_text(strip=True) if h1_tag else page_overall_title
                
                blocks_input_for_parser = actual_article_blocks_container 
                
                if EXPORT_DISK_CD_URL_IDENTIFIER in url_to_process:
                    print(f"'{url_to_process}'에 대해 특정 내용 추출을 위한 블록 필터링 시도합니다.")
                    candidate_blocks_specific = actual_article_blocks_container.find_all(
                        lambda tag: tag.name == 'div' and \
                                    any(cls in tag.get('class', []) for cls in ['text', 'procedure', 'imagepar', 'reference']), 
                        recursive=False 
                    )
                    if not candidate_blocks_specific: 
                         candidate_blocks_specific = actual_article_blocks_container.find_all(
                            lambda tag: tag.name == 'div' and \
                                        any(cls in tag.get('class', []) for cls in ['text', 'procedure'])
                        )
                    if not candidate_blocks_specific and hasattr(actual_article_blocks_container, 'name'): 
                        candidate_blocks_specific = [actual_article_blocks_container]
                    
                    temp_specific_blocks_list = [] 
                    collecting = False
                    if candidate_blocks_specific: 
                        for block_item in candidate_blocks_specific:
                            block_text_for_phrase_check = block_item.get_text(strip=True)
                            if not collecting and SPECIFIC_CONTENT_START_PHRASE in block_text_for_phrase_check:
                                collecting = True
                            if collecting:
                                temp_specific_blocks_list.append(block_item)
                            if collecting and SPECIFIC_CONTENT_END_PHRASE in block_text_for_phrase_check:
                                break 
                    
                    if temp_specific_blocks_list: 
                        blocks_input_for_parser = temp_specific_blocks_list 
                        print(f"  특정 내용 블록 {len(blocks_input_for_parser)}개 선택됨.")
                    else:
                        print(f"  경고: '{url_to_process}'에서 특정 내용 시작/끝 부분을 포함하는 블록을 찾지 못했습니다. 전체 주요 콘텐츠를 파싱합니다.")
                        blocks_input_for_parser = actual_article_blocks_container # 전체 컨테이너로 대체
                else: 
                    print(f"'{url_to_process}'에 대해 전체 주요 콘텐츠 영역 파싱을 시도합니다.")
                    blocks_input_for_parser = actual_article_blocks_container
                
                # parse_adobe_content_blocks는 이제 이미지 정보를 직접 사용하지 않음
                structured_text_body = parse_adobe_content_blocks(blocks_input_for_parser)
                
                image_markdown_list = []
                if image_references_map:
                    image_markdown_list.append("\n\n---\n## 문서 내 참조된 이미지 목록\n")
                    for original_src, img_data in image_references_map.items():
                        alt = img_data['alt'] if img_data['alt'] else f"{page_overall_title} 관련 이미지"
                        image_markdown_list.append(f"### 이미지: {alt}")
                        if img_data['download_failed']:
                            image_markdown_list.append(f"![{alt}]({IMAGE_DOWNLOAD_FAILED_PLACEHOLDER})")
                        else:
                            image_markdown_list.append(f"![{alt}]({img_data['md_relative_path']})")
                        image_markdown_list.append(f"[원본 이미지 보기]({img_data['original_url']})\n---")
                
                final_md_content = f"# {doc_main_title}\n\n{structured_text_body}\n" + "\n".join(image_markdown_list)
                save_to_markdown(doc_main_title, final_md_content.strip(), md_output_dir)
            else:
                print(f"[{url_to_process}]에서 주요 콘텐츠 영역을 찾지 못했습니다.")
    
    finally:
        if 'selenium_service' in locals() and hasattr(selenium_service, 'is_connectable') and selenium_service.is_connectable():
            print("진단: Selenium 서비스 종료 중...")
            selenium_service.stop()
            print("진단: Selenium 서비스 종료 완료.")