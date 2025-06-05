# Adobe HelpX 페이지 HTML to Markdown 변환기

이 프로그램은 Adobe HelpX 웹 페이지의 URL을 입력받아, 해당 페이지의 주요 콘텐츠(텍스트 및 이미지)를 추출하여 로컬에 마크다운(.md) 파일과 이미지 파일로 저장하는 파이썬 스크립트입니다.

## 주요 기능

* 지정된 URL의 웹 페이지 HTML 내용을 가져옵니다. (Selenium 사용)
* HTML에서 주요 본문 영역을 식별합니다.
* 본문 내의 텍스트(제목, 문단, 목록 등)를 마크다운 형식으로 변환합니다.
* 본문 내의 이미지 (너비 200px 이상)를 다운로드하여 로컬에 저장하고, 마크다운 문서에 해당 이미지를 참조합니다.
* 이미지 원본 URL 링크를 마크다운에 함께 포함합니다.
* 최종 마크다운 파일은 `md/` 폴더에, 관련 이미지는 `md/페이지제목_images/` 폴더에 저장됩니다.

## 사용 환경

* Python 3.8 이상
* 필수 라이브러리 (자세한 내용은 `requirements.txt` 파일 참조):
    * selenium
    * beautifulsoup4
    * requests
    * lxml
* Google Chrome 브라우저 및 해당 버전에 맞는 ChromeDriver (최신 Selenium 버전은 ChromeDriver 자동 관리를 지원할 수 있습니다.)

## 설치 및 실행 방법

1.  **프로젝트 복제 (GitHub에서):**
    ```bash
    git clone [GitHub 저장소 URL]
    cd [프로젝트 폴더명]
    ```

2.  **가상 환경 생성 및 활성화:**
    ```bash
    python -m venv .venv
    # Windows
    # .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **필요 라이브러리 설치:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **스크립트 실행:**
    ```bash
    python main.py -u <URL1> [URL2 URL3 ...]
    ```
    * `<URL1>`: 필수적으로 변환할 웹 페이지의 전체 URL을 입력합니다.
    * `[URL2 URL3 ...]` (선택 사항): 공백으로 구분하여 여러 URL을 한 번에 처리할 수 있습니다.

    **예시:**
    ```bash
    python main.py -u "[https://helpx.adobe.com/kr/lightroom-classic/help/workspace-basics.html](https://helpx.adobe.com/kr/lightroom-classic/help/workspace-basics.html)" "[https://helpx.adobe.com/kr/lightroom-classic/help/using-watermark-editor.html](https://helpx.adobe.com/kr/lightroom-classic/help/using-watermark-editor.html)"
    ```

## 출력 결과

* 마크다운 파일: `md/페이지제목.md` 형식으로 저장됩니다.
* 이미지 파일: `md/페이지제목_images/페이지제목_alt텍스트_순번.확장자` 형식으로 저장됩니다.

## 알려진 이슈 / 제한 사항

* 현재 Adobe HelpX 한국어 페이지(`helpx.adobe.com/kr/lightroom-classic/help/`)에 최적화되어 있습니다. 다른 구조의 웹사이트에서는 정상 작동하지 않을 수 있습니다.
* 404 오류 페이지나 예상치 못한 구조의 페이지에 대해서는 콘텐츠 추출이 제한될 수 있습니다.
* 이미지 필터링은 현재 너비(200px 이상) 기준으로만 이루어지므로, 본문과 관련 없는 큰 이미지가 포함될 수 있습니다.

## 향후 개선 사항 (선택 사항)

* 더 다양한 웹사이트 구조 지원
* 이미지 필터링 규칙 정교화
* 특정 섹션만 추출하는 기능 옵션화

---
이 프로젝트는 [사용자 이름 또는 프로젝트 소유자]에 의해 개발되었습니다.
