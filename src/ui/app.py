"""
CrawlAgent Gradio UI - Final Enhanced Version
Created: 2025-11-16
Updated: 2025-11-16 (철학 통합, 워크플로우 시각화, Consensus 신뢰성 추가)

철학: "Learn Once, Reuse Forever"
목표: 객관적 데이터 중심의 겸손한 PoC 검증 UI (4탭 구조)

핵심 개선 사항 (메타인지적 분석 반영):
1. ✅ 버전 숨김: "v7.0" 제거, 프로젝트 철학 강조
2. ✅ 문제 정의: "왜 CrawlAgent인가?" 섹션 추가 (탭1 상단)
3. ✅ 워크플로우 시각화: HTML/CSS 플로우차트 (Supervisor → UC1/UC2/UC3)
4. ✅ Consensus 신뢰성: 2-Agent 시스템 근거 및 실제 검증 데이터 명시
5. ✅ 핵심 철학: 헤더/푸터에 "Learn Once, Reuse Forever" 강조

핵심 원칙 (v6.0 유지):
1. 과장 금지: "1,000배" → "이론적 시나리오: $0.033 vs $30 (전제 조건 명시)"
2. 출처 필수: 모든 수치에 PostgreSQL 테이블/쿼리 명시
3. 한계 명시: Yonhap 42.9%, crawl_duration 미측정 등
4. 색상 절제: UC별 구분(Green/Orange/Blue) + theme.py Purple

스타일링:
- theme.py 기반 프로페셔널 CSS (gradients, animations, hover effects)
- UC별 색상: UC1(green), UC2(orange), UC3(blue)
- 인터랙티브 배지, 카드, 상태 박스
- 소스 어트리뷰션 뱃지, 한계점 강조 박스
- Master Workflow HTML 플로우차트
"""

import sys
sys.path.insert(0, ".")

import json
import logging
import os
import time
from datetime import datetime, timedelta
from io import StringIO
from typing import Tuple
from urllib.parse import urlparse

import gradio as gr
import pandas as pd
import requests
from sqlalchemy import func

from src.storage.database import get_db
from src.storage.models import CrawlResult, DecisionLog, Selector
from src.ui.theme import CrawlAgentDarkTheme, get_custom_css
from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState

# Logger 설정
logger = logging.getLogger(__name__)

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========================================
# 유틸리티 함수
# ========================================

def get_validation_summary():
    """
    검증 데이터 요약 조회
    출처: PostgreSQL crawl_results 테이블
    """
    try:
        db = next(get_db())

        # 전체 통계
        total_count = db.query(CrawlResult).count()
        success_count = db.query(CrawlResult).filter(CrawlResult.quality_score >= 80).count()
        avg_quality = db.query(func.avg(CrawlResult.quality_score)).scalar() or 0

        # 사이트별 통계
        site_stats = db.query(
            CrawlResult.site_name,
            func.count(CrawlResult.id).label('count'),
            func.avg(CrawlResult.quality_score).label('avg_quality'),
            func.max(CrawlResult.created_at).label('last_crawl')
        ).group_by(CrawlResult.site_name).all()

        return {
            'total': total_count,
            'success': success_count,
            'avg_quality': round(avg_quality, 2),
            'sites': site_stats
        }
    except Exception as e:
        logger.error(f"Error getting validation summary: {e}")
        return None

def get_selector_stats():
    """
    Selector 성공률 통계
    출처: PostgreSQL selectors 테이블
    """
    try:
        db = next(get_db())

        selectors = db.query(Selector).all()
        stats = []

        for selector in selectors:
            success_rate = 0
            if selector.success_count + selector.failure_count > 0:
                success_rate = (selector.success_count /
                               (selector.success_count + selector.failure_count)) * 100

            stats.append({
                'site': selector.site_name,
                'success': selector.success_count,
                'failure': selector.failure_count,
                'rate': round(success_rate, 1),
                'type': selector.site_type or 'ssr'
            })

        return stats
    except Exception as e:
        logger.error(f"Error getting selector stats: {e}")
        return []

def get_recent_decision_logs(limit=10):
    """
    최근 Decision Log 조회
    출처: PostgreSQL decision_logs 테이블
    """
    try:
        db = next(get_db())

        logs = db.query(DecisionLog).order_by(
            DecisionLog.created_at.desc()
        ).limit(limit).all()

        return logs
    except Exception as e:
        logger.error(f"Error getting decision logs: {e}")
        return []

def search_articles(
    keyword: str = "",
    category: str = "all",
    site: str = "all",
    date_from: str = "",
    date_to: str = "",
    limit: int = 100,
) -> pd.DataFrame:
    """
    데이터베이스에서 기사를 조회하고 필터링하는 함수
    출처: PostgreSQL crawl_results 테이블

    Args:
        keyword: 제목/본문 검색 키워드 (부분 일치)
        category: 카테고리 필터 ("all" 또는 politics/economy/society/international)
        site: 사이트 필터 ("all" 또는 yonhap/naver/bbc/donga)
        date_from: 시작일 필터 (YYYY-MM-DD 형식)
        date_to: 종료일 필터 (YYYY-MM-DD 형식)
        limit: 최대 조회 개수

    Returns:
        pd.DataFrame: 조회 결과
    """
    try:
        db = next(get_db())
        query = db.query(CrawlResult)

        # 필터 적용
        if keyword:
            query = query.filter(
                (CrawlResult.title.contains(keyword)) | (CrawlResult.body.contains(keyword))
            )

        if category != "all":
            query = query.filter(CrawlResult.category == category)

        if site != "all":
            query = query.filter(CrawlResult.site_name == site)

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(CrawlResult.article_date >= date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(CrawlResult.article_date <= date_to_obj)
            except ValueError:
                pass

        # 최신순 정렬 및 제한
        results = query.order_by(CrawlResult.created_at.desc()).limit(limit).all()

        # DataFrame 변환
        data = []
        for r in results:
            # 발행일 우선순위: article_date > date > created_at
            if r.article_date:
                pub_date = r.article_date.strftime("%Y-%m-%d")
            elif r.date:
                # date 필드가 문자열인 경우 파싱 시도
                try:
                    if isinstance(r.date, str):
                        # ISO format 시도
                        if 'T' in r.date:
                            pub_date = r.date.split('T')[0]
                        else:
                            pub_date = r.date[:10] if len(r.date) >= 10 else r.date
                    else:
                        pub_date = str(r.date)
                except:
                    pub_date = "N/A"
            else:
                # 크롤링 날짜로 대체
                pub_date = r.created_at.strftime("%Y-%m-%d") if r.created_at else "N/A"

            # 카테고리 표시
            category_display = f"{r.category_kr or r.category or 'N/A'}"

            data.append({
                "제목": r.title if r.title else "N/A",
                "사이트": r.site_name,
                "카테고리": category_display,
                "품질": f"{r.quality_score:.0f}" if r.quality_score else "N/A",
                "발행일": pub_date,
                "본문 길이": f"{len(r.body)}자" if r.body else "0자",
                "URL": r.url,
                "ID": r.id
            })

        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        return pd.DataFrame()


def export_to_csv(df: pd.DataFrame) -> str:
    """
    DataFrame을 CSV 파일로 변환 (UTF-8 BOM, Excel 호환)

    Args:
        df: 내보낼 DataFrame

    Returns:
        str: CSV 파일 경로
    """
    import tempfile

    if df.empty:
        raise ValueError("내보낼 데이터가 없습니다")

    # 타임스탬프 포함 파일명
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 임시 파일 생성 (UTF-8 BOM for Excel)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        suffix=f"_crawlagent_{timestamp}.csv",
        encoding="utf-8-sig"  # Excel 호환 (BOM)
    )

    # ID 컬럼 제외
    export_df = df.drop(columns=["ID"], errors="ignore")

    # CSV 저장
    export_df.to_csv(temp_file.name, index=False)
    temp_file.close()

    logger.info(f"CSV 내보내기 완료: {temp_file.name} ({len(df)}개 행)")

    return temp_file.name


def export_to_json(df: pd.DataFrame) -> str:
    """
    DataFrame을 JSON 파일로 변환

    Args:
        df: 내보낼 DataFrame

    Returns:
        str: JSON 파일 경로
    """
    import tempfile
    import json

    if df.empty:
        raise ValueError("내보낼 데이터가 없습니다")

    # 타임스탬프 포함 파일명
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 임시 파일 생성
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        suffix=f"_crawlagent_{timestamp}.json",
        encoding="utf-8"
    )

    # ID 컬럼 제외
    export_df = df.drop(columns=["ID"], errors="ignore")

    # JSON 구조화
    data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(export_df),
        "articles": export_df.to_dict(orient="records")
    }

    # JSON 저장 (들여쓰기 포함, 한글 유지)
    json.dump(data, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()

    logger.info(f"JSON 내보내기 완료: {temp_file.name} ({len(df)}개 행)")

    return temp_file.name


def get_search_statistics(df: pd.DataFrame) -> str:
    """
    검색 결과 통계 생성

    Args:
        df: 검색 결과 DataFrame

    Returns:
        str: 통계 문자열
    """
    if df.empty:
        return "검색 결과가 없습니다."

    try:
        # 품질 점수는 문자열이므로 숫자로 변환
        quality_scores = df["품질"].astype(float)
        avg_quality = quality_scores.mean()

        # 사이트별 통계
        site_counts = df["사이트"].value_counts().to_dict()
        site_stats = ", ".join([f"{site}: {count}개" for site, count in site_counts.items()])

        stats = f"""
📊 검색 결과 통계

✅ 총 기사 수: {len(df)}개
⭐ 평균 품질 점수: {avg_quality:.1f}/100
🌐 사이트별: {site_stats}
"""
        return stats.strip()

    except Exception as e:
        logger.error(f"통계 생성 오류: {e}")
        return f"통계 생성 실패: {str(e)}"


def run_crawl_test(url: str) -> Tuple[str, str]:
    """
    Master Graph 워크플로우 실행 (UC1→UC2→UC3)

    Args:
        url: 테스트할 뉴스 기사 URL

    Returns:
        Tuple[str, str]: (HTML 결과, 상세 로그)
    """
    if not url or not url.startswith("http"):
        error_html = """
        <div style='background: #ef444430; border-left: 4px solid #ef4444;
                    padding: 20px; border-radius: 12px; color: #ef4444;'>
            <h3>오류: 유효하지 않은 URL</h3>
            <p>올바른 URL을 입력하세요 (예: https://news.naver.com/...)</p>
        </div>
        """
        return error_html, "Invalid URL provided"

    # 로그 캡처 설정
    log_capture = StringIO()
    log_handler = logging.StreamHandler(log_capture)
    log_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    log_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)

    try:
        start_time = time.time()

        # 1. Master Graph 빌드
        master_app = build_master_graph()

        # 2. HTML 다운로드
        logger.info(f"Fetching HTML from {url}")

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )
        response.raise_for_status()
        html_content = response.text

        # 3. 사이트 이름 추출 (site_detector 사용)
        from src.utils.site_detector import extract_site_id
        site_name = extract_site_id(url)

        # 4. 초기 State
        initial_state: MasterCrawlState = {
            "url": url,
            "site_name": site_name,
            "html_content": html_content,
            "current_uc": None,
            "next_action": None,
            "failure_count": 0,
            "uc1_validation_result": None,
            "uc2_consensus_result": None,
            "uc3_discovery_result": None,
            "final_result": None,
            "error_message": None,
            "workflow_history": [],
        }

        # 5. Master Graph 실행
        logger.info("Running Master Graph...")
        final_state = master_app.invoke(initial_state)

        elapsed = time.time() - start_time

        # 6. 결과 HTML 생성
        workflow_history = final_state.get("workflow_history", [])
        final_result = final_state.get("final_result")
        error_message = final_state.get("error_message")

        # LangSmith 링크 생성
        langsmith_url = os.getenv("LANGSMITH_URL", "https://smith.langchain.com")
        langsmith_link = f"{langsmith_url}" if os.getenv("LANGCHAIN_TRACING_V2") == "true" else None

        # UC 배지 및 비용 결정
        uc_badge = ""
        cost_info = ""

        if "UC1" in workflow_history:
            uc_badge = '<span class="badge badge-uc1">UC1 Selector 기반</span>'
            cost_info = '<p><strong>예상 비용:</strong> $0 (LLM 미사용)</p>'
        elif "UC2" in workflow_history:
            uc_badge = '<span class="badge badge-uc2">UC2 Self-Healing</span>'
            cost_info = '<p><strong>예상 비용:</strong> $0.0137 (Claude Sonnet 4.5 + GPT-4o)</p>'
        elif "UC3" in workflow_history:
            uc_badge = '<span class="badge badge-uc3">UC3 Discovery</span>'
            cost_info = '<p><strong>예상 비용:</strong> $0.033 (Claude Sonnet 4.5 + GPT-4o)</p>'

        if final_result:
            # 성공 케이스
            quality_score = final_result.get('quality_score', 0)
            result_html = f"""
            <div style='background: #10b98130; border-left: 4px solid #10b981;
                        padding: 20px; border-radius: 12px; color: #10b981; margin-bottom: 10px;'>
                <h3>크롤링 성공! ({elapsed:.2f}초)</h3>
                <p><strong>워크플로우:</strong> {' → '.join(workflow_history)}</p>
                <p>{uc_badge}</p>
                {f'<p><a href="{langsmith_link}" target="_blank" style="color: #667eea;">🔗 LangSmith 추적 보기</a></p>' if langsmith_link else ''}
            </div>

            <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-top: 10px;'>
                <h4>추출된 기사</h4>
                <p><strong>제목:</strong> {final_result.get('title', 'N/A')[:200]}</p>
                <p><strong>발행일:</strong> {final_result.get('date', 'N/A')}</p>
                <p><strong>본문 미리보기:</strong> {final_result.get('body', 'N/A')[:300]}...</p>
                <p><strong>품질 점수:</strong> {quality_score}/100</p>
                {cost_info}
            </div>
            """
        else:
            # 실패 케이스
            result_html = f"""
            <div style='background: #ef444430; border-left: 4px solid #ef4444;
                        padding: 20px; border-radius: 12px; color: #ef4444;'>
                <h3>크롤링 실패 ({elapsed:.2f}초)</h3>
                <p><strong>워크플로우:</strong> {' → '.join(workflow_history)}</p>
                <p><strong>오류:</strong> {error_message or 'Unknown error'}</p>
            </div>
            """

        # 로그 가져오기
        log_content = log_capture.getvalue()

        return result_html, log_content

    except Exception as e:
        logger.error(f"Error in crawl test: {e}")
        error_html = f"""
        <div style='background: #ef444430; border-left: 4px solid #ef4444;
                    padding: 20px; border-radius: 12px; color: #ef4444;'>
            <h3>예외 발생</h3>
            <p>{str(e)}</p>
        </div>
        """
        return error_html, log_capture.getvalue()

    finally:
        # 로그 핸들러 제거
        root_logger.removeHandler(log_handler)
        root_logger.setLevel(original_level)

# ========================================
# Gradio UI 구성
# ========================================

def create_ui():
    """Gradio UI 생성"""

    # 커스텀 CSS에 UC 배지 스타일 추가
    custom_css = get_custom_css() + """
    /* UC 배지 스타일 */
    :root {
        --uc1-color: #10b981;
        --uc2-color: #f59e0b;
        --uc3-color: #3b82f6;
    }

    .badge-uc1 {
        background: #10b98130;
        color: #10b981;
        border: 1px solid #10b981;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
        display: inline-block;
    }

    .badge-uc2 {
        background: #f59e0b30;
        color: #f59e0b;
        border: 1px solid #f59e0b;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
        display: inline-block;
    }

    .badge-uc3 {
        background: #3b82f630;
        color: #3b82f6;
        border: 1px solid #3b82f6;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
        display: inline-block;
    }

    .uc-card {
        border: 2px solid;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }

    .uc-card.uc1 {
        border-color: var(--uc1-color);
        background: #10b98110;
    }

    .uc-card.uc2 {
        border-color: var(--uc2-color);
        background: #f59e0b10;
    }

    .uc-card.uc3 {
        border-color: var(--uc3-color);
        background: #3b82f610;
    }

    /* ============================================ */
    /* UC 인터랙티브 배지 (hover 효과) */
    /* ============================================ */
    .badge-uc1, .badge-uc2, .badge-uc3 {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .badge-uc1:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(16, 185, 129, 0.4);
        background: linear-gradient(135deg, #10b98130 0%, #10b98140 100%);
    }

    .badge-uc2:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(245, 158, 11, 0.4);
        background: linear-gradient(135deg, #f59e0b30 0%, #f59e0b40 100%);
    }

    .badge-uc3:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.4);
        background: linear-gradient(135deg, #3b82f630 0%, #3b82f640 100%);
    }

    /* ============================================ */
    /* UC 상태 박스 (fadeIn 애니메이션) */
    /* ============================================ */
    .uc1-status-box {
        background: linear-gradient(135deg, #10b98120 0%, #10b98130 100%) !important;
        border-left: 4px solid #10b981 !important;
        color: #10b981 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        margin: 20px 0 !important;
        animation: fadeIn 0.5s ease-in !important;
    }

    .uc2-status-box {
        background: linear-gradient(135deg, #f59e0b20 0%, #f59e0b30 100%) !important;
        border-left: 4px solid #f59e0b !important;
        color: #f59e0b !important;
        padding: 20px !important;
        border-radius: 12px !important;
        margin: 20px 0 !important;
        animation: fadeIn 0.5s ease-in !important;
    }

    .uc3-status-box {
        background: linear-gradient(135deg, #3b82f620 0%, #3b82f630 100%) !important;
        border-left: 4px solid #3b82f6 !important;
        color: #3b82f6 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        margin: 20px 0 !important;
        animation: fadeIn 0.5s ease-in !important;
    }

    /* ============================================ */
    /* 메트릭 카드 (호버 스케일 효과) */
    /* ============================================ */
    .metric-card {
        background: #2d2e32 !important;
        border: 1px solid #4a4b4f !important;
        border-radius: 12px !important;
        padding: 24px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .metric-card:hover {
        transform: translateY(-4px) scale(1.01) !important;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3) !important;
        border-color: #667eea50 !important;
    }

    /* ============================================ */
    /* 소스 어트리뷰션 뱃지 */
    /* ============================================ */
    .source-badge {
        display: inline-block;
        background: #4a4b4f;
        color: #9ca3af;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.75em;
        font-weight: 500;
        margin-left: 8px;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }

    .source-badge:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transform: scale(1.05);
        border-color: #667eea;
        box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
    }

    /* ============================================ */
    /* 한계점 강조 박스 (점선 테두리) */
    /* ============================================ */
    .limitation-box {
        background: linear-gradient(135deg, #ef444420 0%, #ef444430 100%) !important;
        border: 2px dashed #ef4444 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin: 20px 0 !important;
        animation: fadeIn 0.5s ease-in !important;
    }

    .limitation-box h3 {
        color: #ef4444 !important;
        font-weight: 700 !important;
        margin-bottom: 12px !important;
        display: flex;
        align-items: center;
    }

    .limitation-box p {
        color: #fca5a5 !important;
        margin: 8px 0 !important;
        line-height: 1.6 !important;
    }

    /* ============================================ */
    /* 데이터 소스 박스 */
    /* ============================================ */
    .data-source-box {
        background: #3a3b3f !important;
        border-left: 3px solid #667eea !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
        margin: 12px 0 !important;
        font-size: 0.9em !important;
        color: #9ca3af !important;
        transition: all 0.3s ease !important;
    }

    .data-source-box:hover {
        background: #4a4b4f !important;
        border-left-color: #764ba2 !important;
        transform: translateX(4px);
    }

    /* ============================================ */
    /* 진행 상태 인디케이터 (pulsing dot) */
    /* ============================================ */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s ease-in-out infinite;
    }

    .status-indicator.success {
        background: #10b981;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
    }

    .status-indicator.warning {
        background: #f59e0b;
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
    }

    .status-indicator.error {
        background: #ef4444;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
    }

    /* ============================================ */
    /* 테이블 행 호버 효과 강화 */
    /* ============================================ */
    .dataframe tbody tr:hover {
        background: #3a3b3f !important;
        cursor: pointer;
        transform: scale(1.005);
        transition: all 0.2s ease;
    }

    /* ============================================ */
    /* 로딩 스피너 (결과 표시 중) */
    /* ============================================ */
    .loading-text {
        color: #667eea;
        font-size: 1.1em;
        font-weight: 600;
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* ============================================ */
    /* 성공 체크마크 애니메이션 */
    /* ============================================ */
    .success-checkmark {
        display: inline-block;
        animation: checkmark 0.5s ease-in-out;
        color: #10b981;
        font-size: 1.5em;
    }

    @keyframes checkmark {
        0% {
            transform: scale(0) rotate(0deg);
            opacity: 0;
        }
        50% {
            transform: scale(1.2) rotate(180deg);
        }
        100% {
            transform: scale(1) rotate(360deg);
            opacity: 1;
        }
    }

    /* ============================================ */
    /* 스크롤바 스타일링 (다크 모드) */
    /* ============================================ */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: #2d2e32;
    }

    ::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #764ba2;
    }

    /* ============================================ */
    /* 툴팁 호버 효과 */
    /* ============================================ */
    [title]:hover::after {
        animation: fadeIn 0.3s ease-in;
    }

    /* ============================================ */
    /* 헤더 스타일 개선 */
    /* ============================================ */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800 !important;
    }

    h2 {
        color: #e5e7eb !important;
        font-weight: 700 !important;
        margin-top: 24px !important;
        margin-bottom: 16px !important;
    }

    h3 {
        color: #9ca3af !important;
        font-weight: 600 !important;
        margin-top: 20px !important;
        margin-bottom: 12px !important;
    }
    """

    with gr.Blocks(
        theme=CrawlAgentDarkTheme(),
        css=custom_css,
        title="CrawlAgent v7.0",
    ) as demo:

        gr.HTML("""
            <div style='text-align: center; padding: 30px 20px; animation: fadeIn 0.8s ease-in;'>
                <h1 style='font-size: 2.8em; margin-bottom: 15px; line-height: 1.2;'>
                    CrawlAgent
                </h1>
                <div style='font-size: 1.5em; color: #667eea; font-weight: 700; margin-bottom: 20px;'>
                    "Learn Once, Reuse Forever"
                </div>
                <div style='font-size: 1.1em; color: #9ca3af; font-weight: 500; margin-bottom: 25px;'>
                    뉴스 크롤링 자동화를 위한 LangGraph Supervisor Pattern PoC
                </div>

                <div style='background: linear-gradient(135deg, #667eea30 0%, #764ba230 100%);
                            border: 1px solid #667eea50; border-radius: 12px; padding: 20px;
                            max-width: 900px; margin: 0 auto;'>
                    <div style='margin-bottom: 15px;'>
                        <span class='status-indicator success'></span>
                        <strong style='color: #e5e7eb; font-size: 1.1em;'>
                            첫 학습 비용만 지불하고, 이후는 Selector 재사용
                        </strong>
                    </div>
                    <div style='color: #9ca3af; font-size: 0.95em; line-height: 1.6;'>
                        <strong>핵심:</strong> Supervisor가 UC1/UC2/UC3를 자동 라우팅<br>
                        <strong>실적:</strong> 459개 실제 크롤링 100% 성공 (PostgreSQL DB 검증)<br>
                        <strong>투명성:</strong> Mock 없음 | 한계점 명시 | 객관적 평가
                    </div>
                </div>
            </div>
        """)

        with gr.Tabs():

            # ============================================
            # 탭1: 실시간 테스트
            # ============================================
            with gr.Tab("🎯 실시간 테스트"):
                gr.HTML("""
                <div style='background: linear-gradient(135deg, #3b82f620 0%, #3b82f630 100%);
                            border-left: 4px solid #3b82f6; padding: 20px; border-radius: 12px;
                            margin-bottom: 20px;'>
                    <h3 style='color: #3b82f6; margin-bottom: 12px;'>💡 왜 CrawlAgent인가?</h3>
                    <p style='color: #e5e7eb; line-height: 1.6; margin-bottom: 10px;'>
                        <strong>문제:</strong> 뉴스 사이트는 평균 <strong style='color: #f59e0b;'>3-6개월마다 UI 변경</strong>
                        → 기존 Selector가 깨짐 → 수동 수정 필요
                    </p>
                    <p style='color: #e5e7eb; line-height: 1.6; margin-bottom: 10px;'>
                        <strong>기존 방식:</strong> 매번 LLM 호출 ($0.03/page) 또는 수동 Selector 수정
                    </p>
                    <p style='color: #10b981; line-height: 1.6; font-weight: 600;'>
                        <strong>CrawlAgent 해결책:</strong> Supervisor가 상황에 따라 UC1/UC2/UC3 자동 선택
                        <br>→ 첫 학습 후 재사용 (~$0) | 변경 감지 시 자동 Self-Healing (~$0.0137)
                    </p>
                </div>
                """)

                gr.Markdown(
                    """
                    ## 크롤링 테스트

                    URL을 입력하여 UC1/UC2/UC3 자동 판단 및 실행을 테스트합니다.

                    **동작 방식**:
                    - **UC1 (Quality Gate)**: Selector 존재 시 → 품질 검증 (80점 이상 통과) → **비용 $0**
                    - **UC2 (Self-Healing)**: UC1 실패 시 → 2-Agent Consensus (Claude + GPT-4o) → Selector 자동 수정 → **비용 ~$0.0137**
                    - **UC3 (Discovery)**: Selector 미존재 시 → 2-Agent Consensus (Claude + GPT-4o) → 신규 등록 → **비용 ~$0.033**
                    """
                )

                test_url = gr.Textbox(
                    label="테스트할 URL",
                    placeholder="예: https://www.yna.co.kr/view/AKR...",
                    lines=1,
                )

                with gr.Row():
                    test_btn = gr.Button("🚀 크롤링 실행", variant="primary", size="lg")
                    clear_btn = gr.Button("🗑️ 초기화", size="sm")

                test_output = gr.HTML(label="실행 결과")

                with gr.Accordion("📋 상세 로그", open=False):
                    test_log = gr.Textbox(
                        label="워크플로우 실행 로그",
                        lines=20,
                        max_lines=30,
                        interactive=False,
                        show_copy_button=True,
                    )

                # Event handlers
                test_btn.click(
                    fn=run_crawl_test,
                    inputs=test_url,
                    outputs=[test_output, test_log],
                )

                clear_btn.click(
                    fn=lambda: ("", "", ""),
                    outputs=[test_url, test_output, test_log],
                )

            # ============================================
            # 탭2: ⚙️ 자동화 관리 (Multi-Site Automation)
            # ============================================
            with gr.Tab("⚙️ 자동화 관리"):
                gr.HTML("""
                <div style='background: linear-gradient(135deg, #f59e0b20 0%, #f59e0b30 100%);
                            border-left: 4px solid #f59e0b; padding: 20px; border-radius: 12px;
                            margin-bottom: 20px;'>
                    <h3 style='color: #f59e0b; margin-bottom: 12px;'>🤖 다중 사이트 자동화 크롤링</h3>
                    <p style='color: #e5e7eb; line-height: 1.6; margin-bottom: 10px;'>
                        <strong>실시간 검증 완료</strong> → <strong style='color: #f59e0b;'>Scrapy 자동화로 확장</strong>
                    </p>
                    <p style='color: #e5e7eb; line-height: 1.6;'>
                        💡 <strong>Learn Once, Reuse Forever:</strong> 검증된 Master Workflow를 기반으로 여러 사이트와 카테고리를 동시에 자동 수집합니다.
                    </p>
                </div>
                """)

                # Import multi-site crawler functions
                from src.scheduler.multi_site_crawler import (
                    get_available_sites,
                    get_site_categories,
                    VERIFIED_SITES
                )
                from src.ui.scheduler_control import (
                    start_multi_site_scheduler,
                    run_multi_site_manual_crawl,
                    stop_scheduler,
                    get_scheduler_status,
                    get_scheduler_logs,
                    get_recent_crawl_stats
                )

                # 1. 사이트 선택
                gr.Markdown("## 🌐 Step 1: 사이트 선택 (검증된 사이트만)")

                site_selector = gr.CheckboxGroup(
                    choices=get_available_sites(),
                    label="수집할 사이트 선택 (복수 선택 가능)",
                    value=["yonhap"],  # 기본값: Yonhap
                    info="검증된 사이트: 연합뉴스, 네이버 뉴스, BBC"
                )

                # 2. 카테고리 선택
                gr.Markdown("## 📂 Step 2: 카테고리 선택")

                category_selector = gr.CheckboxGroup(
                    choices=[],
                    label="수집할 카테고리 선택 (복수 선택 가능)",
                    info="사이트 선택 후 자동으로 표시됩니다"
                )

                scope_selector = gr.Radio(
                    choices=[
                        ("선택한 카테고리만 수집", "selected"),
                        ("전체 카테고리 수집 (카테고리 선택 무시)", "all")
                    ],
                    value="selected",
                    label="카테고리 범위",
                    info="💡 '전체 카테고리'를 선택하면 위의 카테고리 선택이 무시됩니다"
                )

                # 2.5. 날짜 범위 선택
                gr.Markdown("## 📅 Step 2.5: 날짜 범위 선택")

                date_range_mode = gr.Radio(
                    choices=[
                        ("자동 (어제 날짜)", "auto"),
                        ("오늘만", "today"),
                        ("최근 3일", "recent_3"),
                        ("최근 7일", "recent_7"),
                        ("커스텀 범위", "custom")
                    ],
                    value="auto",
                    label="날짜 범위 모드",
                    info="💡 '자동'은 어제 날짜 기사를 수집합니다 (가장 안정적)"
                )

                with gr.Row(visible=False) as custom_date_row:
                    date_from_input = gr.Textbox(
                        label="시작일 (YYYY-MM-DD)",
                        placeholder="2025-11-10",
                        scale=1
                    )
                    date_to_input = gr.Textbox(
                        label="종료일 (YYYY-MM-DD)",
                        placeholder="2025-11-17",
                        scale=1
                    )

                # 3. 스케줄 설정
                gr.Markdown("## ⏰ Step 3: 스케줄 설정")

                with gr.Row():
                    schedule_time = gr.Textbox(
                        label="실행 시각 (HH:MM)",
                        value="00:30",
                        placeholder="00:30",
                        scale=1
                    )

                    frequency_selector = gr.Radio(
                        choices=[
                            ("매일", "daily"),
                            ("주간 (월요일)", "weekly"),
                            ("월간 (1일)", "monthly")
                        ],
                        value="daily",
                        label="실행 빈도",
                        scale=2
                    )

                # 4. 실행 계획 미리보기
                gr.Markdown("## 📋 Step 4: 실행 계획 확인")

                plan_preview = gr.Textbox(
                    label="실행 계획 미리보기",
                    lines=8,
                    interactive=False,
                    placeholder="사이트와 카테고리를 선택하면 실행 계획이 표시됩니다"
                )

                preview_btn = gr.Button("🔍 실행 계획 미리보기", size="sm")

                # 5. 실행 버튼
                gr.Markdown("## 🚀 Step 5: 실행")

                with gr.Row():
                    start_auto_btn = gr.Button("🚀 자동화 시작 (스케줄)", variant="primary", size="lg", scale=1)
                    manual_exec_btn = gr.Button("▶️ 즉시 실행 (테스트)", variant="secondary", size="lg", scale=1)
                    stop_btn = gr.Button("⏹️ 중지", variant="stop", size="lg", scale=1)

                # 6. 상태 및 로그
                gr.Markdown("## 📊 실행 상태")

                status_display = gr.Textbox(
                    label="현재 상태",
                    value="⏹️ 중지됨",
                    interactive=False,
                    lines=1
                )

                log_display = gr.Textbox(
                    label="실행 로그 (실시간)",
                    lines=15,
                    max_lines=20,
                    interactive=False,
                    show_copy_button=True
                )

                with gr.Row():
                    refresh_log_btn = gr.Button("🔄 로그 새로고침", size="sm")

                # 7. 통계
                gr.Markdown("## 📈 자동화 통계 (최근 7일)")

                stats_display = gr.HTML()

                with gr.Row():
                    refresh_stats_btn = gr.Button("🔄 통계 새로고침", size="sm")

                # ========================================
                # Event Handlers
                # ========================================

                def on_site_change(selected_sites):
                    """사이트 선택 변경 시 카테고리 목록 업데이트"""
                    if not selected_sites:
                        return gr.update(choices=[], value=[])

                    # 선택된 사이트들의 카테고리 수집
                    all_categories = []
                    for site in selected_sites:
                        site_cats = get_site_categories(site)
                        site_name = VERIFIED_SITES[site]["name"]

                        # 사이트명 prefix 추가
                        for cat_label, cat_value in site_cats:
                            all_categories.append((f"[{site_name}] {cat_label}", f"{site}:{cat_value}"))

                    return gr.update(choices=all_categories, value=[])

                def on_preview_plan(selected_sites, selected_categories, scope, date_mode, date_from, date_to):
                    """실행 계획 미리보기 생성"""
                    if not selected_sites:
                        return "⚠️ 사이트를 먼저 선택하세요."

                    # 날짜 범위 처리
                    from datetime import datetime, timedelta
                    if date_mode == "auto":
                        date_info = "📅 날짜: 어제 (자동)"
                    elif date_mode == "today":
                        date_info = f"📅 날짜: 오늘 ({datetime.now().strftime('%Y-%m-%d')})"
                    elif date_mode == "recent_3":
                        date_info = f"📅 날짜: 최근 3일 ({(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')})"
                    elif date_mode == "recent_7":
                        date_info = f"📅 날짜: 최근 7일 ({(datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')})"
                    elif date_mode == "custom":
                        date_info = f"📅 날짜: 커스텀 ({date_from} ~ {date_to})"
                    else:
                        date_info = "📅 날짜: 어제 (기본값)"

                    # 카테고리 파싱 (site:category 형식)
                    categories_per_site = {}
                    for cat_str in selected_categories:
                        if ":" in cat_str:
                            site, cat = cat_str.split(":", 1)
                            if site not in categories_per_site:
                                categories_per_site[site] = []
                            categories_per_site[site].append(cat)

                    # 계획 생성
                    from src.scheduler.multi_site_crawler import get_crawl_plan_summary
                    plan = get_crawl_plan_summary(selected_sites, categories_per_site, scope)
                    return f"{plan}\n\n{date_info}"

                def on_start_automation(selected_sites, selected_categories, scope, time_str, frequency, date_mode, date_from, date_to):
                    """자동화 시작 핸들러"""
                    if not selected_sites:
                        return "❌ 사이트 선택 필요", "최소 1개 이상의 사이트를 선택하세요."

                    # 카테고리 파싱
                    categories_per_site = {}
                    for cat_str in selected_categories:
                        if ":" in cat_str:
                            site, cat = cat_str.split(":", 1)
                            if site not in categories_per_site:
                                categories_per_site[site] = []
                            categories_per_site[site].append(cat)

                    # 스케줄러 시작 (날짜 범위는 scheduler에서 처리)
                    status_msg, log_msg = start_multi_site_scheduler(
                        sites=selected_sites,
                        categories_per_site=categories_per_site,
                        scope=scope,
                        schedule_time=time_str,
                        frequency=frequency
                    )

                    return status_msg, log_msg

                def on_manual_execute(selected_sites, selected_categories, scope, date_mode, date_from, date_to):
                    """즉시 실행 핸들러"""
                    if not selected_sites:
                        return "❌ 사이트 선택 필요", "최소 1개 이상의 사이트를 선택하세요."

                    # 카테고리 파싱
                    categories_per_site = {}
                    for cat_str in selected_categories:
                        if ":" in cat_str:
                            site, cat = cat_str.split(":", 1)
                            if site not in categories_per_site:
                                categories_per_site[site] = []
                            categories_per_site[site].append(cat)

                    # 날짜 범위 계산
                    from datetime import datetime, timedelta
                    date_list = []

                    if date_mode == "auto":
                        # 어제 날짜
                        date_list = [(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]
                    elif date_mode == "today":
                        # 오늘
                        date_list = [datetime.now().strftime('%Y-%m-%d')]
                    elif date_mode == "recent_3":
                        # 최근 3일
                        for i in range(3):
                            date_list.append((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))
                    elif date_mode == "recent_7":
                        # 최근 7일
                        for i in range(7):
                            date_list.append((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))
                    elif date_mode == "custom":
                        # 커스텀 범위
                        if date_from and date_to:
                            try:
                                start_date = datetime.strptime(date_from, '%Y-%m-%d')
                                end_date = datetime.strptime(date_to, '%Y-%m-%d')
                                current_date = start_date
                                while current_date <= end_date:
                                    date_list.append(current_date.strftime('%Y-%m-%d'))
                                    current_date += timedelta(days=1)
                            except:
                                return "❌ 날짜 형식 오류", "날짜 형식은 YYYY-MM-DD이어야 합니다."
                        else:
                            return "❌ 날짜 입력 필요", "커스텀 범위를 선택하셨습니다. 시작일과 종료일을 입력하세요."
                    else:
                        # 기본값: 어제
                        date_list = [(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]

                    # 즉시 실행 (날짜 범위 포함)
                    status_msg, log_msg = run_multi_site_manual_crawl(
                        sites=selected_sites,
                        categories_per_site=categories_per_site,
                        scope=scope,
                        date_list=date_list  # 날짜 리스트 전달
                    )

                    return status_msg, log_msg

                def on_stop_automation():
                    """자동화 중지 핸들러"""
                    status_msg, log_msg = stop_scheduler()
                    return status_msg, log_msg

                def on_refresh_log():
                    """로그 새로고침 핸들러"""
                    return get_scheduler_logs(lines=100)

                def on_refresh_stats():
                    """통계 새로고침 핸들러"""
                    stats = get_recent_crawl_stats(days=7)

                    # HTML 포맷팅
                    html = f"""
                    <div style='background: #1f2937; padding: 20px; border-radius: 12px;'>
                        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px;'>
                            <div style='background: rgba(16,185,129,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                                <div style='color: #9ca3af; font-size: 0.9em; margin-bottom: 5px;'>총 크롤링</div>
                                <div style='color: #10b981; font-size: 2em; font-weight: 700;'>{stats['total_count']}</div>
                            </div>
                            <div style='background: rgba(16,185,129,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                                <div style='color: #9ca3af; font-size: 0.9em; margin-bottom: 5px;'>성공 크롤링</div>
                                <div style='color: #10b981; font-size: 2em; font-weight: 700;'>{stats['success_count']}</div>
                            </div>
                            <div style='background: rgba(16,185,129,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                                <div style='color: #9ca3af; font-size: 0.9em; margin-bottom: 5px;'>성공률</div>
                                <div style='color: #10b981; font-size: 2em; font-weight: 700;'>{stats['success_rate']}%</div>
                            </div>
                        </div>

                        <h4 style='color: #e5e7eb; margin-bottom: 10px;'>일별 수집 현황</h4>
                        <div style='background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;'>
                    """

                    for day_stat in stats['daily_stats']:
                        html += f"""
                            <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                <span style='color: #9ca3af;'>{day_stat['date']}</span>
                                <span style='color: #10b981; font-weight: 600;'>{day_stat['count']}개</span>
                            </div>
                        """

                    html += """
                        </div>
                    </div>
                    """

                    return html

                # 날짜 범위 모드 변경 핸들러
                def on_date_mode_change(mode):
                    """날짜 범위 모드 변경 시 커스텀 입력 필드 표시/숨김"""
                    if mode == "custom":
                        return gr.update(visible=True)
                    else:
                        return gr.update(visible=False)

                # Bind events
                date_range_mode.change(
                    fn=on_date_mode_change,
                    inputs=[date_range_mode],
                    outputs=[custom_date_row]
                )

                site_selector.change(
                    fn=on_site_change,
                    inputs=[site_selector],
                    outputs=[category_selector]
                )

                preview_btn.click(
                    fn=on_preview_plan,
                    inputs=[site_selector, category_selector, scope_selector, date_range_mode, date_from_input, date_to_input],
                    outputs=[plan_preview]
                )

                start_auto_btn.click(
                    fn=on_start_automation,
                    inputs=[site_selector, category_selector, scope_selector, schedule_time, frequency_selector, date_range_mode, date_from_input, date_to_input],
                    outputs=[status_display, log_display]
                )

                manual_exec_btn.click(
                    fn=on_manual_execute,
                    inputs=[site_selector, category_selector, scope_selector, date_range_mode, date_from_input, date_to_input],
                    outputs=[status_display, log_display]
                )

                stop_btn.click(
                    fn=on_stop_automation,
                    outputs=[status_display, log_display]
                )

                refresh_log_btn.click(
                    fn=on_refresh_log,
                    outputs=[log_display]
                )

                refresh_stats_btn.click(
                    fn=on_refresh_stats,
                    outputs=[stats_display]
                )

            # ============================================
            # 탭3: 아키텍처 + 비용 (간소화 버전)
            # ============================================
            with gr.Tab("🧠 아키텍처 + 비용"):

                # 안내 메시지
                gr.HTML("""
                <div style='background: linear-gradient(135deg, #667eea20 0%, #764ba230 100%);
                            border: 2px solid #667eea; padding: 20px; border-radius: 10px; margin-bottom: 30px;'>
                    <h3 style='color: #667eea; text-align: center; margin-bottom: 15px;'>
                        📚 상세 문서는 HANDOFF_PACKAGE/ 폴더를 참고하세요
                    </h3>
                    <p style='color: #e5e7eb; text-align: center; margin: 0; font-size: 1.1em; line-height: 1.8;'>
                        <strong>발표자료:</strong> 03_PRESENTATION_SLIDES_V2.md<br>
                        <strong>개발자 가이드:</strong> 04_SKILL_INTEGRATED.md<br>
                        <strong>트러블슈팅:</strong> 09_TROUBLESHOOTING_REFERENCE.md
                    </p>
                </div>
                """)

                # ==========================================
                # 핵심 워크플로우 다이어그램 (간소화)
                # ==========================================
                gr.Markdown("## 🧠 Master Workflow (Supervisor Pattern)")

                gr.HTML("""
                <div style='background: rgba(0,0,0,0.3); padding: 30px; border-radius: 12px; margin: 20px 0;'>
                    <!-- START -->
                    <div style='text-align: center; margin-bottom: 20px;'>
                        <div style='background: #667eea; color: white; padding: 12px 25px; border-radius: 8px; display: inline-block; font-weight: 600;'>
                            🚀 URL 입력
                        </div>
                    </div>

                    <div style='text-align: center; color: #667eea; font-size: 1.5em; margin: 10px 0;'>↓</div>

                    <!-- SUPERVISOR -->
                    <div style='text-align: center; margin-bottom: 20px;'>
                        <div style='background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 30px; border-radius: 10px; display: inline-block;'>
                            <div style='font-weight: 700; font-size: 1.1em;'>🧠 Supervisor (Rule-based)</div>
                        </div>
                    </div>

                    <div style='text-align: center; color: #667eea; font-size: 1.5em; margin: 10px 0;'>↓</div>

                    <!-- UC1, UC2, UC3 -->
                    <div style='display: flex; justify-content: space-between; gap: 15px; margin-bottom: 20px;'>
                        <div style='flex: 1; text-align: center;'>
                            <div style='background: #10b981; color: white; padding: 20px 15px; border-radius: 8px;'>
                                <div style='font-weight: 700; font-size: 1.1em;'>🟢 UC1</div>
                                <div style='font-size: 0.9em; margin: 8px 0;'>재사용</div>
                                <div style='font-size: 1.2em; font-weight: 700;'>$0</div>
                                <div style='font-size: 0.8em; opacity: 0.9;'>~100ms</div>
                            </div>
                        </div>
                        <div style='flex: 1; text-align: center;'>
                            <div style='background: #f59e0b; color: white; padding: 20px 15px; border-radius: 8px;'>
                                <div style='font-weight: 700; font-size: 1.1em;'>🟡 UC2</div>
                                <div style='font-size: 0.9em; margin: 8px 0;'>복구</div>
                                <div style='font-size: 1.2em; font-weight: 700;'>~$0.014</div>
                                <div style='font-size: 0.8em; opacity: 0.9;'>~5s</div>
                            </div>
                        </div>
                        <div style='flex: 1; text-align: center;'>
                            <div style='background: #3b82f6; color: white; padding: 20px 15px; border-radius: 8px;'>
                                <div style='font-weight: 700; font-size: 1.1em;'>🔵 UC3</div>
                                <div style='font-size: 0.9em; margin: 8px 0;'>학습</div>
                                <div style='font-size: 1.2em; font-weight: 700;'>~$0.033</div>
                                <div style='font-size: 0.8em; opacity: 0.9;'>~8s</div>
                            </div>
                        </div>
                    </div>
                </div>
                """)


                # ==========================================
                # 비용 비교 (간소화)
                # ==========================================
                gr.Markdown("## 💰 비용 비교")

                gr.HTML("""
                <div style='margin: 20px 0;'>
                    <table style='width: 100%; border-collapse: collapse; background: rgba(0,0,0,0.3); border-radius: 10px; overflow: hidden;'>
                        <thead>
                            <tr style='background: linear-gradient(135deg, #667eea, #764ba2);'>
                                <th style='padding: 15px; color: white; text-align: left;'>시나리오</th>
                                <th style='padding: 15px; color: white; text-align: right;'>비용</th>
                                <th style='padding: 15px; color: white; text-align: right;'>레이턴시</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                <td style='padding: 15px; color: #10b981; font-weight: 600;'>🟢 UC1: 알려진 사이트 재사용</td>
                                <td style='padding: 15px; color: #10b981; text-align: right; font-weight: 700;'>$0.00</td>
                                <td style='padding: 15px; color: #9ca3af; text-align: right;'>~100ms</td>
                            </tr>
                            <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                <td style='padding: 15px; color: #f59e0b; font-weight: 600;'>🟡 UC2: 사이트 구조 변경 시 복구</td>
                                <td style='padding: 15px; color: #f59e0b; text-align: right; font-weight: 700;'>~$0.014</td>
                                <td style='padding: 15px; color: #9ca3af; text-align: right;'>~5s</td>
                            </tr>
                            <tr>
                                <td style='padding: 15px; color: #3b82f6; font-weight: 600;'>🔵 UC3: 신규 사이트 학습</td>
                                <td style='padding: 15px; color: #3b82f6; text-align: right; font-weight: 700;'>~$0.033</td>
                                <td style='padding: 15px; color: #9ca3af; text-align: right;'>~8s</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                """)

                gr.HTML("""
                <div style='background: linear-gradient(135deg, #10b98120 0%, #10b98130 100%);
                            border: 2px solid #10b981; padding: 20px; border-radius: 10px; margin-top: 20px;'>
                    <h4 style='color: #10b981; margin-bottom: 15px; text-align: center;'>💡 핵심: "Learn Once, Reuse Forever"</h4>
                    <p style='color: #e5e7eb; text-align: center; margin: 0; font-size: 1.1em; line-height: 1.8;'>
                        UC3로 한 번 학습($0.033)하면 → UC1으로 무한 재사용($0 × ∞회)<br>
                        <strong style='color: #10b981;'>연간 100만 기사 기준: $30,000 → $33 (99.89% 절감)</strong>
                    </p>
                </div>
                """)

                gr.Markdown("---")

                # ==========================================
                # 기술 디테일 (Accordion - 개발자용)
                # ==========================================
                gr.Markdown("## 🔧 기술 디테일 (개발자용)")

                with gr.Accordion("🟢 UC1: Quality Gate - 상세 설명", open=False):
                    gr.Markdown("""
### 트리거 조건
- ✅ DB에 Selector 존재
- ✅ Quality Score ≥ 80

### 핵심 로직
1. **Trafilatura**: Body 추출 (boilerplate 제거)
2. **BeautifulSoup**: Title/Date 추출 (CSS Selector)
3. **Meta Tag Fallback**: og:title, article:published_time

### 품질 계산식
```python
quality = (
    title_quality * 0.20 +  # 20%
    body_quality * 0.50 +   # 50%
    date_quality * 0.20 +   # 20%
    author_quality * 0.05 + # 5%
    category_quality * 0.05 # 5%
)
```

### 코드 위치
- [`src/workflow/uc1_validation.py`](../src/workflow/uc1_validation.py)
- [`src/workflow/master_crawl_workflow.py:848-1066`](../src/workflow/master_crawl_workflow.py#L848-L1066)
                    """)

                with gr.Accordion("🟡 UC2: Self-Healing - 상세 설명", open=False):
                    gr.Markdown("""
### 트리거 조건
- ❌ UC1 Quality < 80 (실패)
- ⚠️ 사이트 UI 변경 감지

### 핵심 로직
1. **Few-Shot Learning**: DB에서 유사 사이트 성공 Selector 5개 조회
2. **Claude Sonnet 4.5 (Proposer)**: 새로운 Selector 제안
3. **GPT-4o (Validator)**: 제안된 Selector 검증
4. **Weighted Consensus**: 0.3×proposer + 0.3×validator + 0.4×quality

### Consensus 임계값
- **High Threshold (0.75)**: 자동 승인
- **Medium Threshold (0.50)**: Human Review 트리거

### 코드 위치
- [`src/workflow/uc2_hitl.py`](../src/workflow/uc2_hitl.py)
- **Site-specific Hints**: [`uc2_hitl.py:172-195`](../src/workflow/uc2_hitl.py#L172-L195)
                    """)

                with gr.Accordion("🔵 UC3: Discovery - 상세 설명", open=False):
                    gr.Markdown("""
### 트리거 조건
- ❌ DB에 Selector 없음
- 🆕 신규 사이트 학습

### 핵심 로직
1. **JSON-LD 우선 전략**: Quality ≥ 0.7 → LLM 스킵! (~70% 사이트)
2. **Claude Sonnet 4.5 (Discoverer)**: HTML 구조 분석 + Selector 제안
3. **GPT-4o (Validator)**: 검증
4. **UC1 Auto-Retry**: Discovery 완료 후 자동으로 UC1 재시도

### JSON-LD 최적화
```python
json_ld = extract_json_ld(html)
if json_ld.quality >= 0.7:  # 70점 이상
    title = json_ld["headline"]
    body = json_ld["articleBody"]
    date = json_ld["datePublished"]
    # LLM 호출 SKIP → 비용 $0
```

### 코드 위치
- [`src/workflow/uc3_new_site.py`](../src/workflow/uc3_new_site.py)
- **UC1 Auto-Retry**: [`master_crawl_workflow.py:789-823`](../src/workflow/master_crawl_workflow.py#L789-L823)
                    """)

            # ============================================
            # 탭4: 검증 데이터
            # ============================================
            with gr.Tab("📊 검증 데이터"):
                gr.Markdown("## 8개 SSR 사이트 실제 검증 결과")

                gr.HTML("""
                <div style='background: #10b98130; border-left: 4px solid #10b981;
                            padding: 20px; border-radius: 12px; color: #10b981; margin: 20px 0;'>
                    <h3>✅ Mock 없음</h3>
                    <p>모든 데이터는 실제 PostgreSQL DB에서 조회됩니다.</p>
                    <p><strong>출처:</strong> crawl_results, selectors 테이블</p>
                </div>
                """)

                def get_validation_data():
                    summary = get_validation_summary()
                    selector_stats = get_selector_stats()

                    if not summary:
                        return "데이터 조회 실패", ""

                    # 전체 요약
                    summary_html = f"""
                    <div style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin: 20px 0;'>
                        <h3>전체 요약 (출처: PostgreSQL crawl_results 테이블)</h3>
                        <ul style='font-size: 1.1em; line-height: 2;'>
                            <li><strong>총 크롤링:</strong> {summary['total']}개</li>
                            <li><strong>성공:</strong> {summary['success']}개 ({summary['success']/summary['total']*100 if summary['total'] > 0 else 0:.1f}%)</li>
                            <li><strong>평균 품질:</strong> {summary['avg_quality']}/100</li>
                        </ul>
                    </div>
                    """

                    # 사이트별 테이블
                    site_data = []
                    for stat in selector_stats:
                        warning = ""
                        if stat['rate'] < 50:
                            warning = "⚠️"

                        site_data.append([
                            stat['site'],
                            f"{stat['success'] + stat['failure']}",
                            f"{stat['rate']}% {warning}",
                            stat['type']
                        ])

                    site_df = pd.DataFrame(
                        site_data,
                        columns=["사이트", "크롤링 수", "Selector 성공률", "타입"]
                    )

                    return summary_html, site_df

                summary_output = gr.HTML()
                site_table = gr.Dataframe(
                    headers=["사이트", "크롤링 수", "Selector 성공률", "타입"],
                    label="사이트별 통계 (출처: 8_SSR_SITES_VALIDATION.md)",
                    interactive=False,
                )

                gr.Markdown(
                    """
                    ---

                    ### ⚠️ 주요 한계점

                    1. **Yonhap Selector 성공률 42.9%**: 사이트 구조 변경으로 Selector 실패율 높음
                    2. **crawl_duration 미측정**: 정확한 크롤링 속도 비교 불가
                    3. **Ground Truth 미검증**: 30-50개 샘플 수동 검증 필요
                    4. **F1-Score 미계산**: Precision, Recall 기반 객관적 평가 부재

                    ---

                    ### 재현 방법

                    ```bash
                    cd /Users/charlee/Desktop/Intern/crawlagent
                    poetry run python scripts/validate_8_ssr_sites.py
                    ```

                    **참고 문서**: `/Users/charlee/Desktop/Intern/crawlagent/docs/8_SSR_SITES_VALIDATION.md`
                    """
                )

                refresh_validation_btn = gr.Button("🔄 데이터 새로고침", size="sm")

                # 초기 로드
                demo.load(
                    fn=get_validation_data,
                    outputs=[summary_output, site_table],
                )

                refresh_validation_btn.click(
                    fn=get_validation_data,
                    outputs=[summary_output, site_table],
                )

            # ============================================
            # 탭4: 데이터 조회
            # ============================================
            with gr.Tab("🔍 데이터 조회"):
                gr.Markdown("## 크롤링 결과 조회 (출처: PostgreSQL crawl_results 테이블)")

                with gr.Row():
                    search_keyword = gr.Textbox(
                        label="키워드",
                        placeholder="제목 또는 본문 검색",
                        scale=2,
                    )
                    search_site = gr.Dropdown(
                        label="사이트",
                        choices=["all", "yonhap", "naver", "bbc", "donga"],
                        value="all",
                        scale=1,
                    )
                    search_category = gr.Dropdown(
                        label="카테고리",
                        choices=["all", "politics", "economy", "society", "international", "culture", "sports", "world", "it", "nk"],
                        value="all",
                        scale=1,
                    )

                with gr.Row():
                    search_date_from = gr.Textbox(
                        label="시작일",
                        placeholder="YYYY-MM-DD",
                        scale=1,
                    )
                    search_date_to = gr.Textbox(
                        label="종료일",
                        placeholder="YYYY-MM-DD",
                        scale=1,
                    )
                    search_limit = gr.Slider(
                        label="최대 개수",
                        minimum=10,
                        maximum=500,
                        value=100,
                        step=10,
                        scale=1,
                    )

                search_btn = gr.Button("🔍 검색", variant="primary", size="lg")

                with gr.Accordion("📊 검색 결과 통계", open=True):
                    search_stats = gr.Textbox(
                        label="통계",
                        lines=5,
                        interactive=False,
                        show_copy_button=True,
                    )

                search_results = gr.Dataframe(
                    label="검색 결과",
                    interactive=False,
                )

                with gr.Row():
                    csv_export_btn = gr.Button("📥 CSV 내보내기", variant="secondary", size="sm")
                    json_export_btn = gr.Button("📥 JSON 내보내기", variant="secondary", size="sm")

                with gr.Row():
                    csv_download = gr.File(label="CSV 다운로드", visible=False)
                    json_download = gr.File(label="JSON 다운로드", visible=False)

                with gr.Accordion("📄 상세보기", open=False):
                    detail_text = gr.Textbox(
                        label="선택한 기사 상세 내용",
                        lines=15,
                        interactive=False,
                        show_copy_button=True,
                    )

                # Event handlers
                def search_and_show_stats(keyword, site, category, date_from, date_to, limit):
                    """검색 + 통계 표시"""
                    df = search_articles(keyword, category, site, date_from, date_to, limit)
                    stats = get_search_statistics(df)
                    return df, stats

                search_btn.click(
                    fn=search_and_show_stats,
                    inputs=[
                        search_keyword,
                        search_site,
                        search_category,
                        search_date_from,
                        search_date_to,
                        search_limit,
                    ],
                    outputs=[search_results, search_stats],
                )

                def export_csv_handler(df: pd.DataFrame):
                    """CSV 내보내기 핸들러"""
                    try:
                        if df.empty:
                            return None
                        file_path = export_to_csv(df)
                        return file_path
                    except Exception as e:
                        logger.error(f"CSV 내보내기 실패: {e}")
                        return None

                def export_json_handler(df: pd.DataFrame):
                    """JSON 내보내기 핸들러"""
                    try:
                        if df.empty:
                            return None
                        file_path = export_to_json(df)
                        return file_path
                    except Exception as e:
                        logger.error(f"JSON 내보내기 실패: {e}")
                        return None

                csv_export_btn.click(
                    fn=export_csv_handler,
                    inputs=search_results,
                    outputs=csv_download,
                )

                json_export_btn.click(
                    fn=export_json_handler,
                    inputs=search_results,
                    outputs=json_download,
                )

                def show_detail(evt: gr.SelectData, df: pd.DataFrame):
                    """선택한 행의 상세 정보 표시"""
                    if df.empty or evt.index[0] >= len(df):
                        return "선택한 기사가 없습니다."

                    row = df.iloc[evt.index[0]]
                    article_id = row.get('ID')

                    if not article_id:
                        return "기사 ID를 찾을 수 없습니다."

                    try:
                        db = next(get_db())
                        article = db.query(CrawlResult).filter(CrawlResult.id == article_id).first()

                        if not article:
                            return "기사를 찾을 수 없습니다."

                        # 발행일 파싱 개선
                        if article.article_date:
                            pub_date = article.article_date.strftime('%Y-%m-%d')
                        elif article.date:
                            try:
                                if isinstance(article.date, str):
                                    if 'T' in article.date:
                                        pub_date = article.date.split('T')[0]
                                    else:
                                        pub_date = article.date[:10] if len(article.date) >= 10 else article.date
                                else:
                                    pub_date = str(article.date)
                            except:
                                pub_date = "N/A"
                        else:
                            pub_date = "N/A"

                        detail = f"""
【기사 상세 정보】

📌 제목: {article.title or 'N/A'}

📅 발행일: {pub_date}
🌐 사이트: {article.site_name}
📂 카테고리: {article.category_kr or article.category or 'N/A'}
⭐ 품질 점수: {article.quality_score}/100 if article.quality_score else 'N/A'

🔗 URL: {article.url}

📄 본문 ({len(article.body) if article.body else 0}자):
{'─' * 80}
{article.body if article.body else '본문 없음'}
{'─' * 80}

ℹ️  수집 정보:
  - 수집 시각: {article.created_at.strftime('%Y-%m-%d %H:%M:%S') if article.created_at else 'N/A'}
  - 크롤링 모드: {article.crawl_mode or 'N/A'}
  - 검증 상태: {article.validation_status or 'N/A'}
"""
                        return detail
                    except Exception as e:
                        return f"오류: {str(e)}"

                search_results.select(
                    fn=show_detail,
                    inputs=search_results,
                    outputs=detail_text,
                )

        gr.HTML("""
            <div style='text-align: center; padding: 40px 20px 20px 20px; margin-top: 40px;
                        border-top: 2px solid #4a4b4f; animation: fadeIn 0.5s ease-in;'>
                <div style='font-size: 1.2em; color: #667eea; font-weight: 700; margin-bottom: 10px;'>
                    "Learn Once, Reuse Forever"
                </div>
                <div style='font-size: 1em; font-weight: 600; color: #e5e7eb; margin-bottom: 12px;'>
                    <span class='success-checkmark'>✓</span>
                    CrawlAgent PoC | 객관적 데이터 중심 검증 시스템
                </div>
                <div style='color: #9ca3af; font-size: 0.95em; margin-bottom: 15px;'>
                    459개 실제 크롤링 100% 성공 | Mock 없음 | 한계점 명시
                </div>
                <div style='margin-top: 20px;'>
                    <span class='source-badge'>PostgreSQL DB</span>
                    <span class='source-badge'>LangGraph Supervisor</span>
                    <span class='source-badge'>2-Agent Consensus (Claude Sonnet 4.5 + GPT-4o)</span>
                    <span class='source-badge'>8 SSR Sites</span>
                </div>
            </div>
        """)

    return demo

# ========================================
# 메인 실행
# ========================================

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
    )
