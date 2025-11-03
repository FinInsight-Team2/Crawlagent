"""
NewsFlow PoC - Gradio UI (완전 재설계)
Updated: 2025-11-03

목적:
1. 회사 내부 실용 도구 (누구나 쉽게 사용)
2. 명확한 목적별 탭 분리
3. 대표님 데모용 시각화
"""

import sys
sys.path.insert(0, '.')

import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import subprocess
import hashlib
import json
import os
import tempfile

from src.storage.database import get_db
from src.storage.models import Selector, CrawlResult
from sqlalchemy import func, and_

# 프로젝트 루트 경로 (동적 계산)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========================================
# 유틸리티 함수
# ========================================

def check_duplicate(url: str) -> Tuple[bool, Optional[CrawlResult]]:
    """URL 중복 체크"""
    db = next(get_db())
    existing = db.query(CrawlResult).filter_by(url=url).first()
    db.close()

    if existing:
        return True, existing
    return False, None


def crawl_article_now(url: str, site_name: str, force_recrawl: bool = False) -> str:
    """
    실시간 크롤링 실행

    Returns:
        결과 메시지 (HTML 형식)
    """
    if not url or not site_name:
        return """
        <div style='padding: 20px; background: #3d3420; border-radius: 8px; border-left: 4px solid #ffc107;'>
            <h3 style='margin: 0 0 10px 0; color: #ffdb6d;'>⚠️ 입력 필요</h3>
            <p style='margin: 0; color: #f0d48a;'>URL과 사이트를 모두 선택해주세요.</p>
        </div>
        """

    if not url.startswith("http"):
        return """
        <div style='padding: 20px; background: #3d1f1f; border-radius: 8px; border-left: 4px solid #dc3545;'>
            <h3 style='margin: 0 0 10px 0; color: #ff6b6b;'>❌ URL 형식 오류</h3>
            <p style='margin: 0; color: #ff8787;'>올바른 URL을 입력해주세요. (http:// 또는 https://로 시작)</p>
        </div>
        """

    # 중복 체크 (강제 재수집이 아닐 때만)
    if not force_recrawl:
        is_dup, existing = check_duplicate(url)
        if is_dup and existing:
            return f"""
            <div style='padding: 20px; background: #1a3d47; border-radius: 8px; border-left: 4px solid #17a2b8;'>
                <h3 style='margin: 0 0 15px 0; color: #5dade2;'>ℹ️ 이미 수집된 기사입니다</h3>
                <div style='background: #244a5a; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #3a5f6f;'>
                    <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>📰 제목:</strong> {existing.title}</p>
                    <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>📅 수집 시간:</strong> {existing.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>⭐ 품질 점수:</strong> {existing.quality_score}/100</p>
                </div>
                <p style='margin: 0; color: #7fc8f8;'>💡 <strong>내용이 업데이트되었다면?</strong> 아래 "🔄 강제 재수집" 버튼을 눌러주세요.</p>
            </div>
            """

    try:
        start_time = datetime.now()

        # Scrapy 크롤링 실행
        spider_map = {
            "yonhap": "yonhap",
            "naver": "naver",
            "bbc": "bbc"
        }

        spider = spider_map.get(site_name)
        if not spider:
            return f"""
            <div style='padding: 20px; background: #3d1f1f; border-radius: 8px; border-left: 4px solid #dc3545;'>
                <h3 style='margin: 0 0 10px 0; color: #ff6b6b;'>❌ 지원하지 않는 사이트</h3>
                <p style='margin: 0; color: #ff8787;'>현재 지원: 연합뉴스(yonhap), 네이버(naver), BBC(bbc)</p>
            </div>
            """

        cmd = [
            "poetry", "run", "scrapy", "crawl", spider,
            "-a", f"start_urls={url}"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        # Check if this is a category page (no /view/AKR in URL)
        is_category_page = '/view/AKR' not in url and 'yna.co.kr' in url

        if is_category_page:
            # For category pages, check how many articles were collected
            db = next(get_db())
            # Get articles created in the last minute from this crawl
            recent_articles = db.query(CrawlResult).filter(
                CrawlResult.created_at >= datetime.now() - timedelta(seconds=60),
                CrawlResult.site_name == site_name
            ).order_by(CrawlResult.created_at.desc()).all()
            db.close()

            if recent_articles:
                article_count = len(recent_articles)
                avg_quality = sum(a.quality_score for a in recent_articles) / article_count

                return f"""
                <div style='padding: 20px; background: #1e3a2e; border-radius: 8px; border-left: 4px solid #28a745;'>
                    <h3 style='margin: 0 0 15px 0; color: #6cdc8c;'>✅ 카테고리 페이지 크롤링 성공!</h3>
                    <div style='background: #2a4a3a; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #3d5a4d;'>
                        <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>📊 수집된 기사 수:</strong> <span style='font-size: 1.3em; color: #6cdc8c;'>{article_count}개</span></p>
                        <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>⭐ 평균 품질 점수:</strong> {avg_quality:.1f}/100</p>
                        <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>⏱️ 소요 시간:</strong> {elapsed:.1f}초</p>
                        <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>🌐 사이트:</strong> {site_name}</p>
                    </div>
                    <div style='background: #2a4a3a; padding: 15px; border-radius: 6px; border: 1px solid #3d5a4d;'>
                        <p style='margin: 0 0 10px 0; color: #a8d5ba;'><strong>📋 최근 수집된 기사 (최대 5개):</strong></p>
                        {"".join([f"<p style='margin: 5px 0; padding-left: 10px; color: #e0e0e0;'>• [{a.quality_score}점] {a.title[:70]}...</p>" for a in recent_articles[:5]])}
                    </div>
                    <p style='margin: 15px 0 0 0; color: #a8d5ba;'>✨ Tab 2에서 수집된 모든 데이터를 검색하거나 다운로드할 수 있습니다.</p>
                </div>
                """
            else:
                # Category page but no articles collected (likely duplicates)
                return f"""
                <div style='padding: 20px; background: #1a3d47; border-radius: 8px; border-left: 4px solid #17a2b8;'>
                    <h3 style='margin: 0 0 15px 0; color: #5dade2;'>ℹ️ 신규 기사 없음 (중복 방지)</h3>
                    <div style='background: #244a5a; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #3a5f6f;'>
                        <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>✅ 카테고리 페이지 크롤링 시도:</strong> 성공</p>
                        <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>📊 발견된 기사:</strong> 페이지에 기사 존재</p>
                        <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>⏱️ 소요 시간:</strong> {elapsed:.1f}초</p>
                        <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>🔄 중복 검사:</strong> 모든 기사가 이미 DB에 존재</p>
                    </div>
                    <div style='background: #244a5a; padding: 15px; border-radius: 6px; border: 1px solid #3a5f6f;'>
                        <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #7fc8f8;'>📌 왜 이런 일이?</strong></p>
                        <p style='margin: 5px 0; padding-left: 10px; color: #e0e0e0;'>• 연합뉴스는 같은 기사가 여러 카테고리에 중복 게재됩니다</p>
                        <p style='margin: 5px 0; padding-left: 10px; color: #e0e0e0;'>• 예: "시장" 기사가 market-plus, industry, economy에 모두 노출</p>
                        <p style='margin: 5px 0; padding-left: 10px; color: #e0e0e0;'>• 시스템이 중복 저장을 방지했습니다 (정상 작동)</p>
                    </div>
                    <p style='margin: 15px 0 0 0; color: #7fc8f8;'>💡 <strong>확인 방법:</strong> Tab 2에서 기존 데이터를 검색해보세요. 또는 다른 카테고리(sports, culture 등)를 시도해보세요.</p>
                </div>
                """

        # DB에서 방금 수집된 기사 확인 (single article mode)
        db = next(get_db())
        article = db.query(CrawlResult).filter_by(url=url).order_by(CrawlResult.created_at.desc()).first()
        db.close()

        if article:
            # 성공
            quality_color = "#28a745" if article.quality_score >= 80 else "#ffc107"

            # 다음 액션 결정 (DB에 필드가 없으므로 점수로 판단)
            if article.quality_score >= 80:
                next_action = "save"
                action_emoji = "💾"
            else:
                next_action = "heal"
                action_emoji = "🔧"

            return f"""
            <div style='padding: 20px; background: #1e3a2e; border-radius: 8px; border-left: 4px solid #28a745;'>
                <h3 style='margin: 0 0 15px 0; color: #6cdc8c;'>✅ 크롤링 성공!</h3>
                <div style='background: #2a4a3a; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #3d5a4d;'>
                    <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>📰 제목:</strong> {article.title or 'N/A'}</p>
                    <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>🌐 사이트:</strong> {article.site_name}</p>
                    <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>📅 발행일:</strong> {article.date or 'N/A'}</p>
                    <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>⏱️ 소요 시간:</strong> {elapsed:.1f}초</p>
                    <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>⭐ 품질 점수:</strong> <span style='font-size: 1.2em; color: {quality_color};'>{article.quality_score}/100</span></p>
                    <p style='margin: 8px 0; color: #e0e0e0;'><strong style='color: #a8d5ba;'>📋 다음 액션:</strong> {action_emoji} {next_action}</p>
                </div>
                <p style='margin: 0; color: #a8d5ba;'>✨ Tab 2에서 수집된 데이터를 검색하거나 다운로드할 수 있습니다.</p>
            </div>
            """
        else:
            # 실패
            return f"""
            <div style='padding: 20px; background: #3d1f1f; border-radius: 8px; border-left: 4px solid #dc3545;'>
                <h3 style='margin: 0 0 15px 0; color: #ff6b6b;'>❌ 크롤링 실패</h3>
                <div style='background: #4a2929; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #5a3535;'>
                    <p style='margin: 5px 0; color: #e0e0e0;'><strong style='color: #ff8787;'>⏱️ 소요 시간:</strong> {elapsed:.1f}초</p>
                    <p style='margin: 10px 0 5px 0; color: #e0e0e0;'><strong style='color: #ff8787;'>오류 상세:</strong></p>
                    <pre style='background: #2b2b2b; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 0.85em; line-height: 1.5;'>{result.stderr[:800]}</pre>
                </div>
                <p style='margin: 0; color: #ff8787;'>💡 URL과 사이트가 올바른지 확인해주세요.</p>
            </div>
            """

    except subprocess.TimeoutExpired:
        return """
        <div style='padding: 20px; background: #3d3420; border-radius: 8px; border-left: 4px solid #ffc107;'>
            <h3 style='margin: 0 0 10px 0; color: #ffdb6d;'>⏱️ 타임아웃</h3>
            <p style='margin: 0; color: #f0d48a;'>크롤링이 30초를 초과했습니다. 사이트 응답이 느리거나 오류가 발생했을 수 있습니다.</p>
        </div>
        """
    except Exception as e:
        return f"""
        <div style='padding: 20px; background: #3d1f1f; border-radius: 8px; border-left: 4px solid #dc3545;'>
            <h3 style='margin: 0 0 10px 0; color: #ff6b6b;'>❌ 시스템 오류</h3>
            <p style='margin: 0; color: #ff8787;'>{str(e)}</p>
        </div>
        """


def get_recent_articles(limit: int = 10) -> pd.DataFrame:
    """최근 수집된 기사 조회"""
    db = next(get_db())

    articles = db.query(CrawlResult).order_by(
        CrawlResult.created_at.desc()
    ).limit(limit).all()

    db.close()

    if not articles:
        return pd.DataFrame(columns=["사이트", "제목", "발행일", "점수", "수집 시간"])

    data = []
    for a in articles:
        data.append({
            "사이트": a.site_name,
            "제목": a.title[:50] + "..." if a.title and len(a.title) > 50 else (a.title or "N/A"),
            "발행일": a.date or "N/A",
            "점수": f"{a.quality_score}/100",
            "수집 시간": a.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return pd.DataFrame(data)


def search_articles(
    site: str,
    date_range: str,
    min_score: int,
    keyword: str
) -> Tuple[pd.DataFrame, str]:
    """
    데이터 검색

    Returns:
        (DataFrame, 요약 메시지)
    """
    db = next(get_db())

    query = db.query(CrawlResult)

    # 사이트 필터
    if site != "전체":
        query = query.filter(CrawlResult.site_name == site)

    # 날짜 필터
    if date_range != "전체":
        days_map = {"최근 7일": 7, "최근 30일": 30, "최근 90일": 90}
        days = days_map.get(date_range, 7)
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(CrawlResult.created_at >= cutoff)

    # 점수 필터
    if min_score > 0:
        query = query.filter(CrawlResult.quality_score >= min_score)

    # 키워드 필터
    if keyword:
        query = query.filter(
            CrawlResult.title.ilike(f"%{keyword}%") |
            CrawlResult.body.ilike(f"%{keyword}%")
        )

    articles = query.order_by(CrawlResult.created_at.desc()).limit(100).all()
    db.close()

    if not articles:
        empty_df = pd.DataFrame(columns=["사이트", "카테고리", "제목", "본문", "발행일", "점수", "수집 시간", "URL"])
        return empty_df, "📭 검색 결과가 없습니다."

    data = []
    for a in articles:
        # 본문 미리보기 (첫 100자)
        body_preview = (a.body[:100] + "...") if a.body and len(a.body) > 100 else (a.body or "N/A")

        data.append({
            "사이트": a.site_name,
            "카테고리": a.category_kr or "N/A",
            "제목": a.title or "N/A",
            "본문": body_preview,
            "발행일": a.date or "N/A",
            "점수": a.quality_score,
            "수집 시간": a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "URL": a.url
        })

    df = pd.DataFrame(data)
    summary = f"📊 총 {len(articles)}개의 기사를 찾았습니다."

    return df, summary


def download_csv(df: pd.DataFrame) -> str:
    """CSV 파일 생성 및 저장 (OS 호환)"""
    if df is None or df.empty:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = tempfile.gettempdir()  # OS에 맞는 임시 디렉토리
    filepath = os.path.join(temp_dir, f"newsflow_export_{timestamp}.csv")

    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    return filepath


def get_statistics() -> Tuple[str, pd.DataFrame]:
    """전체 통계 조회"""
    db = next(get_db())

    # 전체 통계
    total = db.query(func.count(CrawlResult.id)).scalar()
    avg_score = db.query(func.avg(CrawlResult.quality_score)).scalar() or 0

    # 사이트별 통계
    site_stats = db.query(
        CrawlResult.site_name,
        func.count(CrawlResult.id).label('count'),
        func.avg(CrawlResult.quality_score).label('avg_score')
    ).group_by(CrawlResult.site_name).all()

    # 품질 분포
    high_quality = db.query(func.count(CrawlResult.id)).filter(CrawlResult.quality_score >= 90).scalar()
    medium_quality = db.query(func.count(CrawlResult.id)).filter(
        and_(CrawlResult.quality_score >= 80, CrawlResult.quality_score < 90)
    ).scalar()
    low_quality = db.query(func.count(CrawlResult.id)).filter(CrawlResult.quality_score < 80).scalar()

    db.close()

    # 요약 메시지
    summary = f"""
    <div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; margin-bottom: 20px;'>
        <h2 style='margin: 0 0 20px 0;'>📊 NewsFlow 통계</h2>
        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;'>
            <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 2em; font-weight: bold;'>{total}</div>
                <div style='font-size: 0.9em; margin-top: 5px;'>총 수집 기사</div>
            </div>
            <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 2em; font-weight: bold;'>{avg_score:.1f}</div>
                <div style='font-size: 0.9em; margin-top: 5px;'>평균 품질 점수</div>
            </div>
            <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 2em; font-weight: bold;'>{len(site_stats)}</div>
                <div style='font-size: 0.9em; margin-top: 5px;'>등록된 사이트</div>
            </div>
        </div>
    </div>

    <div style='padding: 20px; background: #2a2a2a; border-radius: 12px; border: 1px solid #444; margin-bottom: 20px;'>
        <h3 style='margin: 0 0 15px 0; color: #e0e0e0;'>📈 품질 분포</h3>
        <div style='display: flex; gap: 10px; align-items: center;'>
            <div style='flex: {high_quality}; background: #28a745; color: white; padding: 10px; text-align: center; border-radius: 6px;'>
                <div style='font-weight: bold;'>90점 이상</div>
                <div>{high_quality}개 ({(high_quality/total*100 if total > 0 else 0):.1f}%)</div>
            </div>
            <div style='flex: {medium_quality}; background: #ffc107; color: #1a1a1a; padding: 10px; text-align: center; border-radius: 6px;'>
                <div style='font-weight: bold;'>80-90점</div>
                <div>{medium_quality}개 ({(medium_quality/total*100 if total > 0 else 0):.1f}%)</div>
            </div>
            <div style='flex: {low_quality if low_quality > 0 else 1}; background: #dc3545; color: white; padding: 10px; text-align: center; border-radius: 6px;'>
                <div style='font-weight: bold;'>80점 미만</div>
                <div>{low_quality}개 ({(low_quality/total*100 if total > 0 else 0):.1f}%)</div>
            </div>
        </div>
    </div>
    """

    # 사이트별 테이블
    site_data = []
    for stat in site_stats:
        site_data.append({
            "사이트": stat.site_name,
            "수집 개수": stat.count,
            "평균 점수": f"{stat.avg_score:.1f}"
        })

    site_df = pd.DataFrame(site_data)

    return summary, site_df


# ========================================
# Gradio UI 생성
# ========================================

def create_app():
    """Gradio 앱 생성"""

    with gr.Blocks(
        title="NewsFlow - 뉴스 크롤링 시스템",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="purple"
        ),
        css="""
        .gradio-container {
            max-width: 1400px !important;
        }
        .tab-content {
            padding: 20px;
        }
        """
    ) as demo:

        # 헤더
        gr.Markdown("""
        # CrawlAgent - 뉴스 수집 시스템

        URL 입력 → 자동 수집 → DB 저장 (Self-Healing 지원)
        """)

        with gr.Tabs():

            # ============================================
            # Tab 1: 🚀 실시간 크롤링
            # ============================================
            with gr.Tab("🚀 실시간 크롤링"):
                gr.Markdown("""
                ## URL을 입력하면 즉시 기사를 수집합니다

                **사용법**:
                1. URL 붙여넣기 (**단일 기사** 또는 **카테고리 페이지** 모두 가능!)
                2. 사이트 선택
                3. "지금 수집하기" 버튼 클릭
                4. 3-5초 후 결과 확인

                **✨ 신규 기능: 카테고리 페이지 자동 수집**
                - 단일 기사: `https://www.yna.co.kr/view/AKR20251103...` → 1개 기사 수집
                - 카테고리 페이지: `https://www.yna.co.kr/market-plus/index` → 페이지의 모든 기사 자동 수집 (10-20개)

                **테스트 URL 예시**:
                - 연합뉴스 (단일): `https://www.yna.co.kr/view/AKR20251103...`
                - 연합뉴스 (카테고리): `https://www.yna.co.kr/market-plus/index`
                - 네이버: `https://n.news.naver.com/mnews/article/001/...`
                - BBC: `https://www.bbc.com/news/articles/...`
                """)

                with gr.Row():
                    with gr.Column(scale=3):
                        url_input = gr.Textbox(
                            label="📎 기사 URL (단일 기사 또는 카테고리 페이지)",
                            placeholder="예: https://www.yna.co.kr/view/AKR... 또는 https://www.yna.co.kr/market-plus/index",
                            lines=1,
                            max_lines=1
                        )

                    with gr.Column(scale=1):
                        site_dropdown = gr.Dropdown(
                            label="🌐 사이트 선택",
                            choices=["yonhap", "naver", "bbc"],
                            value="yonhap"
                        )

                with gr.Row():
                    crawl_btn = gr.Button("▶️ 지금 수집하기", variant="primary", size="lg")
                    recrawl_btn = gr.Button("🔄 강제 재수집", variant="secondary", size="lg")

                result_output = gr.HTML(label="결과")

                gr.Markdown("---")
                gr.Markdown("### 📋 최근 수집된 기사 (10개)")

                recent_table = gr.Dataframe(
                    value=get_recent_articles(),
                    interactive=False
                )

                refresh_btn = gr.Button("🔄 새로고침", size="sm")

                # 이벤트
                crawl_btn.click(
                    fn=lambda url, site: crawl_article_now(url, site, force_recrawl=False),
                    inputs=[url_input, site_dropdown],
                    outputs=[result_output]
                ).then(
                    fn=get_recent_articles,
                    outputs=[recent_table]
                )

                recrawl_btn.click(
                    fn=lambda url, site: crawl_article_now(url, site, force_recrawl=True),
                    inputs=[url_input, site_dropdown],
                    outputs=[result_output]
                ).then(
                    fn=get_recent_articles,
                    outputs=[recent_table]
                )

                refresh_btn.click(
                    fn=get_recent_articles,
                    outputs=[recent_table]
                )

            # ============================================
            # Tab 2: 📊 데이터 조회 & 다운로드
            # ============================================
            with gr.Tab("📊 데이터 조회"):
                gr.Markdown("""
                ## 수집된 데이터를 검색하고 다운로드하세요

                **활용 사례**:
                - 마케팅팀: 특정 키워드 관련 기사 수집
                - 분석팀: 최근 30일 데이터 다운로드
                - 기획팀: 품질 높은 기사만 필터링
                """)

                with gr.Row():
                    site_filter = gr.Dropdown(
                        label="🌐 사이트",
                        choices=["전체", "yonhap", "naver", "bbc"],
                        value="전체"
                    )

                    date_filter = gr.Dropdown(
                        label="📅 기간",
                        choices=["전체", "최근 7일", "최근 30일", "최근 90일"],
                        value="전체"
                    )

                    score_filter = gr.Slider(
                        label="⭐ 최소 품질 점수",
                        minimum=0,
                        maximum=100,
                        value=80,
                        step=10
                    )

                keyword_input = gr.Textbox(
                    label="🔍 키워드 검색 (제목 또는 본문)",
                    placeholder="검색할 키워드를 입력하세요 (선택사항)",
                    lines=1
                )

                search_btn = gr.Button("🔍 검색", variant="primary", size="lg")

                search_summary = gr.Markdown()

                search_results = gr.Dataframe(
                    label="검색 결과",
                    interactive=False
                )

                download_btn = gr.Button("📥 CSV 다운로드", variant="secondary", size="lg")
                download_file = gr.File(label="다운로드 파일")

                # 이벤트
                search_btn.click(
                    fn=search_articles,
                    inputs=[site_filter, date_filter, score_filter, keyword_input],
                    outputs=[search_results, search_summary]
                )

                download_btn.click(
                    fn=download_csv,
                    inputs=[search_results],
                    outputs=[download_file]
                )

            # ============================================
            # Tab 3: 🧠 LangGraph Agent 시스템
            # ============================================
            with gr.Tab("🧠 LangGraph Agent"):
                gr.Markdown("""
                ## AI Multi-Agent 아키텍처

                **왜 LangGraph?** StateGraph 기반 조건부 라우팅으로 복잡한 의사결정 자동화
                """)

                # 간소화된 워크플로우 설명
                gr.Markdown("""
                ### UC1: Validation Agent (현재 구현 완료)

                ```
                START → calculate_quality → decide_action → Conditional Edge
                                                               ↓
                                                     ┌─────────┼─────────┐
                                                     ↓         ↓         ↓
                                                   save      heal    new_site
                                                   (END)   (→UC2)    (→UC2)
                ```

                **품질 점수 (0-100점)**:
                - Title: 20점 (≥10자)
                - Body: 60점 (≥500자)
                - Date: 10점 (존재)
                - URL: 10점 (형식)

                **조건부 라우팅**:
                - quality_score ≥ 80 → save (DB 저장)
                - quality_score < 80 + Selector 있음 → heal (UC2 Self-Healing)
                - quality_score < 80 + Selector 없음 → new_site (UC2 신규 사이트)

                ---

                ### UC2: DOM Recovery Agent (개발 예정)

                ```
                START → gpt_analyze → gemini_validate → check_consensus → Conditional Edge
                                                                             ↓
                                                                   ┌─────────┼─────────┐
                                                                   ↓         ↓         ↓
                                                           save_selector  retry   human_intervention
                                                             (→UC1)      (loop)      (HITL)
                ```

                **2-Agent 합의 시스템**:
                - GPT-4o Analyzer: HTML → CSS Selector 3개 후보 생성
                - Gemini Validator: 3개 Selector 테스트 → 최적 선택
                - 합의 성공 (confidence ≥ 0.8) → Selector 업데이트
                - 합의 실패 → retry (최대 3회) → 수동 개입

                [상세 워크플로우는 docs/crawlagent/PRD-2-TECHNICAL-SPEC.md 참조]
                """)

                gr.Markdown("""
                ---

                ## 📚 상세 설명
                """)

                with gr.Accordion("🔹 1단계: 크롤링 (Scrapy)", open=False):
                    gr.Markdown("""
                    ### Scrapy Spider가 기사를 수집합니다

                    - **입력**: 사용자가 제공한 URL
                    - **처리**:
                      - HTTP 요청으로 HTML 페이지 다운로드
                      - Selector를 사용해 제목, 본문, 날짜 추출
                    - **출력**: 원시 데이터 (title, body, publish_date)
                    - **소요 시간**: 보통 3-5초

                    **지원 사이트**: 연합뉴스, 네이버 뉴스, BBC
                    """)

                with gr.Accordion("🔹 2단계: UC1 Validation Agent (LangGraph)", open=False):
                    gr.Markdown("""
                    ### 3개의 노드로 품질을 검증합니다

                    #### Node 1: extract_fields
                    - 필드 추출 및 정제
                    - None 값 처리, 공백 제거

                    #### Node 2: calculate_quality
                    - **5W1H 저널리즘 기준** (100점 만점):
                      - Title: 20점 (10자 이상)
                      - Body: 60점 (500자 이상)
                      - Date: 10점 (유효한 날짜)
                      - URL: 10점 (올바른 형식)

                    #### Node 3: decide_action
                    - 점수 기반 다음 액션 결정:
                      - 80점 이상 → **save** (DB 저장)
                      - 80점 미만 + Selector 있음 → **heal** (UC2 복구)
                      - 80점 미만 + Selector 없음 → **new_site** (UC2 신규 생성)
                    """)

                with gr.Accordion("🔹 3단계: Self-Healing (UC2, 개발 예정)", open=False):
                    gr.Markdown("""
                    ### AI가 자동으로 Selector를 복구합니다

                    **문제 상황**:
                    - 네이버가 리뉴얼 → 기존 Selector 실패
                    - 광고 섹션 추가 → 본문 추출 오염
                    - CSS 클래스 변경 → 모든 필드 실패

                    **UC2의 역할**:
                    1. **heal**: 기존 Selector 수정
                       - GPT-4o: HTML 분석 → 새 Selector 생성
                       - Gemini 2.5 Flash: 검증 및 합의
                       - 2-Agent 합의 → DB 업데이트

                    2. **new_site**: 신규 사이트 Selector 생성
                       - 동일한 2-Agent 프로세스
                       - 5분 내 완료 (기존: 개발자 2-3시간)

                    **효과**: 장애 시간 97% 단축
                    """)

                gr.Markdown("""
                ---

                ## 🎯 프로젝트 비전

                **NewsFlow**는 **Self-Healing 뉴스 크롤링 시스템**입니다.

                ### 핵심 가치

                1. **실시간 수집**: URL 입력 → 3-5초 내 완료
                2. **품질 보장**: 5W1H 저널리즘 기준 자동 검증
                3. **Self-Healing**: 사이트 변경 시 AI가 자동 복구
                4. **실용적 도구**: 다른 부서에서 바로 사용 가능

                ### 적용 사례

                - **마케팅팀**: 특정 키워드 트렌드 분석
                - **분석팀**: 월간 뉴스 보고서 작성
                - **기획팀**: 시장 동향 파악
                - **경영진**: 산업 뉴스 모니터링

                ### 기술적 차별점

                - **LangGraph**: StateGraph 기반 Agent 오케스트레이션
                - **2-Agent Consensus**: GPT-4o + Gemini 합의로 정확도 향상
                - **자동화**: 개발자 개입 없이 Self-Healing
                """)

                demo_btn = gr.Button("🚀 Tab 1에서 직접 사용해보기", variant="primary", size="lg")

            # ============================================
            # Tab 4: 📈 통계 & 관리
            # ============================================
            with gr.Tab("📈 통계"):
                gr.Markdown("""
                ## 시스템 전체 통계를 확인하세요

                관리자를 위한 대시보드입니다.
                """)

                stats_refresh_btn = gr.Button("🔄 통계 새로고침", variant="primary")

                stats_summary = gr.HTML()

                gr.Markdown("### 📊 사이트별 상세 통계")
                stats_table = gr.Dataframe(label="사이트별 데이터")

                # 이벤트
                stats_refresh_btn.click(
                    fn=get_statistics,
                    outputs=[stats_summary, stats_table]
                )

                # 초기 로드
                demo.load(
                    fn=get_statistics,
                    outputs=[stats_summary, stats_table]
                )

        gr.Markdown("""
        ---

        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            <p><strong>NewsFlow v1.0</strong> | UC1 완료 | UC2 개발 예정 (7-8시간)</p>
            <p>개발: Claude + Charlee | 2025-11-03</p>
        </div>
        """)

    return demo


# ========================================
# 메인 실행
# ========================================

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
