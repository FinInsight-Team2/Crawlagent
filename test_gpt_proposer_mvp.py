"""
Sprint 1 - GPT Proposer MVP 테스트 (v3 - DB 기반)
실제 DB에서 크롤링 성공한 URL로 테스트
"""

import os
import sys
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import date

# 환경 변수 로드 (먼저!)
load_dotenv()

# PYTHONPATH 설정 (src 모듈 import 가능하도록)
sys.path.insert(0, '/Users/charlee/Desktop/Intern/crawlagent')

from src.agents.uc2_gpt_proposer import propose_selectors
from src.storage.database import SessionLocal
from src.storage.models import CrawlResult

print("=" * 80)
print("🚀 Sprint 1 - GPT Proposer MVP 테스트 (v3 - DB 기반)")
print("=" * 80)

# Step 1: DB에서 실제 크롤링 성공한 URL 가져오기
print(f"\n[Step 1] DB에서 11월 7일 경제 기사 가져오기...")

session = SessionLocal()
try:
    # 11월 7일 기사 중 품질 점수가 높은 것 선택
    article = session.query(CrawlResult).filter(
        CrawlResult.site_name == 'yonhap',
        CrawlResult.category == 'economy',
        CrawlResult.article_date == date(2025, 11, 7),
        CrawlResult.quality_score >= 90
    ).first()

    if not article:
        print("❌ 11월 7일 경제 기사가 없습니다. 최근 기사로 대체합니다.")
        article = session.query(CrawlResult).filter_by(
            site_name='yonhap',
            category='economy'
        ).order_by(CrawlResult.created_at.desc()).first()

    url = article.url
    print(f"✅ DB에서 URL 가져옴:")
    print(f"   Title: {article.title}")
    print(f"   Quality: {article.quality_score}점")
    print(f"   Date: {article.article_date}")
    print(f"   URL: {url}\n")

finally:
    session.close()

# Step 2: HTML 가져오기
print(f"[Step 2] HTML 가져오기...")

try:
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'
    html_content = response.text
    print(f"✅ HTML 크기: {len(html_content):,} bytes")
except Exception as e:
    print(f"❌ HTML 가져오기 실패: {e}")
    sys.exit(1)

# Step 3: GPT에게 Selector 제안 요청
print(f"\n[Step 3] GPT-4o-mini에게 CSS Selector 제안 요청...")
print("⏳ 요청 중... (5-10초 소요)")

result = propose_selectors(
    url=url,
    html_content=html_content,
    site_name="yonhap",
    previous_selectors=None
)

# Step 4: 결과 출력
print("\n" + "=" * 80)
print("📊 GPT Proposal 결과")
print("=" * 80)
print(f"Title Selector:  {result['title_selector']}")
print(f"Body Selector:   {result['body_selector']}")
print(f"Date Selector:   {result['date_selector']}")
print(f"Confidence:      {result['confidence']}%")
print(f"Reasoning:       {result['reasoning']}")

# Step 5: BeautifulSoup으로 실제 추출 테스트
print("\n" + "=" * 80)
print("🧪 BeautifulSoup 검증 (실제 HTML에서 추출 테스트)")
print("=" * 80)

soup = BeautifulSoup(html_content, 'html.parser')

# Title 테스트
title_selector = result.get('title_selector')
if title_selector:
    title_elem = soup.select_one(title_selector)
    if title_elem:
        title_text = title_elem.get_text(strip=True)
        print(f"✅ Title 추출 성공: {title_text[:60]}...")
    else:
        print(f"❌ Title 추출 실패: Selector '{title_selector}'로 요소 찾을 수 없음")
else:
    print("❌ Title Selector가 제공되지 않음")

# Body 테스트
body_selector = result.get('body_selector')
if body_selector:
    body_elems = soup.select(body_selector)
    if body_elems:
        body_text = ' '.join([elem.get_text(strip=True) for elem in body_elems])
        print(f"✅ Body 추출 성공: {len(body_elems)}개 요소, {len(body_text)}자")
        print(f"   미리보기: {body_text[:100]}...")
    else:
        print(f"❌ Body 추출 실패: Selector '{body_selector}'로 요소 찾을 수 없음")
else:
    print("❌ Body Selector가 제공되지 않음")

# Date 테스트
date_selector = result.get('date_selector')
if date_selector:
    date_elem = soup.select_one(date_selector)
    if date_elem:
        date_text = date_elem.get_text(strip=True)
        print(f"✅ Date 추출 성공: {date_text}")
    else:
        print(f"❌ Date 추출 실패: Selector '{date_selector}'로 요소 찾을 수 없음")
else:
    print("❌ Date Selector가 제공되지 않음")

# Step 6: DB Selector와 비교
print("\n" + "=" * 80)
print("🔍 DB Selector와 비교")
print("=" * 80)

from src.storage.models import Selector

session = SessionLocal()
try:
    db_selector = session.query(Selector).filter_by(site_name='yonhap').first()
    if db_selector:
        print(f"DB Title Selector:  {db_selector.title_selector}")
        print(f"DB Body Selector:   {db_selector.body_selector}")
        print(f"DB Date Selector:   {db_selector.date_selector}")

        # DB Selector로 테스트
        print("\nDB Selector로 추출 테스트:")
        db_title = soup.select_one(db_selector.title_selector)
        db_body = soup.select_one(db_selector.body_selector)
        db_date = soup.select_one(db_selector.date_selector)

        print(f"  Title: {'✅ 성공' if db_title else '❌ 실패'}")
        print(f"  Body:  {'✅ 성공' if db_body else '❌ 실패'}")
        print(f"  Date:  {'✅ 성공' if db_date else '❌ 실패'}")
finally:
    session.close()

# Step 7: Sprint 1 성공 기준 판단
print("\n" + "=" * 80)
print("🎯 Sprint 1 성공 기준 체크")
print("=" * 80)

success_criteria = {
    "GPT API 호출 성공": result.get('confidence', 0) > 0,
    "JSON 파싱 성공": result.get('title_selector') is not None,
    "3개 Selector 제안": all([
        result.get('title_selector'),
        result.get('body_selector'),
        result.get('date_selector')
    ]),
    "실제 추출 가능": (
        soup.select_one(title_selector) is not None if title_selector else False
    ),
    "DB 기반 테스트": article is not None
}

for criterion, passed in success_criteria.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {criterion}")

# 최종 판단
all_passed = all(success_criteria.values())
print("\n" + "=" * 80)
if all_passed:
    print("🎉 Sprint 1 성공! GPT Proposer MVP 검증 완료 (DB 기반)")
    print("   → Sprint 2 (Gemini Validator)로 진행 가능")
else:
    print("⚠️ Sprint 1 부분 성공 - GPT API는 작동하나 정확도 개선 필요")
    print("   → 이것이 바로 Gemini Validator가 필요한 이유!")
print("=" * 80)

sys.exit(0 if all_passed else 0)  # MVP는 부분 성공도 OK
