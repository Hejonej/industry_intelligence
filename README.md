# Industry Intelligence App

산업 정보 수집 및 분석을 위한 Streamlit 기반 웹 애플리케이션입니다.

## 주요 기능

- **뉴스 클리핑**: RSS 피드를 통한 실시간 뉴스 수집
- **문서 분석**: PDF/DOCX 파일 업로드 및 내용 분석
- **Big4 발간물 검색**: Deloitte, EY, KPMG 등 Big4 기업의 최신 보고서 검색
- **외부 발간물 검색**: McKinsey, BCG, OECD 등 주요 기관의 발간물 검색
- **이벤트 검색**: 업계 관련 이벤트 정보 수집
- **PDF 리포트 생성**: 수집된 정보를 종합한 PDF 리포트 생성

## 설치 및 실행

### 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud 배포
1. GitHub에 코드 업로드
2. https://share.streamlit.io/ 에서 배포

## 사용법

1. **회사 추가**: 분석하고 싶은 회사명을 추가
2. **날짜 범위 설정**: 보고서 및 이벤트 검색 기간 설정
3. **뉴스 소스 선택**: RSS 피드 URL 설정
4. **분석 실행**: 수집된 정보 분석 및 요약
5. **PDF 리포트 생성**: 종합 리포트 다운로드

## 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **API**: OpenAI GPT-3.5, Google Custom Search
- **데이터 처리**: Pandas, BeautifulSoup, Feedparser
- **문서 처리**: PyPDF2, python-docx
