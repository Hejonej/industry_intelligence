from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일의 환경변수를 자동으로 불러옵니다.

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import requests
from bs4 import BeautifulSoup
import feedparser
import urllib.parse
import re
from PyPDF2 import PdfReader
import docx
import io
import openai
from dateutil import parser
client = openai.OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="Industry Intelligence", layout="wide")

# 세션 상태 초기화
if 'pwc_data' not in st.session_state:
    st.session_state.pwc_data = []
if 'big4_data' not in st.session_state:
    st.session_state.big4_data = []
if 'external_data' not in st.session_state:
    st.session_state.external_data = []
if 'event_data' not in st.session_state:
    st.session_state.event_data = []

# 프롬프트 설정 초기화(사용자 요청 상세 가이드 및 예시 포함)
if 'pwc_prompt' not in st.session_state:
    st.session_state.pwc_prompt = """아래 영문 발간물 본문을 반드시 한국어로 1~2문장, 200자 이내, 음슴체("~함", "~임") 스타일로 요약해줘.\n- 이 글을 읽는 해당 산업의 전문가가 이 글을 읽으면 어떤 내용을 알 수 있을지, 어떻게 활용할 수 있을지에 대한 관점으로 요약해줘\n- 핵심 변화/이슈(예: BEV 확산, 제조사 직판 확대 등), 주체(누가), 구체적 전략/툴/프레임워크(무엇을, 어떻게), 시사점만 간결하게 포함.\n- 원문에서 지역/국가/산업 등 구체적 맥락이 중요하게 다뤄지면 자연스럽게 포함하고, 그렇지 않으면 불필요하게 넣지 마라.
- 중복, 불필요한 정보, 원문 여러 문장 나열, 배경설명, 추측, 명령형/권고형 문장(예: ~하라, ~에 대비하라)은 하지 말 것.
- 반드시 핵심만 압축해서 1~2문장, 200자 이내로 작성.
- 아래 영문 발간물 본문을 반드시 한국어로 1~2문장, 200자 이내, 음슴체(~함, ~임) 스타일로 요약해줘.
- 아래 예시 참고:
예시) GCC 자동차 유통 산업의 구조 변화와 BEV 확산에 대응하기 위한 완성차 유통사의 전략적 전환 방향(다운스트림·인접 사업·현지화)을 제시함
예시) 공급망 압박 상황에서 공급망 전략 수립에 필요한 4가지 프레임워크를 제시함
예시) 제조업 현장 안전성 향상과 생산성 증대를 위한 IoT 웨어러블 도입 사례를 정리함
예시) 미국 제조업의 최근 동향 분석을 통해 AI/로봇, 新관세 정책, 리쇼어링 등 '4Rs' 전략 등 생산 효율성 및 운영 회복력 개선을 위한 산업 부활 전략을 설명함

---
{text[:1000]}
---
"""
if 'big4_prompt' not in st.session_state:
    st.session_state.big4_prompt = """다음 산업에 대한 Big4 회사(Deloitte안진, EY한영, KPMG삼정)의 최신 발간물을 검색하여 다음 정보를 제공하세요 절대 가짜 링크를 넣지 마세요.:

1. 발간일: YY.MM 형식
2. 제목: 원문 제목
3. 요약: 한국어로 번역된 핵심 내용 요약 (1-2문장)
4. 링크: 실제 발간물 페이지 링크

검색할 산업:"""
if 'external_prompt' not in st.session_state:
    st.session_state.external_prompt = """다음 산업에 대한 외부 기관(McKinsey, BCG, OECD, World Bank, IEA, 한국국가기관 등)의 최신 발간물을 검색하여 다음 정보를 제공하세요:

1. 발간일: YY.MM 형식
2. 제목: 원문 제목
3. 기관명: 발간 기관명
4. 요약: 한국어로 번역된 핵심 내용 요약 (1-2문장)
5. 링크: 실제 발간물 페이지 링크

검색할 산업:"""
if 'event_prompt' not in st.session_state:
    st.session_state.event_prompt = """다음 산업에 대한 주요 행사/컨퍼런스 정보를 검색하여 다음 정보를 제공하세요:

1. 행사명: 원문 행사명
2. 주최: 주최 기관명
3. 일정 및 장소: 날짜와 장소 (예: 6/15-6/17, 2025, Singapore)
4. 행사 내용: 한국어로 번역된 행사 주요 내용 (1-2문장)
5. 링크: 행사 등록/정보 페이지 링크

검색할 산업:"""

# --- 사이드바 ---
st.sidebar.title("⚙️ 설정")

# 산업 선택
industry_options = [
    "Automotive & Battery",
    "Consumer & Retail & Logistics",
    "Industrial Manufacturing",
    "Technology & Media",
    "Financial Services",
    "Healthcare & Life Sciences",
    "Energy & Resources",
    "Real Estate & Construction"
]

industry = st.sidebar.selectbox(
    "🏭 산업 선택",
    industry_options,
    index=0
)

# 기간 설정
col1, col2 = st.sidebar.columns(2)
with col1:
    report_start = st.date_input("📅 발간물 시작일", value=(datetime.today() - timedelta(days=30)))
with col2:
    report_end = st.date_input("📅 발간물 종료일", value=datetime.today())

col3, col4 = st.sidebar.columns(2)
with col3:
    event_start = st.date_input("📅 행사 시작일", value=datetime.today())
with col4:
    event_end = st.date_input("📅 행사 종료일", value=(datetime.today() + timedelta(days=60)))

# PwC 발간물 업로드
st.sidebar.subheader("PwC 발간물 업로드")
uploaded_file = st.sidebar.file_uploader("워드/ PDF 파일 업로드", type=["pdf", "docx"])

# 프롬프트 설정
st.sidebar.subheader("🔧 프롬프트 설정")

# PwC 분석 프롬프트
st.sidebar.markdown("**📄 PwC 발간물 분석 프롬프트**")
pwc_prompt = st.sidebar.text_area(
    "PwC 발간물 분석 프롬프트",
    value=st.session_state.pwc_prompt,
    height=100,
    help="PDF/Word 파일 분석 시 사용할 프롬프트를 설정하세요"
)
st.session_state.pwc_prompt = pwc_prompt

# Big4 검색 프롬프트
st.sidebar.markdown("**🔍 Big4 발간물 검색 프롬프트**")
big4_prompt = st.sidebar.text_area(
    "Big4 발간물 검색 프롬프트",
    value=st.session_state.big4_prompt,
    height=100,
    help="Big4 발간물 검색 시 사용할 프롬프트를 설정하세요"
)
st.session_state.big4_prompt = big4_prompt

# 외부 발간물 검색 프롬프트
st.sidebar.markdown("**🔍 외부 발간물 검색 프롬프트**")
external_prompt = st.sidebar.text_area(
    "외부 발간물 검색 프롬프트",
    value=st.session_state.external_prompt,
    height=100,
    help="외부 발간물 검색 시 사용할 프롬프트를 설정하세요"
)
st.session_state.external_prompt = external_prompt

# 행사 검색 프롬프트
st.sidebar.markdown("**🔍 행사 검색 프롬프트**")
event_prompt = st.sidebar.text_area(
    "행사 검색 프롬프트",
    value=st.session_state.event_prompt,
    height=100,
    help="행사 검색 시 사용할 프롬프트를 설정하세요"
)
st.session_state.event_prompt = event_prompt

# 프롬프트 초기화 버튼
if st.sidebar.button("🔄 프롬프트 초기화"):
    st.session_state.pwc_prompt = """아래 영문 발간물 본문을 반드시 한국어로 1~2문장, 200자 이내, 음슴체("~함", "~임") 스타일로 요약해줘.
다음 조건을 반드시 지킬 것:
1. **원문에 명시적으로 존재하지 않는 내용은 절대 포함하지 말 것**
   - 프레임워크, 전략 축, 시사점 등은 반드시 원문에 명시된 표현만 사용할 것
   - 일반적인 PwC 보고서 구조나 업계 관행을 근거로 추론하거나 보완하지 말 것
2. **요약은 원문에 있는 문장 또는 문단의 의미를 압축하는 수준으로만 작성할 것**
   - 구조적 재구성은 허용하되, 의미 추가나 해석은 금지
3. **지역·산업·세대 등 맥락은 원문에서 중요하게 다뤄질 경우에만 포함할 것**
   - 예: GCC 지역이 중심이라면 포함, 단순 언급 수준이면 생략
4. **산업 전문가가 고객과 커뮤니케이션할 때 활용할 수 있도록 전략적 시사점 중심으로 요약할 것**
   - 단, 시사점 역시 원문에 기반한 표현만 사용할 것
5. **배경 설명, 중복 정보, 명령형 문장, 추측성 표현은 절대 사용하지 말 것**
요약 방식 자동 판단 기준:
1. 설문조사 (Survey/Report)
- 조사 시점, 대상, 주요 트렌드 변화, 기업 전략적 시사점 중심
- 음슴체, 200자 이내
- 예시:
  PwC가 2025년 6월에 전 세계 소비자를 대상으로 진행한 설문조사로, 건강·편의·지속가능성을 중시하는 경향이 강화되며 식품 기업은 기술 융합 및 데이터 기반 전략이 필요함을 시사함.
2. 사례 (Case Study)
- PwC 어느 지역 법인이 수행했는지, 어떤 기능을 어떻게 개선했는지, 산업별 인사이트 중심
- 음슴체, 200자 이내
- 예시:
  PwC 미국 법인이 단일 플랫폼 도입과 업무 자동화를 통해 American Airlines의 재무 시스템을 디지털화한 사례로, 항공업계의 자금 관리 효율성과 리스크 대응 역량 강화함.
3. 보고서/기고문/인사이트/분석 (Thought Leadership, Insight)
- 주제별 핵심 주장, 제시된 프레임워크나 전략, 산업별 적용 가능성 중심
- 음슴체, 200자 이내
- 불필요한 주체(PwC가~ 등) 언급 생략 가능
- 예시:
  AI 기반 수요 예측과 재고 최적화를 통해 유통업계의 공급망 민첩성과 비용 효율성 제고 전략을 설명함.
  미국 제조업의 최근 동향 분석을 통해 AI/로봇, 新관세 정책, 리쇼어링 등 '4Rs' 전략 등 생산 효율성 및 운영 회복력 개선을 위한 산업 부활 전략을 설명함.
  GCC 자동차 유통 산업의 구조 변화와 BEV 확산에 대응하기 위한 완성차 유통사의 전략적 전환 방향(다운스트림·인접 사업·현지화)을 제시함.
  공급망 압박 상황에서 공급망 전략 수립에 필요한 4가지 프레임워크를 제시함.
  동아시아 지역이 글로벌 럭셔리 시장의 핵심 성장지로 부상하며, 럭셔리 브랜드는 소비자 유입 확대·도시별 소비 격차·해외 소비 비중 등을 고려한 현지화 전략이 필요함을 설명함
  글로벌 리테일 기업들이 외부 지향적 사고, 실시간 데이터 활용, 민첩한 조직 운영을 통해 소비자 기대 변화에 대응하고 경쟁 우위를 확보하는 전략을 설명함

본문:
{text[:1000]}
"""
    st.session_state.big4_prompt = """다음 산업에 대한 Big4 회사(Deloitte안진, EY한영, KPMG삼정)의 최신 발간물을 검색하여 다음 정보를 제공하세요:

1. 발간일: YY.MM 형식
2. 제목: 원문 제목
3. 요약: 한국어로 번역된 핵심 내용 요약 (1-2문장)
4. 링크: 실제 발간물 페이지 링크

검색할 산업:"""
    st.session_state.external_prompt = """다음 산업에 대한 외부 기관(McKinsey, BCG, OECD, World Bank, IEA, 한국국가기관 등)의 최신 발간물을 검색하여 다음 정보를 제공하세요:

1. 발간일: YY.MM 형식
2. 제목: 원문 제목
3. 기관명: 발간 기관명
4. 요약: 한국어로 번역된 핵심 내용 요약 (1-2문장)
5. 링크: 실제 발간물 페이지 링크

검색할 산업:"""
    st.session_state.event_prompt = """다음 산업에 대한 주요 행사/컨퍼런스 정보를 검색하여 다음 정보를 제공하세요:

1. 행사명: 원문 행사명
2. 주최: 주최 기관명
3. 일정 및 장소: 날짜와 장소 (예: 6/15-6/17, 2025, Singapore)
4. 행사 내용: 한국어로 번역된 행사 주요 내용 (1-2문장)
5. 링크: 행사 등록/정보 페이지 링크

검색할 산업:"""
    st.rerun()

def extract_text_from_pdf(pdf_file):
    """PDF에서 텍스트 추출"""
    try:
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"PDF 읽기 오류: {str(e)}")
        return ""

def extract_text_from_docx(docx_file):
    """DOCX에서 텍스트 추출"""
    try:
        doc = docx.Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"DOCX 읽기 오류: {str(e)}")
        return ""

def analyze_document_content(text, filename=""):
    """문서 내용 분석하여 한글 요약 및 발간처 추출"""
    if not text:
        return {"title": "", "summary": "", "author": "", "translated_title": ""}

    # 파일명에서 정보 추출
    filename_parts = filename.replace('.pdf', '').replace('.docx', '').split('_')
    title = filename_parts[0] if filename_parts else "제목 없음"

    # 발간처 추출 (파일명, 본문에서 PwC, Deloitte 등 탐색)
    author = "알 수 없음"
    for org in ["PwC", "Deloitte", "EY", "KPMG"]:
        if org.lower() in filename.lower() or org.lower() in text.lower():
            author = org
            break
    # PwC 세부 구분
    if author == "PwC":
        if "US" in text or "United States" in text:
            author = "PwC US"
        elif "Korea" in text or "한국" in text:
            author = "PwC Korea"
        else:
            author = "PwC Global"

    # OpenAI API로 한글 번역 및 요약
    
    prompt = f"""
아래 영문 발간물 본문을 반드시 한국어로 1~2문장, 200자 이내, 음슴체("~함", "~임") 스타일로 요약해줘.
다음 조건을 반드시 지킬 것:
1. **원문에 명시적으로 존재하지 않는 내용은 절대 포함하지 말 것**
   - 프레임워크, 전략 축, 시사점 등은 반드시 원문에 명시된 표현만 사용할 것
   - 일반적인 PwC 보고서 구조나 업계 관행을 근거로 추론하거나 보완하지 말 것
2. **요약은 원문에 있는 문장 또는 문단의 의미를 압축하는 수준으로만 작성할 것**
   - 구조적 재구성은 허용하되, 의미 추가나 해석은 금지
3. **지역·산업·세대 등 맥락은 원문에서 중요하게 다뤄질 경우에만 포함할 것**
   - 예: GCC 지역이 중심이라면 포함, 단순 언급 수준이면 생략
4. **산업 전문가가 고객과 커뮤니케이션할 때 활용할 수 있도록 전략적 시사점 중심으로 요약할 것**
   - 단, 시사점 역시 원문에 기반한 표현만 사용할 것
5. **배경 설명, 중복 정보, 명령형 문장, 추측성 표현은 절대 사용하지 말 것**
요약 방식 자동 판단 기준:
1. 설문조사 (Survey/Report)
- 조사 시점, 대상, 주요 트렌드 변화, 기업 전략적 시사점 중심
- 음슴체, 200자 이내
- 예시:
  PwC가 2025년 6월에 전 세계 소비자를 대상으로 진행한 설문조사로, 건강·편의·지속가능성을 중시하는 경향이 강화되며 식품 기업은 기술 융합 및 데이터 기반 전략이 필요함을 시사함.
2. 사례 (Case Study)
- PwC 어느 지역 법인이 수행했는지, 어떤 기능을 어떻게 개선했는지, 산업별 인사이트 중심
- 음슴체, 200자 이내
- 예시:
  PwC 미국 법인이 단일 플랫폼 도입과 업무 자동화를 통해 American Airlines의 재무 시스템을 디지털화한 사례로, 항공업계의 자금 관리 효율성과 리스크 대응 역량 강화함.
3. 보고서/기고문/인사이트/분석 (Thought Leadership, Insight)
- 주제별 핵심 주장, 제시된 프레임워크나 전략, 산업별 적용 가능성 중심
- 음슴체, 200자 이내
- 불필요한 주체(PwC가~ 등) 언급 생략 가능
- 예시:
  AI 기반 수요 예측과 재고 최적화를 통해 유통업계의 공급망 민첩성과 비용 효율성 제고 전략을 설명함.
  미국 제조업의 최근 동향 분석을 통해 AI/로봇, 新관세 정책, 리쇼어링 등 '4Rs' 전략 등 생산 효율성 및 운영 회복력 개선을 위한 산업 부활 전략을 설명함.
  GCC 자동차 유통 산업의 구조 변화와 BEV 확산에 대응하기 위한 완성차 유통사의 전략적 전환 방향(다운스트림·인접 사업·현지화)을 제시함.
  공급망 압박 상황에서 공급망 전략 수립에 필요한 4가지 프레임워크를 제시함.
  동아시아 지역이 글로벌 럭셔리 시장의 핵심 성장지로 부상하며, 럭셔리 브랜드는 소비자 유입 확대·도시별 소비 격차·해외 소비 비중 등을 고려한 현지화 전략이 필요함을 설명함
  글로벌 리테일 기업들이 외부 지향적 사고, 실시간 데이터 활용, 민첩한 조직 운영을 통해 소비자 기대 변화에 대응하고 경쟁 우위를 확보하는 전략을 설명함

본문:
{text[:1000]}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3
        )
        summary = response.choices[0].message.content.strip()
        print("OpenAI 응답:", summary)
    except Exception as e:
        summary = f"[OpenAI 요약 실패: {e}]\n" + (text[:300] + "..." if len(text) > 300 else text)

    # summary 줄바꿈 제거(표에 넣기 전)
    summary = summary.replace('\n', ' ')

    # 제목도 한글로 번역 (최신 방식)
    title_prompt = f"다음 영문 제목을 한국어로 자연스럽게 번역해줘: {title}"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=60,
            temperature=0.3
        )
        translated_title = response.choices[0].message.content.strip()
    except Exception as e:
        translated_title = title

    return {
        "title": title,
        "translated_title": translated_title,
        "summary": summary,
        "author": author
    }

GOOGLE_API_KEY = "AIzaSyB51FOsIGLbOAXVH30HSBNYYnJosY797oM"
CSE_ID = "a5ffa574ddd0247af"

def google_search(query, cse_id=CSE_ID, api_key=GOOGLE_API_KEY, num=3):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": cse_id,
        "key": api_key,
        "num": num
    }
    
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()  # HTTP 에러 체크
        data = resp.json()
        
        # API 에러 체크
        if "error" in data:
            st.error(f"Google API 에러: {data['error'].get('message', 'Unknown error')}")
            return []
        
        # 검색 결과 확인
        items = data.get("items", [])
        if not items:
            st.warning(f"검색 결과 없음: '{query}'")
            return []
        
        results = []
        for item in items:
            results.append({
                "title": item["title"],
                "summary": item.get("snippet", ""),
                "link": item["link"]
            })
        
        st.success(f"검색 성공: '{query}' - {len(results)}개 결과")
        return results
        
    except requests.exceptions.RequestException as e:
        st.error(f"네트워크 에러: {str(e)}")
        return []
    except ValueError as e:
        st.error(f"JSON 파싱 에러: {str(e)}")
        return []
    except Exception as e:
        st.error(f"예상치 못한 에러: {str(e)}")
        return []

def extract_ym_from_text(text):
    # 2024-06, 2024.06, 24.06, 2024/06 등 다양한 연월 패턴 추출
    patterns = [
        r'(20\d{2})[.\-/년 ](0[1-9]|1[0-2])',  # 2024.06, 2024-06, 2024/06, 2024년 06
        r'(\d{2})[.\-/년 ](0[1-9]|1[0-2])'      # 24.06, 24-06, 24/06, 24년 06
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            year = m.group(1)
            month = m.group(2)
            if len(year) == 2:
                year = '20' + year
            return f"{year}.{month}"
    return None

def search_big4_publications(industry, report_start, report_end):
    big4_sites = ["deloitte.com", "ey.com", "kpmg.com"]
    big4_data = []
    st.info(f"Big4 검색 시작: {industry}")
    api_success = False
    for site in big4_sites:
        query = f"site:{site} {industry} (report OR insight OR publication OR whitepaper OR 리포트 OR 보고서 OR 발간물)"
        st.info(f"검색 중: {query}")
        results = google_search(query)
        if results:
            api_success = True
            for result in results:
                # 발간일 추출
                ym = extract_ym_from_text(result['title'] + ' ' + result['summary'])
                # 날짜 필터: 발간일이 있으면 필터, 없으면 최근 10개라도 표시
                show = False
                if ym:
                    try:
                        pub_date = parser.parse(ym + '-01').date()
                        if report_start <= pub_date <= report_end:
                            show = True
                    except:
                        pass
                else:
                    show = True  # 발간일 없으면 최근 결과라도 표시
                if not show:
                    continue
                # 제목에 하이퍼링크
                title_link = f"[{result['title']}]({result['link']})"
                # 한글 요약(OpenAI API)
                prompt = f"아래는 Big4(예: Deloitte, EY, KPMG)에서 발간한 산업 관련 보고서의 제목, 요약, 링크임.\n- 제목: {result['title']}\n- 요약: {result['summary']}\n- 링크: {result['link']}\n위 정보를 바탕으로, 전문가가 이 보고서를 통해 무엇을 알 수 있고, 어떻게 활용할 수 있을지 1~2문장, 200자 이내, 음슴체(~함, ~임)로 요약해줘. 명령형 금지, 없는 정보는 지어내지 마."
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=200,
                        temperature=0.3
                    )
                    summary = response.choices[0].message.content.strip().replace('\n', ' ')
                except Exception as e:
                    summary = f"[OpenAI 요약 실패: {e}] {result['summary']}"
                # (YY.MM 또는 -) [제목(링크)]\n: 요약
                ym_str = f"({ym[2:]})" if ym else "(-)"
                content = f"{ym_str} {title_link}\n: {summary}"
                big4_data.append({
                    "경쟁사": site.split(".")[0].capitalize(),
                    "활동 구분": "발간물",
                    "내용": content
                })
        else:
            st.warning(f"{site}에서 검색 결과 없음")
    if not api_success:
        st.warning("Google API 호출 실패로 샘플 데이터를 표시합니다.")
        sample_data = [
            {
                "경쟁사": "Deloitte",
                "활동 구분": "발간물",
                "내용": f"(25.05) [Intelligent manufacturing](https://www2.deloitte.com/global/en/industries/automotive.html)\n: AI가 제조업 경쟁력 강화에 필수로 자리잡으며, 데이터 품질·에너지 소비 등 남은 과제를 해결하기 위한 3단계 AI 도입 프레임워크를 제시함"
            },
            {
                "경쟁사": "Deloitte",
                "활동 구분": "발간물",
                "내용": f"(25.04) [Enhancing supply chain resilience in a new era of policy](https://www2.deloitte.com/global/en/industries/automotive.html)\n: 美 제조업체들이 관세·지정학 리스크에 대응해 리쇼어링과 공급망 재구성에 나서며, 고부가가치 중심의 회복력 전략으로 전환 중임을 설명함"
            }
        ]
        big4_data = sample_data
    st.info(f"Big4 검색 완료: 총 {len(big4_data)}개 결과")
    return big4_data

def search_external_publications(industry, report_start, report_end):
    external_sites = [
        "mckinsey.com", "bcg.com", "oecd.org", "worldbank.org", "iea.org"
    ]
    external_data = []
    
    st.info(f"외부 발간물 검색 시작: {industry}")
    
    # API 호출 시도
    api_success = False
    for site in external_sites:
        query = f"site:{site} {industry}"
        st.info(f"검색 중: {query}")
        
        results = google_search(query)
        if results:
            api_success = True
            for result in results:
                external_data.append({
                    "제목(내용)": f"{result['title']}\n: {result['summary']}",
                    "기관/업체명": site.split(".")[0].capitalize(),
                    "링크": result["link"]
                })
        else:
            st.warning(f"{site}에서 검색 결과 없음")
    
    # API 호출이 모두 실패한 경우 샘플 데이터 제공
    if not api_success:
        st.warning("Google API 호출 실패로 샘플 데이터를 표시합니다.")
        sample_data = [
            {
                "제목(내용)": f"API 호출 실패로 샘플 데이터를 표시합니다.",
                "기관/업체명": "McKinsey",
                "링크": "https://www.mckinsey.com/industries/automotive-and-assembly"
            },
            {
                "제목(내용)": f"API 호출 실패로 샘플 데이터를 표시합니다.",
                "기관/업체명": "BCG",
                "링크": "https://www.bcg.com/industries/automotive"
            },
            {
                "제목(내용)": f"API 호출 실패로 샘플 데이터를 표시합니다.",
                "기관/업체명": "OECD",
                "링크": "https://www.oecd.org/industry/automotive/"
            }
        ]
        external_data = sample_data
    
    st.info(f"외부 발간물 검색 완료: 총 {len(external_data)}개 결과")
    return external_data

def search_upcoming_events(industry, event_start, event_end):
    event_sites = [
        "eventbrite.com", "linkedin.com/events"
    ]
    event_data = []
    
    st.info(f"행사 검색 시작: {industry}")
    
    # API 호출 시도
    api_success = False
    for site in event_sites:
        query = f"site:{site} {industry} conference"
        st.info(f"검색 중: {query}")
        
        results = google_search(query)
        if results:
            api_success = True
            for result in results:
                event_data.append({
                    "행사명": result['title'],
                    "주최": site.split(".")[0].capitalize(),
                    "일정 및 장소": "-",  # 구글 검색 결과에는 날짜/장소 정보가 없으므로 필요시 추가 파싱
                    "행사 내용": result['summary'],
                    "링크": result["link"]
                })
        else:
            st.warning(f"{site}에서 검색 결과 없음")
    
    # API 호출이 모두 실패한 경우 샘플 데이터 제공
    if not api_success:
        st.warning("Google API 호출 실패로 샘플 데이터를 표시합니다.")
        sample_data = [
            {
                "행사명": f"Global {industry} Summit 2024",
                "주최": "Industry Events",
                "일정 및 장소": "2024.06.15-17, Singapore",
                "행사 내용": f"API 호출 실패로 샘플 데이터를 표시합니다.",
                "링크": "https://www.globalindustrysummit.com"
            },
            {
                "행사명": f"{industry} Innovation Conference",
                "주최": "Tech Events",
                "일정 및 장소": "2024.07.20-22, Munich",
                "행사 내용": f"API 호출 실패로 샘플 데이터를 표시합니다.",
                "링크": "https://www.innovationconference.com"
            },
            {
                "행사명": f"Future of {industry} Expo",
                "주최": "Industry Expo",
                "일정 및 장소": "2024.08.10-12, Tokyo",
                "행사 내용": f"API 호출 실패로 샘플 데이터를 표시합니다.",
                "링크": "https://www.futureexpo.com"
            }
        ]
        event_data = sample_data
    
    st.info(f"행사 검색 완료: 총 {len(event_data)}개 결과")
    return event_data

def create_linked_table(df, table_class="dataframe"):
    """링크가 포함된 HTML 테이블 생성"""
    html = df.to_html(index=False, escape=False, classes=table_class)
    
    # 테이블 스타일 추가
    styled_html = f"""
    <style>
        .{table_class} {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
            font-family: Arial, sans-serif;
        }}
        .{table_class} th {{
            background-color: #f2f2f2;
            border: 1px solid #ddd;
            padding: 12px 8px;
            text-align: left;
            font-weight: bold;
            color: #333;
        }}
        .{table_class} td {{
            border: 1px solid #ddd;
            padding: 12px 8px;
            text-align: left;
            vertical-align: top;
            line-height: 1.4;
        }}
        .{table_class} tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .{table_class} a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: bold;
        }}
        .{table_class} a:hover {{
            color: #003366;
            text-decoration: underline;
        }}
    </style>
    {html}
    """
    return styled_html

# --- 메인 화면 ---
st.markdown("""
<div style='background-color:#e95c0f; padding: 18px 20px; border-radius: 8px; margin-bottom: 20px;'>
    <span style='color:white; font-size:28px; font-weight:bold;'>Industry Intelligence</span><br>
    <span style='color:white; font-size:18px;'>""" + industry + """</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"**발간물 기간:** {report_start} ~ {report_end}")
st.markdown(f"**행사 기간:** {event_start} ~ {event_end}")
st.markdown("""
산업별 최신 글로벌 발간물, Big4 및 외부 주요 보고서, 행사 정보를 한눈에 제공합니다.  
<span style='color:#888;'>기준일: 2025년 7월</span>
""", unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)

# 1. Thought Leadership
st.header("1. Thought Leadership")

# 1-1. PwC 발간물 (작성자: 실제 PwC 발간 주체)
st.subheader("• PwC 발간물 (Global 및 한국 포함)")

if uploaded_file:
    st.info("업로드한 파일의 보고서/발간물 내용을 분석하여 표에 기입합니다.")
else:
    st.warning("PwC 발간물 파일을 업로드해 주세요.")

# PwC 데이터 표시
if st.session_state.pwc_data:
    df_pwc = pd.DataFrame(st.session_state.pwc_data)
    st.dataframe(df_pwc, use_container_width=True, hide_index=True)
else:
    # 빈 표 표시
    empty_pwc_data = [{"제목(내용)": "", "작성자": ""}]
    st.dataframe(pd.DataFrame(empty_pwc_data), use_container_width=True, hide_index=True)

st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)

# 1-2. Big4 타 법인 주요 활동 및 발간물 (작성자: 실제 Big4 법인명)
st.subheader("• Big4 타 법인 주요 활동 및 발간물")
st.info("Deloitte, EY, KPMG의 해당 산업 관련 최신 발간물을 리서치하여 표에 기입합니다.")

# Big4 데이터 표시
if st.session_state.big4_data:
    df_big4 = pd.DataFrame(st.session_state.big4_data)
    
    # 링크 컬럼이 없으면 추가
    if '링크' not in df_big4.columns:
        df_big4['링크'] = ''
    
    # 내용 컬럼의 줄바꿈을 HTML <br>로 변환
    df_big4['내용'] = df_big4['내용'].apply(lambda x: x.replace('\n', '<br>') if isinstance(x, str) else x)
    
    # 링크 컬럼을 클릭 가능한 링크로 변환
    df_big4['링크'] = df_big4['링크'].apply(lambda x: f'<a href="{x}" target="_blank">보기</a>' if x else '')
    
    # HTML로 표시 (링크 클릭 가능)
    st.markdown(
        df_big4.to_html(
            index=False,
            escape=False,
            classes=['dataframe'],
            table_id='big4-table'
        ),
        unsafe_allow_html=True
    )
    
    # CSS 스타일 추가
    st.markdown("""
    <style>
    #big4-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 14px;
    }
    #big4-table th {
        background-color: #f0f2f6;
        color: #262730;
        font-weight: 600;
        padding: 12px 8px;
        text-align: left;
        border-bottom: 2px solid #e0e0e0;
    }
    #big4-table td {
        padding: 12px 8px;
        border: 1px solid #e0e0e0;
        vertical-align: top;
        line-height: 1.5;
    }
    #big4-table tr:hover {
        background-color: #f8f9fa;
    }
    #big4-table a {
        color: #0066cc;
        text-decoration: none;
        font-weight: 500;
    }
    #big4-table a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    # 빈 표 표시 (링크 컬럼 포함)
    empty_big4_data = [{"경쟁사": "", "활동 구분": "", "내용": "", "링크": ""}]
    st.dataframe(pd.DataFrame(empty_big4_data), use_container_width=True, hide_index=True)

st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)

# 1-3. 기타 외부 주요 발간물 (작성자: 실제 기관/업체명)
st.subheader("• 기타 외부 주요 발간물")
st.info("기타 공신력 있는 기관/컨설팅펌의 발간물을 리서치하여 표에 기입합니다.")

# 외부 데이터 표시
if st.session_state.external_data:
    df_external = pd.DataFrame(st.session_state.external_data)
    
    # 링크 컬럼이 없으면 추가
    if '링크' not in df_external.columns:
        df_external['링크'] = ''
    
    # 내용 컬럼의 줄바꿈을 HTML <br>로 변환
    df_external['제목(내용)'] = df_external['제목(내용)'].apply(lambda x: x.replace('\n', '<br>') if isinstance(x, str) else x)
    
    # 링크 컬럼을 클릭 가능한 링크로 변환
    df_external['링크'] = df_external['링크'].apply(lambda x: f'<a href="{x}" target="_blank">보기</a>' if x else '')
    
    # HTML로 표시 (링크 클릭 가능)
    st.markdown(
        df_external.to_html(
            index=False,
            escape=False,
            classes=['dataframe'],
            table_id='external-table'
        ),
        unsafe_allow_html=True
    )
    
    # CSS 스타일 추가
    st.markdown("""
    <style>
    #external-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 14px;
    }
    #external-table th {
        background-color: #f0f2f6;
        color: #262730;
        font-weight: 600;
        padding: 12px 8px;
        text-align: left;
        border-bottom: 2px solid #e0e0e0;
    }
    #external-table td {
        padding: 12px 8px;
        border: 1px solid #e0e0e0;
        vertical-align: top;
        line-height: 1.5;
    }
    #external-table tr:hover {
        background-color: #f8f9fa;
    }
    #external-table a {
        color: #0066cc;
        text-decoration: none;
        font-weight: 500;
    }
    #external-table a:hover {
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    # 빈 표 표시 (링크 컬럼 포함)
    empty_external_data = [{"제목(내용)": "", "기관/업체명": "", "링크": ""}]
    st.dataframe(pd.DataFrame(empty_external_data), use_container_width=True, hide_index=True)

st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)

st.header("2. Industry Edge 자료 소개 (Internal Only)")
# 3행 2열(구분, 주요 내용) 공란 표
industry_edge_data = [
    ["", ""],
    ["", ""],
    ["", ""]
]
st.dataframe(pd.DataFrame(industry_edge_data, columns=["구분", "주요 내용"]), use_container_width=True, hide_index=True)

st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)

st.header("3. Upcoming 행사 (국내외, PwC 포함)")
st.info("해당 산업의 주요 행사/세미나/컨퍼런스를 리서치하여 표에 기입합니다.")

# 행사 데이터 표시
if st.session_state.event_data:
    df_events = pd.DataFrame(st.session_state.event_data)
    st.dataframe(df_events, use_container_width=True, hide_index=True)
    
    # 링크 표시
    st.markdown("**🔗 행사 링크:**")
    for _, row in df_events.iterrows():
        st.markdown(f"- [{row['행사명']}]({row['링크']})")
else:
    # 빈 표 표시
    empty_event_data = [{"행사명": "", "주최": "", "일정 및 장소": "", "행사 내용": ""}]
    st.dataframe(pd.DataFrame(empty_event_data), use_container_width=True, hide_index=True)

# 메인 실행 버튼
st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
        with st.spinner("모든 분석을 실행하고 있습니다..."):
            
            # 1. PwC 발간물 분석
            if uploaded_file:
                st.info("📄 PwC 발간물 분석 중...")
                st.info(f"사용 프롬프트: {st.session_state.pwc_prompt}")
                if uploaded_file.type == "application/pdf":
                    text = extract_text_from_pdf(uploaded_file)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    text = extract_text_from_docx(uploaded_file)
                else:
                    text = ""
                
                if text:
                    analysis = analyze_document_content(text, uploaded_file.name)
                    st.session_state.pwc_data = [
                        {
                            "제목(내용)": f"(원문) {analysis['title']}\n(국문) {analysis['translated_title']}\n: {analysis['summary']}",
                            "작성자": analysis['author']
                        }
                    ]
            
            # 2. Big4 발간물 검색
            st.info("🔍 Big4 발간물 검색 중...")
            st.info(f"사용 프롬프트: {st.session_state.big4_prompt}")
            st.session_state.big4_data = search_big4_publications(industry, report_start, report_end)
            
            # 3. 외부 발간물 검색
            st.info("🔍 외부 발간물 검색 중...")
            st.info(f"사용 프롬프트: {st.session_state.external_prompt}")
            st.session_state.external_data = search_external_publications(industry, report_start, report_end)
            
            # 4. 행사 정보 검색
            st.info("🔍 행사 정보 검색 중...")
            st.info(f"사용 프롬프트: {st.session_state.event_prompt}")
            st.session_state.event_data = search_upcoming_events(industry, event_start, event_end)
            
            st.success("✅ 모든 분석이 완료되었습니다!")
            st.rerun()

# 전체 초기화 버튼
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🗑️ 모든 데이터 초기화", use_container_width=True):
        st.session_state.pwc_data = []
        st.session_state.big4_data = []
        st.session_state.external_data = []
        st.session_state.event_data = []
        st.success("✅ 모든 데이터가 초기화되었습니다!")
        st.rerun()

# PDF 출력 섹션 (맨 하단으로 이동)
st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)
st.header("📄 PDF 출력")

# PDF 생성 함수
def generate_pdf_report(industry, report_start, report_end, event_start, event_end, 
                       pwc_data, big4_data, external_data, event_data):
    """전체 분석 결과를 PDF로 생성"""
    
    # HTML 템플릿 생성
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Industry Intelligence Report - {industry}</title>
        <style>
            body {{
                font-family: 'Malgun Gothic', Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                background-color: #e95c0f;
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .header h2 {{
                margin: 5px 0 0 0;
                font-size: 18px;
                font-weight: normal;
            }}
            .info-section {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                margin-bottom: 20px;
                border-left: 4px solid #e95c0f;
            }}
            .section-title {{
                color: #e95c0f;
                font-size: 20px;
                font-weight: bold;
                margin: 30px 0 15px 0;
                border-bottom: 2px solid #e95c0f;
                padding-bottom: 5px;
            }}
            .subsection-title {{
                color: #333;
                font-size: 16px;
                font-weight: bold;
                margin: 20px 0 10px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 12px;
            }}
            th {{
                background-color: #e95c0f;
                color: white;
                padding: 10px 8px;
                text-align: left;
                font-weight: bold;
                border: 1px solid #ddd;
            }}
            td {{
                padding: 10px 8px;
                border: 1px solid #ddd;
                vertical-align: top;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .link {{
                color: #0066cc;
                text-decoration: none;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Industry Intelligence</h1>
            <h2>{industry}</h2>
        </div>
        
        <div class="info-section">
            <strong>발간물 기간:</strong> {report_start.strftime('%Y년 %m월 %d일')} ~ {report_end.strftime('%Y년 %m월 %d일')}<br>
            <strong>행사 기간:</strong> {event_start.strftime('%Y년 %m월 %d일')} ~ {event_end.strftime('%Y년 %m월 %d일')}<br>
            <strong>생성일:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}
        </div>
        
        <div class="section-title">1. Thought Leadership</div>
        
        <div class="subsection-title">• PwC 발간물 (Global 및 한국 포함)</div>
        """
    
    # PwC 데이터 추가
    if pwc_data:
        html_content += """
        <table>
            <thead>
                <tr>
                    <th>제목(내용)</th>
                    <th>작성자</th>
                </tr>
            </thead>
            <tbody>"""
        for item in pwc_data:
            content = item.get('제목(내용)', '').replace('\n', '<br>')
            author = item.get('작성자', '')
            html_content += f"""
                <tr>
                    <td>{content}</td>
                    <td>{author}</td>
                </tr>"""
        html_content += """
            </tbody>
        </table>"""
    else:
        html_content += "<p><em>PwC 발간물 데이터가 없습니다.</em></p>"
    
    # Big4 데이터 추가
    html_content += """
        <div class="subsection-title">• Big4 타 법인 주요 활동 및 발간물</div>"""
    
    if big4_data:
        html_content += """
        <table>
            <thead>
                <tr>
                    <th>경쟁사</th>
                    <th>활동 구분</th>
                    <th>내용</th>
                    <th>링크</th>
                </tr>
            </thead>
            <tbody>"""
        for item in big4_data:
            content = item.get('내용', '').replace('\n', '<br>')
            link = item.get('링크', '')
            link_html = f'<a href="{link}" class="link">보기</a>' if link else ''
            html_content += f"""
                <tr>
                    <td>{item.get('경쟁사', '')}</td>
                    <td>{item.get('활동 구분', '')}</td>
                    <td>{content}</td>
                    <td>{link_html}</td>
                </tr>"""
        html_content += """
            </tbody>
        </table>"""
    else:
        html_content += "<p><em>Big4 발간물 데이터가 없습니다.</em></p>"
    
    # 외부 발간물 데이터 추가
    html_content += """
        <div class="subsection-title">• 기타 외부 주요 발간물</div>"""
    
    if external_data:
        html_content += """
        <table>
            <thead>
                <tr>
                    <th>제목(내용)</th>
                    <th>기관/업체명</th>
                    <th>링크</th>
                </tr>
            </thead>
            <tbody>"""
        for item in external_data:
            content = item.get('제목(내용)', '').replace('\n', '<br>')
            link = item.get('링크', '')
            link_html = f'<a href="{link}" class="link">보기</a>' if link else ''
            html_content += f"""
                <tr>
                    <td>{content}</td>
                    <td>{item.get('기관/업체명', '')}</td>
                    <td>{link_html}</td>
                </tr>"""
        html_content += """
            </tbody>
        </table>"""
    else:
        html_content += "<p><em>외부 발간물 데이터가 없습니다.</em></p>"
    
    # Industry Edge 섹션
    html_content += """
        <div class="section-title">2. Industry Edge 자료 소개 (Internal Only)</div>
        <table>
            <thead>
                <tr>
                    <th>구분</th>
                    <th>주요 내용</th>
                </tr>
            </thead>
            <tbody>
                <tr><td></td><td></td></tr>
                <tr><td></td><td></td></tr>
                <tr><td></td><td></td></tr>
            </tbody>
        </table>"""
    
    # 행사 데이터 추가
    html_content += """
        <div class="section-title">3. Upcoming 행사 (국내외, PwC 포함)</div>"""
    
    if event_data:
        html_content += """
        <table>
            <thead>
                <tr>
                    <th>행사명</th>
                    <th>주최</th>
                    <th>일정 및 장소</th>
                    <th>행사 내용</th>
                    <th>링크</th>
                </tr>
            </thead>
            <tbody>"""
        for item in event_data:
            link = item.get('링크', '')
            link_html = f'<a href="{link}" class="link">보기</a>' if link else ''
            html_content += f"""
                <tr>
                    <td>{item.get('행사명', '')}</td>
                    <td>{item.get('주최', '')}</td>
                    <td>{item.get('일정 및 장소', '')}</td>
                    <td>{item.get('행사 내용', '')}</td>
                    <td>{link_html}</td>
                </tr>"""
        html_content += """
            </tbody>
        </table>"""
    else:
        html_content += "<p><em>행사 데이터가 없습니다.</em></p>"
    
    # 푸터
    html_content += f"""
        <div class="footer">
            <p>Industry Intelligence Report - {industry}</p>
            <p>생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</p>
            <p>© 2025 PwC. All rights reserved.</p>
        </div>
    </body>
    </html>"""
    
    return html_content

# PDF 다운로드 버튼
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("📄 PDF 다운로드", type="primary", use_container_width=True):
        with st.spinner("PDF를 생성하고 있습니다..."):
            try:
                # HTML 생성
                html_content = generate_pdf_report(
                    industry=industry,
                    report_start=report_start,
                    report_end=report_end,
                    event_start=event_start,
                    event_end=event_end,
                    pwc_data=st.session_state.pwc_data,
                    big4_data=st.session_state.big4_data,
                    external_data=st.session_state.external_data,
                    event_data=st.session_state.event_data
                )
                
                # HTML을 파일로 저장
                html_filename = f"Industry_Intelligence_{industry.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                
                # HTML 파일 다운로드
                st.download_button(
                    label="💾 HTML 파일 다운로드",
                    data=html_content,
                    file_name=html_filename,
                    mime="text/html",
                    use_container_width=True
                )
                
                st.success("✅ HTML 파일이 생성되었습니다! 다운로드 후 브라우저에서 열어 PDF로 저장하세요.")
                st.info("💡 팁: 브라우저에서 HTML 파일을 열고 Ctrl+P (또는 Cmd+P)를 눌러 PDF로 저장할 수 있습니다.")
                
            except Exception as e:
                st.error(f"PDF 생성 중 오류가 발생했습니다: {str(e)}")
                st.info("HTML 파일로 다운로드하여 브라우저에서 PDF로 변환하세요.")

# PDF 미리보기 자동 표시 (데이터가 있을 때만)
if (st.session_state.pwc_data or st.session_state.big4_data or 
    st.session_state.external_data or st.session_state.event_data):
    
    st.markdown("<hr style='border:1px solid #e95c0f;'>", unsafe_allow_html=True)
    st.subheader("👁️ PDF 미리보기")
    
    try:
        # HTML 생성
        html_content = generate_pdf_report(
            industry=industry,
            report_start=report_start,
            report_end=report_end,
            event_start=event_start,
            event_end=event_end,
            pwc_data=st.session_state.pwc_data,
            big4_data=st.session_state.big4_data,
            external_data=st.session_state.external_data,
            event_data=st.session_state.event_data
        )
        
        # HTML 미리보기 표시
        st.markdown("### 📋 생성된 PDF 미리보기")
        st.markdown("아래 내용을 확인하고, 필요시 데이터를 수정한 후 다시 분석을 실행하세요.")
        
        # HTML을 iframe으로 표시
        st.components.v1.html(
            html_content,
            height=800,
            scrolling=True
        )
        
        # 다운로드 옵션
        st.markdown("### 💾 다운로드 옵션")
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 HTML 파일 다운로드",
                data=html_content,
                file_name=f"Industry_Intelligence_{industry.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col2:
            # HTML 소스 코드 다운로드
            st.download_button(
                label="📝 HTML 소스 다운로드",
                data=html_content,
                file_name=f"Industry_Intelligence_{industry.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_source.html",
                mime="text/plain",
                use_container_width=True
            )
        
        st.success("✅ PDF 미리보기가 생성되었습니다!")
        st.info("💡 팁: 미리보기에서 Ctrl+P (또는 Cmd+P)를 눌러 PDF로 저장할 수 있습니다.")
        
    except Exception as e:
        st.error(f"PDF 미리보기 생성 중 오류가 발생했습니다: {str(e)}")

# 미리보기 안내
st.info("📋 위의 'PDF 미리보기 생성' 버튼을 클릭하면 화면에서 바로 PDF 페이지를 확인할 수 있습니다.")
st.markdown("""
**미리보기 기능:**
- 📄 전체 분석 결과를 HTML 형태로 미리보기
- 🔍 실시간으로 내용 확인 가능
- 💾 HTML 파일로 다운로드 가능
- 🖨️ 브라우저에서 바로 PDF로 저장 가능
""")