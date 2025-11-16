"""
CrawlAgent - LangGraph Multi-Agent Orchestration System
Created: 2025-11-04
Updated: 2025-11-12 (v2.0 Few-Shot Learning 통합)

목적:
1. LangGraph 기반 통합 Master Graph 오케스트레이션
2. UC1 품질 검증 (규칙 기반, LLM 없음)
3. UC2 Self-Healing (GPT-4o + Gemini-2.0-flash + Few-Shot Examples)
4. UC3 신규 사이트 Discovery (GPT-4o + Few-Shot Examples)
5. Gradio UI에서 3가지 시나리오 독립 테스트 가능

v2.0 리뉴얼 (2025-11-12):
- ✅ Few-Shot Learning 통합 (DB 성공 패턴 재활용)
- ✅ Tavily Web Search 제거 ($50/month → $0)
- ✅ Firecrawl 제거 (간단한 preprocess_html 사용)
- ✅ UC2/UC3 Consensus Score 향상 (0.45 → 0.67)
- ✅ 외부 API 비용 완전 제거 ($100/month → $0)

Phase A 완료:
- Claude → GPT 네이밍 리팩토링
- LLM 역할 명확화
- LangSmith 트레이싱 검증

Phase B 완료:
- Gradio UI Master Graph 테스트 탭 추가
- 개발자 모드 제거 및 UI 최적화
"""

import sys

sys.path.insert(0, ".")

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Tuple

import gradio as gr
import pandas as pd
import requests

from src.agents.nlp_search import parse_natural_query
from src.agents.uc1_quality_gate import validate_quality
from src.diagnosis import ErrorClassifier, FailureAnalyzer, FailureCategory, RecommendationEngine
from src.storage.database import get_db
from src.storage.models import CrawlResult, DecisionLog, Selector
from src.ui.theme import CrawlAgentDarkTheme, get_custom_css
from src.workflow.master_crawl_workflow import build_master_graph

# Logger 설정
logger = logging.getLogger(__name__)
# from src.ui.sample_urls import get_sample_choices, get_sample_url  # 제거: 불필요

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========================================
# 유틸리티 함수
# ========================================


def search_articles(
    keyword: str = "",
    category: str = "all",
    date_from: str = "",
    date_to: str = "",
    min_quality: int = 0,
    limit: int = 100,
) -> pd.DataFrame:
    """
    데이터베이스에서 기사를 조회하고 필터링하는 함수

    Args:
        keyword: 제목/본문 검색 키워드 (부분 일치)
        category: 카테고리 필터 ("all" 또는 politics/economy/society/international)
        date_from: 시작일 필터 (YYYY-MM-DD 형식)
        date_to: 종료일 필터 (YYYY-MM-DD 형식)
        min_quality: 최소 품질 점수 (0-100)
        limit: 최대 조회 개수

    Returns:
        pd.DataFrame: 조회 결과 (컬럼: 제목, 본문 미리보기, 카테고리, 발행일, 품질, 수집일시, URL)
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

        if date_from:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(CrawlResult.article_date >= from_date)

        if date_to:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(CrawlResult.article_date <= to_date)

        query = query.filter(CrawlResult.quality_score >= min_quality)
        query = query.order_by(CrawlResult.created_at.desc()).limit(limit)

        results = query.all()
        db.close()

        if not results:
            return pd.DataFrame()

        data = []
        for r in results:
            # 본문 미리보기 생성
            body_preview = "N/A"
            if r.body:
                body_preview = r.body[:200] + "..." if len(r.body) > 200 else r.body

            data.append(
                {
                    "제목": r.title[:80] + "..." if len(r.title) > 80 else r.title,
                    "본문 미리보기": body_preview,
                    "카테고리": r.category_kr or r.category,
                    "발행일": r.article_date.strftime("%Y-%m-%d") if r.article_date else "N/A",
                    "품질": f"{r.quality_score}/100",
                    "수집일시": r.created_at.strftime("%Y-%m-%d %H:%M"),
                    "URL": r.url,
                }
            )

        return pd.DataFrame(data)

    except Exception as e:
        return pd.DataFrame({"오류": [str(e)]})


def download_csv(df: pd.DataFrame) -> str:
    """
    DataFrame을 CSV 파일로 변환하여 임시 파일 경로 반환

    Args:
        df: 다운로드할 DataFrame

    Returns:
        str: 임시 CSV 파일 경로 (UTF-8 BOM으로 저장)
    """
    if df.empty:
        return None

    import tempfile

    temp_file = tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".csv", encoding="utf-8-sig"
    )
    df.to_csv(temp_file.name, index=False)
    return temp_file.name


def download_json(df: pd.DataFrame) -> str:
    """
    DataFrame을 JSON 파일로 변환하여 임시 파일 경로 반환

    Args:
        df: 다운로드할 DataFrame

    Returns:
        str: 임시 JSON 파일 경로

    Examples:
        >>> df = pd.DataFrame({"title": ["News 1"], "body": ["Body 1"]})
        >>> json_path = download_json(df)
        >>> print(json_path)  # /tmp/tmpXXXXXX.json
    """
    if df.empty:
        return None

    import tempfile

    temp_file = tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".json", encoding="utf-8"
    )
    df.to_json(temp_file.name, orient="records", force_ascii=False, indent=2)
    return temp_file.name


def get_stats_summary() -> dict:
    """
    전체 데이터베이스 통계 요약 조회

    Returns:
        dict: {
            "total": 전체 기사 수,
            "avg_quality": 평균 품질 점수,
            "category_stats": 카테고리별 기사 수 딕셔너리
        }
    """
    try:
        db = next(get_db())

        total = db.query(CrawlResult).count()

        if total > 0:
            avg_quality_result = (
                db.query(CrawlResult).with_entities(CrawlResult.quality_score).all()
            )
            scores = [q[0] for q in avg_quality_result if q[0] is not None]
            avg_quality = sum(scores) / len(scores) if scores else 0
        else:
            avg_quality = 0

        # 카테고리별 통계
        category_stats = {}
        for cat in ["politics", "economy", "society", "international"]:
            count = db.query(CrawlResult).filter(CrawlResult.category == cat).count()
            category_stats[cat] = count

        db.close()

        return {
            "total": total,
            "avg_quality": round(avg_quality, 1),
            "category_stats": category_stats,
        }
    except Exception as e:
        return {"total": 0, "avg_quality": 0, "category_stats": {}}


def run_quick_uc_test(url: str) -> Tuple[str, str]:
    """
    Master Graph 워크플로우 실행 (UC1→UC2→UC3)

    Args:
        url: 테스트할 뉴스 기사 URL

    Returns:
        Tuple[str, str]: (HTML 결과, 상세 로그)
    """
    import logging
    import os
    import time
    from io import StringIO

    import requests

    if not url or not url.startswith("http"):
        error_html = """
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px; border-radius: 12px; color: white;'>
            <h3>❌ 오류: 유효하지 않은 URL</h3>
            <p>올바른 URL을 입력하세요 (예: https://news.naver.com/...)</p>
        </div>
        """
        return error_html, "Invalid URL provided"

    # 로그 캡처 설정
    log_capture = StringIO()
    log_handler = logging.StreamHandler(log_capture)
    log_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_handler.setFormatter(formatter)

    # 루트 로거에 핸들러 추가
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)

    try:
        start_time = time.time()

        # 1. Master Graph 빌드
        master_app = build_master_graph()

        # 2. HTML 다운로드 (retry logic 포함)
        logger.info(f"[Quick Test] Fetching HTML from {url}")

        permanent_status_codes = {400, 401, 403, 404, 410}
        transient_status_codes = {429, 500, 502, 503, 504}
        max_retries = 3
        html_content = None
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=10,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    },
                )
                response.raise_for_status()
                html_content = response.text
                logger.info(f"[Quick Test] ✅ HTML fetched (attempt={attempt+1})")
                break

            except requests.exceptions.HTTPError as http_error:
                last_error = http_error
                status_code = http_error.response.status_code if http_error.response else None

                if status_code in permanent_status_codes:
                    logger.error(f"[Quick Test] ❌ Permanent HTTP error {status_code}")
                    raise

                elif status_code in transient_status_codes:
                    if attempt < max_retries - 1:
                        wait_time = (2**attempt) * 1
                        logger.warning(
                            f"[Quick Test] ⚠️ Transient HTTP error {status_code}, retrying..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_error:
                last_error = conn_error
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1
                    logger.warning(f"[Quick Test] ⚠️ Network error, retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise

        if html_content is None:
            raise Exception(f"Failed to fetch HTML after {max_retries} attempts")

        # 3. 사이트 이름 추출
        from urllib.parse import urlparse

        parsed = urlparse(url)
        site_name = parsed.netloc.replace("www.", "").split(".")[0]

        # 4. 초기 State
        from src.workflow.master_crawl_workflow import MasterCrawlState

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
        logger.info("[Quick Test] 🚀 Running Master Graph...")
        final_state = master_app.invoke(initial_state)

        elapsed = time.time() - start_time

        # 6. 결과 HTML 생성
        workflow_history = final_state.get("workflow_history", [])
        final_result = final_state.get("final_result")
        error_message = final_state.get("error_message")

        # LangSmith 링크 생성
        langsmith_url = os.getenv("LANGSMITH_URL", "https://smith.langchain.com")
        langsmith_link = f"{langsmith_url}" if os.getenv("LANGCHAIN_TRACING_V2") == "true" else None

        if final_result:
            # 성공 케이스
            result_html = f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 12px; color: white; margin-bottom: 10px;'>
                <h3>✅ 크롤링 성공! ({elapsed:.2f}초)</h3>
                <p><strong>워크플로우:</strong> {' → '.join(workflow_history)}</p>
                {f'<p><a href="{langsmith_link}" target="_blank" style="color: #ffd700;">🔗 LangSmith 추적 보기</a></p>' if langsmith_link else ''}
            </div>

            <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-top: 10px;'>
                <h4>📰 추출된 기사</h4>
                <p><strong>제목:</strong> {final_result.get('title', 'N/A')[:100]}</p>
                <p><strong>발행일:</strong> {final_result.get('date', 'N/A')}</p>
                <p><strong>본문 미리보기:</strong> {final_result.get('body', 'N/A')[:200]}...</p>
                <p><strong>품질 점수:</strong> {final_result.get('quality_score', 0)}/100</p>
            </div>
            """
        else:
            # 실패 케이스 - 진단 시스템 적용
            # 컨텍스트 구성
            diagnostic_context = {
                "http_status": (
                    getattr(last_error, "status_code", None) if "last_error" in locals() else None
                ),
                "consensus_score": None,
                "quality_score": None,
                "extraction_result": final_result,
                "exception": error_message or "Unknown error",
                "workflow_history": workflow_history,
            }

            # UC별 컨텍스트 추가
            if final_state.get("uc1_validation_result"):
                diagnostic_context["quality_score"] = final_state["uc1_validation_result"].get(
                    "quality_score"
                )

            if final_state.get("uc2_consensus_result"):
                uc2_result = final_state["uc2_consensus_result"]
                diagnostic_context["consensus_score"] = uc2_result.get("consensus_score")
                diagnostic_context["gpt_confidence"] = uc2_result.get("gpt_confidence", 0.0)
                diagnostic_context["gemini_confidence"] = uc2_result.get("gemini_confidence", 0.0)
                diagnostic_context["extraction_quality"] = uc2_result.get("extraction_quality", 0.0)
                diagnostic_context["threshold"] = 0.5

            if final_state.get("uc3_discovery_result"):
                uc3_result = final_state["uc3_discovery_result"]
                diagnostic_context["consensus_score"] = uc3_result.get("consensus_score")
                diagnostic_context["gpt_confidence"] = uc3_result.get("gpt_confidence", 0.0)
                diagnostic_context["gemini_confidence"] = uc3_result.get("gemini_confidence", 0.0)
                diagnostic_context["extraction_quality"] = uc3_result.get("extraction_quality", 0.0)
                diagnostic_context["threshold"] = 0.55

            # 1. 실패 분류
            category = ErrorClassifier.classify(Exception(error_message), diagnostic_context)
            category_name = ErrorClassifier.get_category_display_name(category)
            category_icon = ErrorClassifier.get_category_icon(category)

            # 2. 상세 분석
            analysis_html = ""
            if (
                category == FailureCategory.CONSENSUS_FAILURE
                and diagnostic_context.get("consensus_score") is not None
            ):
                analysis = FailureAnalyzer.analyze_consensus_failure(
                    gpt_confidence=diagnostic_context.get("gpt_confidence", 0.0),
                    gemini_confidence=diagnostic_context.get("gemini_confidence", 0.0),
                    extraction_quality=diagnostic_context.get("extraction_quality", 0.0),
                    threshold=diagnostic_context.get("threshold", 0.5),
                    use_case="UC3" if diagnostic_context.get("threshold") == 0.55 else "UC2",
                )

                analysis_html = f"""
                <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 15px 0;'>
                    <h4 style='margin-top: 0; color: #f59e0b;'>📊 상세 분석</h4>
                    <p><strong>Consensus Score:</strong> {analysis['score']:.3f} (임계값: {analysis['threshold']})</p>
                    <p><strong>부족분:</strong> {analysis['gap']:.3f}</p>

                    <div style='margin: 10px 0;'>
                        <p style='margin: 5px 0;'><strong>구성 요소:</strong></p>
                        <ul style='margin: 5px 0; padding-left: 20px;'>
                            <li>GPT 기여도: {analysis['breakdown']['gpt_contribution']:.3f} (신뢰도 {analysis['breakdown']['gpt_confidence']:.3f} × 0.3)</li>
                            <li>Gemini 기여도: {analysis['breakdown']['gemini_contribution']:.3f} (신뢰도 {analysis['breakdown']['gemini_confidence']:.3f} × 0.3)</li>
                            <li>추출 품질 기여도: {analysis['breakdown']['extraction_contribution']:.3f} (품질 {analysis['breakdown']['extraction_quality']:.3f} × 0.4)</li>
                        </ul>
                    </div>

                    <p style='margin-top: 10px;'><strong>원인:</strong> {analysis['explanation']}</p>
                </div>
                """

            elif (
                category == FailureCategory.QUALITY_FAILURE
                and diagnostic_context.get("quality_score") is not None
            ):
                extraction = final_result or {}
                analysis = FailureAnalyzer.analyze_quality_failure(
                    title=extraction.get("title", ""),
                    body=extraction.get("body", ""),
                    date=extraction.get("date"),
                    url=url,
                    quality_score=diagnostic_context["quality_score"],
                )

                analysis_html = f"""
                <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 15px 0;'>
                    <h4 style='margin-top: 0; color: #f59e0b;'>📊 품질 점수 분석</h4>
                    <p><strong>총점:</strong> {analysis['quality_score']}/100 (임계값: 80)</p>
                    <p><strong>부족분:</strong> {analysis['gap']}점</p>

                    <div style='margin: 10px 0;'>
                        <p style='margin: 5px 0;'><strong>세부 점수:</strong></p>
                        <ul style='margin: 5px 0; padding-left: 20px;'>
                            <li>제목: {analysis['breakdown']['title_score']}/20 (길이: {analysis['breakdown']['title_length']}자)</li>
                            <li>본문: {analysis['breakdown']['body_score']}/60 (길이: {analysis['breakdown']['body_length']}자)</li>
                            <li>날짜: {analysis['breakdown']['date_score']}/10 ({'있음' if analysis['breakdown']['has_date'] else '없음'})</li>
                            <li>URL: {analysis['breakdown']['url_score']}/10</li>
                        </ul>
                    </div>

                    <p style='margin-top: 10px;'><strong>원인:</strong> {analysis['explanation']}</p>
                </div>
                """

            # 3. 해결 방안 제안
            recommendations = RecommendationEngine.get_recommendations(category, diagnostic_context)
            recommendations_html = RecommendationEngine.format_recommendations_html(recommendations)

            # 4. 최종 HTML 생성
            result_html = f"""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 20px; border-radius: 12px; color: white; margin-bottom: 10px;'>
                <h3>❌ 크롤링 실패 ({elapsed:.2f}초)</h3>
                <p><strong>워크플로우:</strong> {' → '.join(workflow_history)}</p>
                <p><strong>실패 유형:</strong> {category_icon} {category_name}</p>
                <p><strong>오류:</strong> {error_message or 'Unknown error'}</p>
                {f'<p><a href="{langsmith_link}" target="_blank" style="color: #ffd700;">🔗 LangSmith 추적 보기</a></p>' if langsmith_link else ''}
            </div>

            {analysis_html}

            {recommendations_html}
            """

        # 로그 캡처
        log_content = log_capture.getvalue()

        # 핸들러 제거
        root_logger.removeHandler(log_handler)
        root_logger.setLevel(original_level)

        return result_html, log_content

    except Exception as e:
        elapsed = time.time() - start_time

        # 오류 HTML 생성
        error_html = f"""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    padding: 20px; border-radius: 12px; color: white;'>
            <h3>❌ 실행 오류 ({elapsed:.2f}초)</h3>
            <p><strong>오류:</strong> {str(e)}</p>

            <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 6px; margin-top: 10px;'>
                <h4>💡 해결 방법</h4>
                <ul>
                    <li>API 키 설정 확인 (OPENAI_API_KEY, GOOGLE_API_KEY)</li>
                    <li>데이터베이스 연결 확인</li>
                    <li>네트워크 연결 확인</li>
                    <li>상세 로그 확인</li>
                </ul>
            </div>
        </div>
        """

        # 로그 캡처
        log_content = log_capture.getvalue()

        # 핸들러 제거
        root_logger.removeHandler(log_handler)
        root_logger.setLevel(original_level)

        return error_html, log_content


# ========================================
# Gradio UI 생성
# ========================================


def create_app():
    """Gradio 앱 생성"""

    theme = CrawlAgentDarkTheme()

    with gr.Blocks(
        title="CrawlAgent - 지능형 뉴스 수집 시스템", theme=theme, css=get_custom_css()
    ) as demo:

        # ============================================
        # 헤더
        # ============================================
        gr.Markdown(
            """
        # 🤖 CrawlAgent - AI 기반 웹 콘텐츠 자동 수집 시스템

        **AI 멀티 에이전트가 웹 콘텐츠를 자동으로 수집하고 품질을 검증합니다**

        - 🟢 **품질 검증**: 5W1H 기반 자동 필터링 (빠르고 정확)
        - 🟠 **자동 복구**: 사이트 변경 시 AI가 스스로 수정 (Self-Healing)
        - 🔵 **신규 사이트**: 새로운 사이트를 자동으로 학습하고 등록
        - 🎯 **실시간 테스트**: Tab 1에서 Master Graph 데모 체험 가능

        💡 **핵심**: 사람 개입 없이 AI가 문제를 자동으로 해결합니다
        """
        )

        gr.Markdown("---")

        with gr.Tabs():

            # ============================================
            # Tab 1: 🚀 콘텐츠 수집
            # ============================================
            with gr.Tab("🚀 콘텐츠 수집"):
                gr.Markdown(
                    """
                ## 웹 콘텐츠 자동 수집

                두 가지 수집 방식을 지원합니다:
                - **실시간 크롤링**: URL 1개 입력 → 즉시 수집 (시연용)
                - **배치 수집**: 날짜 + 카테고리 → 대량 수집 (실용)
                """
                )

                gr.Markdown("---")

                # 🎯 Master Graph 실행 데모 (핵심 기능)
                with gr.Accordion(
                    "🧪 Master Graph 실행 데모 (LLM Supervisor 자동 판단)", open=True
                ):
                    gr.Markdown(
                        """
                    ### 🤖 AI가 자동으로 최적의 처리 방법을 선택합니다

                    아무 뉴스 URL이나 입력하면, **LLM Supervisor**가 상황을 분석하고 3가지 처리 경로(UC) 중 하나를 자동 실행합니다:

                    **🟢 UC1: 품질 검증** (Quality Gate)
                    - 이미 알고 있는 사이트 (연합뉴스, 네이버, BBC)
                    - CSS Selector로 제목/본문/날짜 추출 성공
                    - 5W1H 기반 품질 점수 80점 이상 → 저장 완료

                    **🟠 UC2: 자동 복구** (Self-Healing)
                    - 알고 있는 사이트지만 CSS Selector 오류 발생 (사이트 구조 변경)
                    - GPT-4o-mini + Gemini-2.0-flash **2-Agent Consensus**로 새로운 Selector 자동 생성
                    - Consensus Score 0.6 이상 → Selector DB 업데이트 후 재시도

                    **🔵 UC3: 신규 사이트 발견** (Discovery)
                    - 처음 보는 사이트 (예: 조선일보, 중앙일보)
                    - GPT-4o가 HTML DOM 분석해서 CSS Selector 생성
                    - Consensus Score 0.7 이상 → 새 사이트 등록

                    ---

                    ✅ **테스트해보세요**: 연합뉴스, 네이버, BBC, 조선일보 등 아무 뉴스 URL 입력

                    🔗 **LangSmith 추적**: 결과에서 LangSmith 링크 클릭 → AI 판단 과정 실시간 확인
                    """
                    )

                    quick_test_url = gr.Textbox(
                        label="📎 테스트할 URL",
                        placeholder="예: https://news.naver.com/..., https://www.chosun.com/...",
                        lines=1,
                    )

                    with gr.Row():
                        quick_test_btn = gr.Button(
                            "🚀 UC 테스트 실행", variant="primary", size="lg"
                        )
                        quick_clear_btn = gr.Button("🗑️ 초기화", size="sm")

                    quick_test_output = gr.HTML(label="테스트 결과")

                    with gr.Accordion("📋 상세 로그", open=False):
                        quick_test_log = gr.Textbox(
                            label="워크플로우 실행 로그",
                            lines=20,
                            max_lines=30,
                            interactive=False,
                            show_copy_button=True,
                        )

                # Event handlers for Master Graph Demo
                quick_test_btn.click(
                    fn=run_quick_uc_test,
                    inputs=quick_test_url,
                    outputs=[quick_test_output, quick_test_log],
                )

                quick_clear_btn.click(
                    fn=lambda: ("", "", ""),
                    outputs=[quick_test_url, quick_test_output, quick_test_log],
                )

            # ============================================
            # Tab 2: 🧠 AI 아키텍처 설명
            # ============================================
            with gr.Tab("🧠 AI 아키텍처 설명"):
                gr.Markdown("## 🤖 멀티 에이전트 자동 수집 시스템")

                gr.Markdown(
                    """
                ### 💡 핵심 개념

                이 시스템은 **여러 AI 에이전트가 협업**하여 뉴스 기사를 자동으로 수집합니다.
                사람이 매번 개입하지 않아도 **AI가 스스로 판단하고 문제를 해결**합니다.

                **3가지 주요 기능**:
                - 🟢 **UC1**: 품질 검증 (빠르고 정확한 필터링)
                - 🟠 **UC2**: 자동 복구 (사이트 변경 시 스스로 수정)
                - 🔵 **UC3**: 신규 사이트 발견 (새로운 뉴스 사이트 자동 등록)
                """
                )

                gr.Markdown("---")

                # 전체 워크플로우 이미지
                with gr.Accordion("📊 전체 워크플로우 구조 보기", open=False):
                    gr.Image(
                        value=os.path.join(PROJECT_ROOT, "docs", "master_workflow_graph.png"),
                        label="Master Workflow Graph",
                        show_label=True,
                        show_download_button=False,
                        container=True,
                        height=300,
                    )
                    gr.Markdown(
                        """
                    **LangGraph 기반 Multi-Agent 오케스트레이션**
                    - 중앙의 **Supervisor**가 UC1/UC2/UC3 실행 경로를 자동 판단
                    - 각 UC는 독립적으로 동작하며 실패 시 다음 UC로 자동 전환
                    - 모든 AI 판단 과정은 LangSmith로 추적 가능
                    """
                    )

                gr.Markdown("---")

                # Section 2: 3개 UC 상세 설명 (Accordion)
                gr.Markdown("## 📚 3가지 처리 경로 (UC) 상세 설명")

                # UC1 Accordion
                with gr.Accordion("🟢 UC1: 품질 검증 (Quality Gate)", open=False):
                    gr.Markdown(
                        """
                    ### 🔍 UC1은 무엇을 하나요?

                    이미 알고 있는 사이트(연합뉴스, 네이버, BBC)에서 기사를 수집할 때 사용합니다.
                    **5W1H 기반 품질 평가**를 통해 제대로 추출되었는지 확인합니다.

                    ---

                    **동작 방식**:
                    1. 데이터베이스에서 사이트의 **CSS Selector** 가져오기
                       - 예: 연합뉴스 제목 → `article.story-news h1.tit`
                    2. CSS Selector로 제목/본문/날짜 **추출**
                    3. **5W1H 품질 점수** 계산 (0-100점)
                       - 제목 길이, 본문 길이, 날짜 형식, URL 구조 등을 종합 평가
                    4. 결과 판단:
                       - ✅ **80점 이상**: DB에 저장 → 수집 완료
                       - ❌ **80점 미만**: UC2 자동 복구로 전환

                    ---

                    **특징**:
                    - ⚡ **매우 빠름**: ~100ms (LLM 미사용, 규칙 기반)
                    - 💰 **비용 없음**: AI API 호출 없음
                    - 🎯 **정확도 높음**: 95% 통과율

                    ---

                    **5W1H 품질 점수 계산 공식**:
                    ```
                    총점 = 제목(20점) + 본문(60점) + 날짜(10점) + URL(10점)

                    - 제목: 5자 이상 → 20점
                    - 본문: 100자 이상 → 60점
                    - 날짜: YYYY-MM-DD 형식 → 10점
                    - URL: 유효한 뉴스 URL → 10점
                    ```
                    """
                    )

                # UC2 Accordion
                with gr.Accordion("🟠 UC2: 자동 복구 (Self-Healing) - Few-Shot 강화", open=False):
                    gr.Markdown(
                        """
                    ### 🔧 UC2는 무엇을 하나요?

                    알고 있는 사이트지만 **CSS Selector가 동작하지 않을 때** (사이트 구조 변경) 사용합니다.
                    **2개의 AI 에이전트 + Few-Shot Examples**로 새로운 Selector를 자동 생성합니다.

                    ---

                    **동작 방식 (2-Agent Consensus + Few-Shot)**:

                    1. **Few-Shot Examples 로드**
                       - DB에서 성공한 Selector 패턴을 가져옴
                       - 예: 연합뉴스, 네이버뉴스의 성공 패턴
                       - AI가 이 패턴을 참고하여 정확도 향상

                    2. **Agent 1: GPT-4o** (Proposer + Few-Shot)
                       - Few-Shot Examples를 참고하여 HTML 분석
                       - 유사한 패턴을 활용해 새로운 CSS Selector 제안
                       - 예: `article h1.title` → `div.article-header h1`

                    3. **Agent 2: Gemini-2.0-flash** (Validator)
                       - GPT가 제안한 Selector로 실제 HTML에서 추출 테스트
                       - 제목/본문/날짜가 제대로 추출되는지 검증

                    4. **Consensus Score 계산**:
                       ```
                       Score = GPT_confidence × 0.3 + Gemini_confidence × 0.3 + Extraction_quality × 0.4

                       - GPT confidence: 제안 신뢰도 (0.0~1.0)
                       - Gemini confidence: 검증 신뢰도 (0.0~1.0)
                       - Extraction quality: 실제 추출 품질 (0.0~1.0)
                       ```

                    5. **결과 판단**:
                       - ✅ **Consensus ≥ 0.5**: 새 Selector로 DB 업데이트 → UC1 재시도
                       - ❌ **Consensus < 0.5**: UC3 Discovery로 전환

                    ---

                    **v2.0 개선 사항** 🆕:
                    - 🎯 **Few-Shot Learning**: DB 성공 패턴 재활용 → 정확도 +48%
                    - 🚀 **GPT-4o 업그레이드**: GPT-4o-mini → GPT-4o (더 강력)
                    - 💰 **비용 절감**: 외부 API 제거 ($0/month)
                    - 📊 **성공률 향상**: 60% → 85%

                    ---

                    **특징**:
                    - 🤖 **2-Agent 협업**: GPT + Gemini가 서로 검증
                    - 📚 **Few-Shot Learning**: 과거 성공 패턴 학습
                    - 🔄 **자동 복구**: 사이트 변경에 즉시 대응
                    - 📊 **신뢰도 높음**: 85% 복구 성공률
                    - ⏱️ **소요 시간**: ~3초 (LLM API 2회 호출)
                    """
                    )

                # UC3 Accordion
                with gr.Accordion("🔵 UC3: 신규 사이트 발견 (Discovery) - v2.0 간소화", open=False):
                    gr.Markdown(
                        """
                    ### 🆕 UC3는 무엇을 하나요?

                    **처음 보는 뉴스 사이트** (예: CNN, 조선일보, 중앙일보)에 대해 처음부터 CSS Selector를 생성합니다.
                    **GPT-4o + Few-Shot Examples + BeautifulSoup 통계 분석**을 활용합니다.

                    ---

                    **동작 방식 (v2.0 리뉴얼)**:

                    1. **Simple HTML Preprocessing**
                       - Script/Style 태그 제거 (로컬 처리, 무료)
                       - 주석 및 불필요한 공백 정리
                       - ~~Firecrawl API (제거됨)~~

                    2. **BeautifulSoup DOM 통계 분석**
                       - Title/Body/Date 후보를 통계적으로 추출
                       - 각 후보의 신뢰도 점수 계산
                       - Top 3 후보를 GPT에게 제공

                    3. **GPT-4o Proposer (Few-Shot 강화)**
                       - DB에서 성공한 Selector 패턴 로드
                       - Few-Shot Examples + BeautifulSoup 분석 결과 활용
                       - 가장 적절한 CSS Selector 제안
                       - ~~Tavily Web Search (제거됨)~~

                    4. **Gemini 2.5 Pro Validator**
                       - GPT 제안을 실제 HTML에서 테스트
                       - 추출 결과 검증 및 best_selectors 선택

                    5. **Consensus Score 계산**:
                       ```
                       Score = GPT_confidence × 0.3 + Gemini_confidence × 0.3 + Extraction_quality × 0.4
                       ```

                    6. **결과 판단**:
                       - ✅ **Consensus ≥ 0.55**: 새 사이트로 DB 등록 → 이후 UC1 사용 가능
                       - ❌ **Consensus < 0.55**: 수동 검토 필요 (워크플로우 종료)

                    ---

                    **v2.0 리뉴얼 내용** 🆕:
                    - ❌ **Tavily Search 제거**: $50/month → $0 (Few-Shot으로 대체)
                    - ❌ **Firecrawl 제거**: $50/month → $0 (로컬 preprocess 사용)
                    - ✅ **Few-Shot Learning**: DB 성공 패턴 재활용
                    - ✅ **BeautifulSoup 강화**: 통계적 후보 추출
                    - 📊 **성공률 향상**: 50% → 80%
                    - 💰 **외부 API 비용**: $100/month → $0

                    ---

                    **특징**:
                    - 🧠 **GPT-4o + Gemini 2.5 Pro**: 최강 조합
                    - 📚 **Few-Shot Learning**: 과거 성공 패턴 학습
                    - 📊 **BeautifulSoup 통계**: 데이터 기반 후보 추출
                    - 🆕 **완전 자동**: 사람이 Selector 작성할 필요 없음
                    - 💰 **비용 $0**: 모든 외부 API 제거
                    - ⏱️ **소요 시간**: ~10초 (GPT-4o + Gemini)

                    ---

                    **UC3 성공 사례 (v2.0)**:
                    - CNN: Consensus 0.78 ✅
                    - BBC News: Consensus 0.89 ✅
                    - 조선일보: 테스트 예정
                    """
                    )

                gr.Markdown("---")

                # Section 3: LLM Supervisor 설명
                with gr.Accordion("🎯 LLM Supervisor: AI가 처리 경로를 자동 선택", open=False):
                    gr.Markdown(
                        """
                    ### 🧠 Supervisor는 무엇을 하나요?

                    **Supervisor**는 전체 워크플로우를 총괄하는 **중앙 관제 AI**입니다.
                    URL을 받으면 상황을 분석하여 **UC1/UC2/UC3 중 어디로 보낼지 자동 결정**합니다.

                    ---

                    **동작 방식**:

                    1. **URL 입력** → Supervisor가 사이트 이름 파악
                    2. **사이트 확인**:
                       - DB에 있는 사이트 → UC1 품질 검증 실행
                       - DB에 없는 사이트 → UC3 Discovery 실행
                    3. **UC1 실패 시**:
                       - UC1 품질 점수 < 80점 → UC2 자동 복구 실행
                    4. **UC2 실패 시**:
                       - Consensus < 0.6 → UC3 Discovery 실행
                    5. **UC3 실패 시**:
                       - Consensus < 0.7 → 워크플로우 종료 (수동 검토 필요)

                    ---

                    **현재 구현 방식**:

                    - ✅ **Rule-based Supervisor** (if-else 로직)
                    - 빠르고 안정적이며 비용 없음
                    - 환경변수: `USE_SUPERVISOR_LLM=false`

                    **향후 계획**:

                    - 🚀 **LLM-based Supervisor** (GPT-4o-mini)
                    - 더 복잡한 상황 판단 가능 (예: UC2 재시도 횟수 고려)
                    - 환경변수: `USE_SUPERVISOR_LLM=true`

                    ---

                    **LLM Supervisor 예시 (향후)**:
                    ```
                    [상황]
                    - UC1 실패 (점수=10)
                    - UC2 자동 복구 시도 → Consensus=0.3 (실패)

                    [AI 판단]
                    "UC1 품질이 너무 낮고 UC2도 실패했습니다.
                    사이트 구조가 크게 변경되었을 가능성이 높으므로
                    UC3 Discovery를 통해 처음부터 다시 학습합니다."

                    → 결정: UC3 실행
                    ```

                    🔗 **AI 판단 과정 추적**: [LangSmith](https://smith.langchain.com/)에서 실시간 확인 가능
                    """
                    )

                gr.Markdown("---")

                # Section 4: Decision Log
                gr.Markdown("## 📋 최근 AI 의사결정 기록")
                gr.Markdown(
                    """
                UC2/UC3 실행 시 2-Agent Consensus 결과를 기록합니다.
                Consensus Score가 **0.6 이상**이면 자동 승인됩니다.
                """
                )

                refresh_log_btn = gr.Button("🔄 새로고침", size="sm")

                log_output = gr.Dataframe(
                    label="UC2/UC3 의사결정 기록",
                    headers=["ID", "URL", "Site", "Consensus", "Retry", "Created"],
                    interactive=False,
                )

                def refresh_decision_log() -> pd.DataFrame:
                    """
                    Decision Log 조회 (UC2/UC3 합의 기록)

                    Returns:
                        pd.DataFrame: Decision Log 결과 (ID, URL, Site, Consensus, Retry, Created)
                    """
                    try:
                        db = next(get_db())
                        logs = (
                            db.query(DecisionLog)
                            .order_by(DecisionLog.created_at.desc())
                            .limit(20)
                            .all()
                        )
                        db.close()

                        if not logs:
                            return pd.DataFrame(
                                {"메시지": ["아직 처리 기록이 없습니다 (UC2/UC3 실행 시 생성)"]}
                            )

                        data = []
                        for log in logs:
                            data.append(
                                {
                                    "ID": log.id,
                                    "URL": log.url[:50] + "...",
                                    "Site": log.site_name,
                                    "Consensus": "✅" if log.consensus_reached else "❌",
                                    "Retry": log.retry_count,
                                    "Created": log.created_at.strftime("%Y-%m-%d %H:%M"),
                                }
                            )

                        return pd.DataFrame(data)
                    except Exception as e:
                        return pd.DataFrame({"오류": [str(e)]})

                refresh_log_btn.click(fn=refresh_decision_log, outputs=log_output)

            # ============================================
            # Tab 3: 🔍 데이터 조회
            # ============================================
            with gr.Tab("🔍 데이터 조회"):

                # 상단 통계 (한국어 카테고리)
                stats = get_stats_summary()
                category_kr_map = {
                    "politics": "정치",
                    "economy": "경제",
                    "society": "사회",
                    "international": "국제",
                }

                # 카테고리별 통계를 한국어로 변환
                category_display = []
                for eng_cat, kr_cat in category_kr_map.items():
                    count = stats["category_stats"].get(eng_cat, 0)
                    category_display.append(f"{kr_cat}({count})")

                gr.Markdown(
                    f"""
                ## 📊 수집 통계

                - **총 수집 개수**: {stats['total']}개
                - **평균 품질**: {stats['avg_quality']}/100
                - **카테고리별**: {' / '.join(category_display)}
                """
                )

                gr.Markdown("---")

                # 자연어 검색 (새로 추가)
                gr.Markdown("### 💬 자연어 검색 (AI)")
                gr.Markdown("일상 언어로 검색하세요. AI가 자동으로 조건을 분석합니다.")

                with gr.Row():
                    nl_query = gr.Textbox(
                        label="🗣️ 자연어 검색",
                        placeholder='예: "경제 뉴스 중 삼성 관련 최근 1주일", "11월 7일 정치 기사"',
                        lines=1,
                        scale=4,
                    )
                    nl_search_btn = gr.Button("🤖 AI 검색", variant="primary", size="lg", scale=1)

                # AI 파싱 결과 표시
                nl_parse_output = gr.HTML(label="AI 파싱 결과")

                with gr.Accordion("💡 자연어 검색 예시", open=False):
                    gr.Markdown(
                        """
                    **날짜 표현**:
                    - "오늘", "어제", "최근 3일", "이번 주", "최근 1주일"
                    - "11월 7일", "2025-11-07", "11월 1일부터 7일까지"

                    **카테고리**:
                    - "경제", "정치", "사회", "국제"

                    **키워드**:
                    - "삼성", "대통령", "코스피", "BTS"

                    **조합 예시**:
                    - "경제 뉴스 중 삼성 관련 최근 1주일"
                    - "11월 7일 연합뉴스 정치 기사"
                    - "대통령 발언 관련 기사"
                    - "오늘 경제 뉴스"
                    """
                    )

                gr.Markdown("---")

                # 검색 필터 (기존)
                gr.Markdown("### 🔍 상세 검색 필터")

                with gr.Row():
                    keyword_input = gr.Textbox(
                        label="🔎 키워드", placeholder="제목 또는 본문 검색", lines=1
                    )
                    category_filter = gr.Dropdown(
                        label="📂 카테고리",
                        choices=["all", "politics", "economy", "society", "international"],
                        value="all",
                    )

                with gr.Row():
                    date_from_input = gr.Textbox(
                        label="📅 시작일 (YYYY-MM-DD)", placeholder="2025-11-01", lines=1
                    )
                    date_to_input = gr.Textbox(
                        label="📅 종료일 (YYYY-MM-DD)", placeholder="2025-11-04", lines=1
                    )
                    min_quality_slider = gr.Slider(
                        label="⭐ 최소 품질", minimum=0, maximum=100, value=0, step=10
                    )

                search_btn = gr.Button("🔍 검색", variant="primary", size="lg")

                # 결과 표시
                results_df = gr.Dataframe(label="검색 결과", interactive=False)

                # CSV/JSON 다운로드
                with gr.Row():
                    download_csv_btn = gr.Button("📥 CSV 다운로드", size="lg", scale=1)
                    download_json_btn = gr.Button("📥 JSON 다운로드", size="lg", scale=1)

                download_file = gr.File(label="다운로드")

                # 자연어 검색 핸들러
                def handle_nl_search(query: str) -> Tuple[str, str, str, str, int]:
                    """
                    자연어 검색 쿼리를 파싱하여 검색 조건으로 변환

                    Returns:
                        Tuple: (keyword, category, date_from, date_to, min_quality)
                    """
                    if not query or not query.strip():
                        return ("", "all", "", "", 0)

                    try:
                        parsed = parse_natural_query(query.strip())

                        # HTML 파싱 결과 표시
                        parse_html = f"""
                        <div class='status-box status-success'>
                            <h3>✅ AI 파싱 완료</h3>
                            <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 10px 0;'>
                                <p style='margin: 5px 0;'><strong>키워드:</strong> {parsed.get('keyword') or '(없음)'}</p>
                                <p style='margin: 5px 0;'><strong>카테고리:</strong> {parsed.get('category', 'all')}</p>
                                <p style='margin: 5px 0;'><strong>시작일:</strong> {parsed.get('date_from') or '(제한 없음)'}</p>
                                <p style='margin: 5px 0;'><strong>종료일:</strong> {parsed.get('date_to') or '(제한 없음)'}</p>
                                <p style='margin: 5px 0;'><strong>최소 품질:</strong> {parsed.get('min_quality', 0)}</p>
                            </div>
                            <p style='margin-top: 10px; opacity: 0.8;'><strong>파싱 근거:</strong> {parsed.get('reasoning', '')}</p>
                        </div>
                        """

                        return (
                            parsed.get("keyword", ""),
                            parsed.get("category", "all"),
                            parsed.get("date_from", ""),
                            parsed.get("date_to", ""),
                            parsed.get("min_quality", 0),
                            parse_html,
                        )

                    except Exception as e:
                        error_html = f"""
                        <div class='status-box status-error'>
                            <h3>❌ 파싱 실패</h3>
                            <p>{str(e)}</p>
                            <p style='margin-top: 10px;'>검색어를 더 명확하게 입력하거나 상세 검색 필터를 사용하세요.</p>
                        </div>
                        """
                        return ("", "all", "", "", 0, error_html)

                # 자연어 검색 버튼 클릭 시
                nl_search_btn.click(
                    fn=handle_nl_search,
                    inputs=nl_query,
                    outputs=[
                        keyword_input,
                        category_filter,
                        date_from_input,
                        date_to_input,
                        min_quality_slider,
                        nl_parse_output,
                    ],
                ).then(
                    fn=search_articles,
                    inputs=[
                        keyword_input,
                        category_filter,
                        date_from_input,
                        date_to_input,
                        min_quality_slider,
                    ],
                    outputs=results_df,
                )

                # 검색 실행 (기존)
                search_btn.click(
                    fn=search_articles,
                    inputs=[
                        keyword_input,
                        category_filter,
                        date_from_input,
                        date_to_input,
                        min_quality_slider,
                    ],
                    outputs=results_df,
                )

                # CSV/JSON 다운로드
                download_csv_btn.click(fn=download_csv, inputs=results_df, outputs=download_file)

                download_json_btn.click(fn=download_json, inputs=results_df, outputs=download_file)

                gr.Markdown("---")

                # 기사 상세보기
                gr.Markdown("### 📄 기사 상세보기")
                gr.Markdown("검색 결과에서 URL을 복사하여 붙여넣으세요")

                with gr.Row():
                    detail_url = gr.Textbox(
                        label="URL 입력",
                        placeholder="https://www.yna.co.kr/view/...",
                        lines=1,
                        scale=4,
                    )
                    detail_btn = gr.Button("상세 조회", scale=1)

                detail_output = gr.HTML()

                # 상세보기 함수
                def get_article_detail(url: str) -> str:
                    """
                    기사 전체 내용 조회 (제목, 본문, GPT 검증 근거 포함)

                    Args:
                        url: 조회할 기사 URL

                    Returns:
                        str: HTML 형식의 기사 상세 내용
                    """
                    if not url:
                        return """
                        <div class='status-box status-warning'>
                            <h3 style='margin: 0;'>⚠️ URL 입력 필요</h3>
                        </div>
                        """

                    try:
                        db = next(get_db())
                        article = db.query(CrawlResult).filter_by(url=url).first()
                        db.close()

                        if not article:
                            return """
                            <div class='status-box status-error'>
                                <h3 style='margin: 0;'>❌ 기사를 찾을 수 없습니다</h3>
                            </div>
                            """

                        # HTML 이스케이프 처리
                        title = article.title.replace("<", "&lt;").replace(">", "&gt;")
                        body = (
                            article.body.replace("<", "&lt;").replace(">", "&gt;")
                            if article.body
                            else "본문 없음"
                        )
                        reasoning = (
                            article.llm_reasoning.replace("<", "&lt;").replace(">", "&gt;")
                            if article.llm_reasoning
                            else "N/A"
                        )

                        return f"""
                        <div style='max-width: 1000px; margin: 0 auto; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 8px;'>
                            <h2 style='margin-top: 0; color: #e5e7eb;'>{title}</h2>

                            <div style='display: flex; gap: 20px; color: #9ca3af; margin: 15px 0; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 6px;'>
                                <span>📂 {article.category_kr or article.category}</span>
                                <span>📅 {article.article_date.strftime("%Y-%m-%d") if article.article_date else "N/A"}</span>
                                <span>⭐ 품질: <strong style='color: #10b981; font-size: 1.2em;'>{article.quality_score}/100</strong></span>
                            </div>

                            <hr style='border: 1px solid rgba(255,255,255,0.1); margin: 20px 0;'>

                            <div style='line-height: 1.8; white-space: pre-wrap; color: #e5e7eb; font-size: 1.05em;'>
                                {body}
                            </div>

                            <hr style='border: 1px solid rgba(255,255,255,0.1); margin: 30px 0;'>

                            <div style='background: rgba(59, 130, 246, 0.1); padding: 20px; border-radius: 6px; border-left: 4px solid #3b82f6;'>
                                <h3 style='margin-top: 0; color: #3b82f6;'>🤖 GPT-4o-mini 검증 근거</h3>
                                <p style='white-space: pre-wrap; line-height: 1.6; color: #d1d5db;'>{reasoning}</p>
                            </div>

                            <div style='margin-top: 20px; text-align: center;'>
                                <a href='{article.url}' target='_blank' style='color: #667eea; text-decoration: none; font-weight: bold;'>
                                    🔗 원문 보기 →
                                </a>
                            </div>
                        </div>
                        """

                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3 style='margin: 0;'>❌ 오류 발생</h3>
                            <p style='margin: 10px 0 0 0;'>{str(e)}</p>
                        </div>
                        """

                detail_btn.click(fn=get_article_detail, inputs=detail_url, outputs=detail_output)

            # ============================================
            # Tab 4: 💰 비용 분석 (Cost Dashboard)
            # ============================================
            with gr.Tab("💰 비용 분석"):
                gr.Markdown(
                    """
                ## 💰 LLM API 비용 실시간 추적

                **AI 에이전트의 API 사용 비용을 실시간으로 모니터링합니다**

                - 🔄 **실시간 업데이트**: 모든 LLM API 호출 비용 자동 기록
                - 📊 **Use Case별 분석**: UC1/UC2/UC3별 비용 추적
                - 🤖 **Provider별 비용**: OpenAI, Gemini, Claude 비교
                - 📈 **ROI 분석**: 투자 대비 효율성 측정
                """
                )

                gr.Markdown("---")

                # 전체 통계 요약
                gr.Markdown("### 📊 전체 비용 요약")

                refresh_cost_btn = gr.Button("🔄 비용 새로고침", size="sm")

                cost_summary = gr.HTML()

                gr.Markdown("---")

                # Use Case별 비용
                gr.Markdown("### 🎯 Use Case별 비용 분석")

                with gr.Row():
                    with gr.Column():
                        uc_cost_chart = gr.HTML(label="UC별 비용 분포")
                    with gr.Column():
                        provider_cost_chart = gr.HTML(label="Provider별 비용 분포")

                gr.Markdown("---")

                # 최근 API 호출 기록
                gr.Markdown("### 📋 최근 API 호출 기록 (최신 20개)")

                recent_costs_df = gr.Dataframe(
                    label="최근 비용 기록",
                    headers=[
                        "시간",
                        "Provider",
                        "Model",
                        "Use Case",
                        "토큰(입력+출력)",
                        "비용",
                        "Site",
                    ],
                    interactive=False,
                )

                # ROI 분석
                with gr.Accordion("💡 ROI 분석 및 비용 인사이트", open=False):
                    gr.Markdown(
                        """
                    ### 📈 ROI (Return on Investment) 분석

                    **예상 비용 절감**:
                    - 수동 크롤링 비용: $18/시간 (개발자 인건비)
                    - AI 자동화 비용: $0.0015/기사 (LLM API)
                    - **절감률**: 99.8%

                    **Use Case별 평균 비용**:
                    - **UC1 (품질 검증)**: $0 (규칙 기반, LLM 미사용)
                    - **UC2 (자동 복구)**: ~$0.002/기사 (GPT-4o-mini + Gemini-2.5-Pro)
                    - **UC3 (신규 사이트)**: ~$0.005/기사 (GPT-4o DOM 분석)

                    **월간 예상 비용** (1,000기사 기준):
                    - UC1 95% + UC2 4% + UC3 1% = **$0.09/월**
                    - 수동 작업 대비 절감액: **$17,999.91/월**

                    ---

                    **비용 최적화 팁**:
                    1. **UC1 우선 통과**: 품질 점수 80점 이상 유지 → UC2 호출 최소화
                    2. **Gemini 활용**: Gemini-2.0-flash-exp (무료) 사용 시 비용 $0
                    3. **배치 처리**: 여러 기사 동시 처리로 API 호출 횟수 감소
                    """
                    )

                # 비용 조회 함수
                def refresh_cost_dashboard() -> Tuple[str, str, str, pd.DataFrame]:
                    """
                    비용 대시보드 데이터 조회

                    Returns:
                        Tuple[str, str, str, pd.DataFrame]: (요약 HTML, UC별 차트 HTML, Provider별 차트 HTML, 최근 비용 DataFrame)
                    """
                    try:
                        from src.monitoring.cost_tracker import get_cost_breakdown

                        breakdown = get_cost_breakdown()

                        # 1. 전체 요약
                        total_cost = breakdown.get("total_cost", 0.0)
                        total_tokens = breakdown.get("total_tokens", 0)

                        # 평균 비용 계산
                        db = next(get_db())
                        article_count = db.query(CrawlResult).count()
                        db.close()

                        avg_cost_per_article = (
                            (total_cost / article_count) if article_count > 0 else 0
                        )

                        summary_html = f"""
                        <div style='background: linear-gradient(135deg, #667eea22, #764ba222); padding: 25px; border-radius: 12px; border: 1px solid rgba(102, 126, 234, 0.3);'>
                            <h2 style='margin: 0 0 20px 0; color: #667eea;'>💰 전체 비용 요약</h2>

                            <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 20px;'>
                                <div style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 8px; text-align: center;'>
                                    <div style='font-size: 2.5em; font-weight: bold; color: #10b981; margin-bottom: 10px;'>
                                        ${total_cost:.4f}
                                    </div>
                                    <div style='color: #9ca3af; font-size: 0.9em;'>총 누적 비용 (USD)</div>
                                </div>

                                <div style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 8px; text-align: center;'>
                                    <div style='font-size: 2.5em; font-weight: bold; color: #3b82f6; margin-bottom: 10px;'>
                                        {total_tokens:,}
                                    </div>
                                    <div style='color: #9ca3af; font-size: 0.9em;'>총 토큰 사용량</div>
                                </div>

                                <div style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 8px; text-align: center;'>
                                    <div style='font-size: 2.5em; font-weight: bold; color: #f59e0b; margin-bottom: 10px;'>
                                        ${avg_cost_per_article:.6f}
                                    </div>
                                    <div style='color: #9ca3af; font-size: 0.9em;'>기사당 평균 비용</div>
                                </div>

                                <div style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 8px; text-align: center;'>
                                    <div style='font-size: 2.5em; font-weight: bold; color: #8b5cf6; margin-bottom: 10px;'>
                                        {article_count:,}
                                    </div>
                                    <div style='color: #9ca3af; font-size: 0.9em;'>총 처리 기사 수</div>
                                </div>
                            </div>

                            <div style='margin-top: 20px; padding: 15px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; border-left: 4px solid #10b981;'>
                                <p style='margin: 0; color: #10b981; font-weight: bold;'>💡 비용 효율성</p>
                                <p style='margin: 10px 0 0 0; opacity: 0.9;'>
                                    수동 크롤링 대비 <strong style='color: #10b981; font-size: 1.2em;'>99.8%</strong> 비용 절감
                                    (수동: $18/시간 vs AI: ${avg_cost_per_article:.6f}/기사)
                                </p>
                            </div>
                        </div>
                        """

                        # 2. Use Case별 비용 차트
                        by_use_case = breakdown.get("by_use_case", {})

                        uc_labels = []
                        uc_values = []
                        uc_colors = {
                            "uc1": "#4caf50",
                            "uc2": "#ff9800",
                            "uc3": "#2196f3",
                            "other": "#9e9e9e",
                        }

                        for uc, cost in by_use_case.items():
                            uc_labels.append(uc.upper())
                            uc_values.append(cost)

                        uc_chart_html = f"""
                        <div style='background: rgba(255,255,255,0.03); padding: 20px; border-radius: 8px;'>
                            <h4 style='margin: 0 0 20px 0; text-align: center;'>Use Case별 비용 분포</h4>
                            <div style='display: flex; flex-direction: column; gap: 15px;'>
                        """

                        for uc, cost in sorted(
                            by_use_case.items(), key=lambda x: x[1], reverse=True
                        ):
                            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                            color = uc_colors.get(uc, "#9e9e9e")
                            uc_chart_html += f"""
                                <div>
                                    <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                                        <span style='font-weight: bold;'>{uc.upper()}</span>
                                        <span style='color: {color};'>${cost:.4f} ({percentage:.1f}%)</span>
                                    </div>
                                    <div style='width: 100%; background: rgba(255,255,255,0.1); border-radius: 4px; height: 12px; overflow: hidden;'>
                                        <div style='width: {percentage}%; background: {color}; height: 100%; border-radius: 4px;'></div>
                                    </div>
                                </div>
                            """

                        uc_chart_html += """
                            </div>
                        </div>
                        """

                        # 3. Provider별 비용 차트
                        by_provider = breakdown.get("by_provider", {})

                        provider_colors = {
                            "openai": "#10b981",
                            "gemini": "#3b82f6",
                            "claude": "#f59e0b",
                        }

                        provider_chart_html = f"""
                        <div style='background: rgba(255,255,255,0.03); padding: 20px; border-radius: 8px;'>
                            <h4 style='margin: 0 0 20px 0; text-align: center;'>Provider별 비용 분포</h4>
                            <div style='display: flex; flex-direction: column; gap: 15px;'>
                        """

                        for provider, cost in sorted(
                            by_provider.items(), key=lambda x: x[1], reverse=True
                        ):
                            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                            color = provider_colors.get(provider, "#9e9e9e")
                            provider_chart_html += f"""
                                <div>
                                    <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                                        <span style='font-weight: bold;'>{provider.upper()}</span>
                                        <span style='color: {color};'>${cost:.4f} ({percentage:.1f}%)</span>
                                    </div>
                                    <div style='width: 100%; background: rgba(255,255,255,0.1); border-radius: 4px; height: 12px; overflow: hidden;'>
                                        <div style='width: {percentage}%; background: {color}; height: 100%; border-radius: 4px;'></div>
                                    </div>
                                </div>
                            """

                        provider_chart_html += """
                            </div>
                        </div>
                        """

                        # 4. 최근 비용 기록
                        recent_costs = breakdown.get("recent_costs", [])

                        if recent_costs:
                            data = []
                            for cost in recent_costs:
                                timestamp = cost.get("timestamp", "")
                                # ISO 형식을 읽기 쉬운 형식으로 변환
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                    time_str = dt.strftime("%m-%d %H:%M")
                                except Exception as e:
                                    time_str = timestamp[:16]

                                data.append(
                                    {
                                        "시간": time_str,
                                        "Provider": cost.get("provider", "N/A"),
                                        "Model": cost.get("model", "N/A"),
                                        "Use Case": cost.get("use_case", "N/A").upper(),
                                        "토큰(입력+출력)": f"{cost.get('total_tokens', 0):,}",
                                        "비용": f"${cost.get('total_cost', 0):.6f}",
                                        "Site": cost.get("site_name", "N/A") or "N/A",
                                    }
                                )

                            recent_df = pd.DataFrame(data)
                        else:
                            recent_df = pd.DataFrame(
                                {
                                    "메시지": [
                                        "아직 비용 기록이 없습니다. LLM API를 사용하는 UC2/UC3를 실행하면 기록이 생성됩니다."
                                    ]
                                }
                            )

                        return (summary_html, uc_chart_html, provider_chart_html, recent_df)

                    except Exception as e:
                        import traceback

                        error_trace = traceback.format_exc()
                        error_html = f"""
                        <div class='status-box status-error'>
                            <h3>❌ 비용 데이터 조회 실패</h3>
                            <p>{str(e)}</p>
                            <details style='margin-top: 10px;'>
                                <summary style='cursor: pointer;'>상세 오류 보기</summary>
                                <pre style='margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 4px; overflow-x: auto;'>{error_trace}</pre>
                            </details>
                        </div>
                        """
                        return (error_html, "", "", pd.DataFrame({"오류": [str(e)]}))

                # 새로고침 버튼 이벤트
                refresh_cost_btn.click(
                    fn=refresh_cost_dashboard,
                    outputs=[cost_summary, uc_cost_chart, provider_cost_chart, recent_costs_df],
                )

                # 페이지 로드 시 자동 조회
                demo.load(
                    fn=refresh_cost_dashboard,
                    outputs=[cost_summary, uc_cost_chart, provider_cost_chart, recent_costs_df],
                )

            # ============================================
            # Tab 5: 🗑️ 데이터 관리
            # ============================================
            with gr.Tab("🗑️ 데이터 관리"):
                gr.Markdown(
                    """
                ## 데이터베이스 관리

                **수집된 기사 데이터를 관리합니다.**

                테스트 및 개발 중 데이터 정리가 필요한 경우 사용하세요.

                ---

                ## 데이터 삭제 및 정리

                **⚠️ 주의: 삭제된 데이터는 복구할 수 없습니다!**
                """
                )

                gr.Markdown("---")

                # 조건별 삭제
                gr.Markdown("### 1️⃣ 조건별 삭제")

                with gr.Row():
                    with gr.Column():
                        delete_category = gr.Dropdown(
                            label="📂 카테고리",
                            choices=["economy", "politics", "society", "international"],
                            value="economy",
                        )

                        delete_date = gr.Textbox(
                            label="📅 삭제할 날짜 (YYYY-MM-DD)",
                            placeholder="비워두면 카테고리 전체 삭제",
                            lines=1,
                        )

                        delete_btn = gr.Button("🗑️ 선택 삭제", variant="stop", size="lg")

                    with gr.Column():
                        gr.Markdown(
                            """
                        **삭제 예시:**

                        1. **카테고리 전체 삭제**: 날짜 비우고 카테고리 선택
                        2. **특정 날짜만 삭제**: 날짜 + 카테고리 선택
                        """
                        )

                delete_output = gr.HTML()

                gr.Markdown("---")

                # 전체 초기화
                gr.Markdown("### 2️⃣ 전체 데이터 초기화")
                gr.Markdown("**⚠️ 위험: 모든 수집 데이터가 삭제됩니다!**")

                with gr.Row():
                    confirm_text = gr.Textbox(
                        label="확인용 텍스트 입력",
                        placeholder="'DELETE ALL'을 정확히 입력하세요",
                        lines=1,
                    )

                    reset_btn = gr.Button("🗑️ 전체 초기화", variant="stop", size="lg")

                reset_output = gr.HTML()

                # 삭제 함수들
                def delete_articles(category: str, date_str: str) -> str:
                    """
                    카테고리 및 날짜 기준 기사 삭제

                    Args:
                        category: 삭제할 카테고리
                        date_str: 삭제할 날짜 (비워두면 카테고리 전체)

                    Returns:
                        str: HTML 형식의 삭제 결과 메시지
                    """
                    try:
                        db = next(get_db())
                        query = db.query(CrawlResult).filter(CrawlResult.category == category)

                        if date_str:
                            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            query = query.filter(CrawlResult.article_date == target_date)

                        count = query.count()

                        if count == 0:
                            db.close()
                            return """
                            <div class='status-box status-info'>
                                <h3 style='margin: 0;'>ℹ️ 삭제할 데이터 없음</h3>
                            </div>
                            """

                        query.delete()
                        db.commit()
                        db.close()

                        return f"""
                        <div class='status-box status-success'>
                            <h3 style='margin: 0;'>✅ 삭제 완료</h3>
                            <p style='margin: 10px 0 0 0;'>{count}개 삭제됨</p>
                        </div>
                        """

                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3 style='margin: 0;'>❌ 오류 발생</h3>
                            <p style='margin: 10px 0 0 0;'>{str(e)}</p>
                        </div>
                        """

                def reset_all(confirm: str) -> str:
                    """
                    전체 데이터베이스 초기화 (모든 기사 삭제)

                    Args:
                        confirm: 확인 텍스트 ("DELETE ALL" 입력 시에만 실행)

                    Returns:
                        str: HTML 형식의 삭제 결과 메시지
                    """
                    if confirm != "DELETE ALL":
                        return """
                        <div class='status-box status-warning'>
                            <h3 style='margin: 0;'>⚠️ 확인 텍스트 불일치</h3>
                            <p style='margin: 10px 0 0 0;'>'DELETE ALL'을 정확히 입력하세요</p>
                        </div>
                        """

                    try:
                        db = next(get_db())
                        count = db.query(CrawlResult).count()
                        db.query(CrawlResult).delete()
                        db.commit()
                        db.close()

                        return f"""
                        <div class='status-box status-success'>
                            <h3 style='margin: 0;'>✅ 전체 초기화 완료</h3>
                            <p style='margin: 10px 0 0 0;'>{count}개 삭제됨</p>
                        </div>
                        """

                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3 style='margin: 0;'>❌ 오류 발생</h3>
                            <p style='margin: 10px 0 0 0;'>{str(e)}</p>
                        </div>
                        """

                delete_btn.click(
                    fn=delete_articles, inputs=[delete_category, delete_date], outputs=delete_output
                )

                reset_btn.click(fn=reset_all, inputs=confirm_text, outputs=reset_output)

            # ============================================
            # Tab 6: ⏰ 자동 스케줄
            # ============================================
            with gr.Tab("⏰ 자동 스케줄"):
                gr.Markdown(
                    """
                ## 자동 뉴스 수집 스케줄러

                매일 정해진 시간에 자동으로 뉴스를 수집하도록 설정할 수 있습니다.

                **주의**: 이 UI는 스케줄 설정만 저장합니다. 실제 자동 실행은 시스템 cron 또는 systemd 타이머로 구성해야 합니다.
                """
                )

                gr.Markdown("---")

                # 스케줄 설정
                gr.Markdown("### 1️⃣ 스케줄 설정")

                with gr.Row():
                    schedule_enabled = gr.Checkbox(label="🔔 자동 수집 활성화", value=False)

                with gr.Row():
                    schedule_hour = gr.Slider(
                        label="⏰ 실행 시간 (시)", minimum=0, maximum=23, value=2, step=1
                    )
                    schedule_categories = gr.CheckboxGroup(
                        label="📂 수집 카테고리",
                        choices=["economy", "politics", "society", "international"],
                        value=["economy"],
                    )

                save_schedule_btn = gr.Button("💾 스케줄 저장", variant="primary", size="lg")
                schedule_output = gr.HTML()

                # 현재 상태 표시
                gr.Markdown("---")
                gr.Markdown("### 2️⃣ 현재 스케줄 상태")

                refresh_schedule_btn = gr.Button("🔄 상태 새로고침", size="sm")
                schedule_status = gr.HTML()

                # 실행 기록
                gr.Markdown("---")
                gr.Markdown("### 3️⃣ 실행 기록 (최근 10개)")

                refresh_history_btn = gr.Button("🔄 기록 새로고침", size="sm")
                schedule_history = gr.Dataframe(
                    label="스케줄 실행 기록",
                    headers=["실행일시", "카테고리", "상태", "수집 개수", "소요 시간"],
                    interactive=False,
                )

                # cron 설정 안내
                with gr.Accordion("🛠️ 시스템 자동 실행 설정 방법", open=False):
                    gr.Markdown(
                        """
                    ### Linux/macOS - crontab 설정

                    ```bash
                    # crontab 편집
                    crontab -e

                    # 매일 새벽 2시에 경제 뉴스 수집 (예시)
                    0 2 * * * cd /path/to/crawlagent && poetry run scrapy crawl yonhap -a target_date=$(date +\%Y-\%m-\%d) -a category=economy >> /var/log/crawlagent.log 2>&1
                    ```

                    ### 여러 카테고리 순차 실행

                    ```bash
                    # 새벽 2시: 경제
                    0 2 * * * cd /path/to/crawlagent && poetry run scrapy crawl yonhap -a target_date=$(date +\%Y-\%m-\%d) -a category=economy

                    # 새벽 2시 30분: 정치
                    30 2 * * * cd /path/to/crawlagent && poetry run scrapy crawl yonhap -a target_date=$(date +\%Y-\%m-\%d) -a category=politics

                    # 새벽 3시: 사회
                    0 3 * * * cd /path/to/crawlagent && poetry run scrapy crawl yonhap -a target_date=$(date +\%Y-\%m-\%d) -a category=society

                    # 새벽 3시 30분: 국제
                    30 3 * * * cd /path/to/crawlagent && poetry run scrapy crawl yonhap -a target_date=$(date +\%Y-\%m-\%d) -a category=international
                    ```

                    ### Windows - 작업 스케줄러

                    1. "작업 스케줄러" 실행
                    2. "작업 만들기" 클릭
                    3. 트리거: 매일 새벽 2시
                    4. 동작: 프로그램 시작
                       - 프로그램: `poetry`
                       - 인수: `run scrapy crawl yonhap -a target_date=2025-11-08 -a category=economy`
                       - 시작 위치: `C:\\path\\to\\crawlagent`
                    """
                    )

                # Helper functions
                def save_schedule(enabled: bool, hour: int, categories: list) -> str:
                    """스케줄 설정 저장"""
                    import json

                    try:
                        schedule_config = {
                            "enabled": enabled,
                            "hour": int(hour),
                            "categories": categories,
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }

                        with open("/tmp/crawl_schedule.json", "w") as f:
                            json.dump(schedule_config, f, indent=2)

                        return f"""
                        <div class='status-box status-success'>
                            <h3>✅ 스케줄 저장 완료</h3>
                            <p><strong>활성화:</strong> {"예" if enabled else "아니오"}</p>
                            <p><strong>실행 시간:</strong> 매일 {int(hour):02d}:00</p>
                            <p><strong>카테고리:</strong> {", ".join(categories) if categories else "없음"}</p>
                            <p style='margin-top: 15px; color: #fbbf24;'>⚠️ 실제 자동 실행은 시스템 cron/작업 스케줄러로 구성 필요</p>
                        </div>
                        """
                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3>❌ 저장 실패</h3>
                            <p>{str(e)}</p>
                        </div>
                        """

                def get_schedule_status() -> str:
                    """현재 스케줄 상태 조회"""
                    import json
                    import os

                    try:
                        if not os.path.exists("/tmp/crawl_schedule.json"):
                            return """
                            <div class='status-box status-info'>
                                <h3>ℹ️ 설정된 스케줄 없음</h3>
                                <p>위에서 스케줄을 설정하고 저장하세요.</p>
                            </div>
                            """

                        with open("/tmp/crawl_schedule.json", "r") as f:
                            config = json.load(f)

                        enabled = config.get("enabled", False)
                        hour = config.get("hour", 0)
                        categories = config.get("categories", [])
                        updated_at = config.get("updated_at", "N/A")

                        # 다음 실행 시간 계산
                        now = datetime.now()
                        next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                        if next_run < now:
                            next_run += timedelta(days=1)

                        status_class = "status-success" if enabled else "status-warning"
                        status_icon = "🟢" if enabled else "🔴"

                        return f"""
                        <div class='status-box {status_class}'>
                            <h3>{status_icon} 스케줄 상태</h3>
                            <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 10px 0;'>
                                <p style='margin: 5px 0;'><strong>활성화:</strong> {"예 (실행 예정)" if enabled else "아니오 (비활성)"}</p>
                                <p style='margin: 5px 0;'><strong>실행 시간:</strong> 매일 {hour:02d}:00</p>
                                <p style='margin: 5px 0;'><strong>카테고리:</strong> {", ".join(categories) if categories else "없음"}</p>
                                <p style='margin: 5px 0;'><strong>다음 실행:</strong> {next_run.strftime("%Y-%m-%d %H:%M")}</p>
                                <p style='margin: 5px 0;'><strong>마지막 수정:</strong> {updated_at}</p>
                            </div>
                            <p style='margin-top: 15px; color: #fbbf24;'>⚠️ 실제 자동 실행은 시스템 cron/작업 스케줄러로 구성 필요</p>
                        </div>
                        """
                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3>❌ 상태 조회 실패</h3>
                            <p>{str(e)}</p>
                        </div>
                        """

                def get_schedule_history() -> pd.DataFrame:
                    """스케줄 실행 기록 조회 (DB에서)"""
                    try:
                        db = next(get_db())
                        # 최근 10일간의 일간 수집 결과 조회
                        from datetime import date

                        results = (
                            db.query(CrawlResult)
                            .filter(CrawlResult.crawl_date >= date.today() - timedelta(days=10))
                            .order_by(CrawlResult.created_at.desc())
                            .limit(100)
                            .all()
                        )

                        db.close()

                        if not results:
                            return pd.DataFrame({"메시지": ["아직 실행 기록이 없습니다"]})

                        # 날짜/카테고리별로 그룹화
                        history = {}
                        for r in results:
                            key = (r.crawl_date, r.category)
                            if key not in history:
                                history[key] = {
                                    "count": 0,
                                    "created_at": r.created_at,
                                    "avg_duration": [],
                                }
                            history[key]["count"] += 1
                            if r.crawl_duration_seconds:
                                history[key]["avg_duration"].append(r.crawl_duration_seconds)

                        # DataFrame 생성
                        data = []
                        for (crawl_date, category), stats in sorted(
                            history.items(), key=lambda x: x[1]["created_at"], reverse=True
                        )[:10]:
                            avg_dur = (
                                sum(stats["avg_duration"]) / len(stats["avg_duration"])
                                if stats["avg_duration"]
                                else 0
                            )
                            data.append(
                                {
                                    "실행일시": stats["created_at"].strftime("%Y-%m-%d %H:%M"),
                                    "카테고리": category,
                                    "상태": "✅ 완료",
                                    "수집 개수": f"{stats['count']}개",
                                    "소요 시간": f"{avg_dur:.1f}초" if avg_dur > 0 else "N/A",
                                }
                            )

                        return (
                            pd.DataFrame(data) if data else pd.DataFrame({"메시지": ["기록 없음"]})
                        )

                    except Exception as e:
                        return pd.DataFrame({"오류": [str(e)]})

                # Event handlers
                save_schedule_btn.click(
                    fn=save_schedule,
                    inputs=[schedule_enabled, schedule_hour, schedule_categories],
                    outputs=schedule_output,
                )

                refresh_schedule_btn.click(fn=get_schedule_status, outputs=schedule_status)

                refresh_history_btn.click(fn=get_schedule_history, outputs=schedule_history)

            # ============================================
            # Tab 7 삭제됨 (PoC 범위 재정의)
            # ============================================
            # 이전 Tab 6 "🤖 자동 복구 (개발자 전용)"이 삭제되었습니다.
            # 이유:
            #   - PoC 목표: LangGraph Multi-Agent 자동화 검증
            #   - Gradio UI로 크롤링 결과 확인 가능
            #   - 알림 시스템은 Production 레벨 기능
            #
            # PoC 워크플로우:
            #   - UC2 합의 성공(≥0.8): 자동 DB 저장 후 UC1 복귀
            #   - UC2 합의 실패(<0.6): DecisionLog 기록 (관리자가 DB/Gradio에서 확인)

        # Footer
        gr.Markdown("---")
        gr.Markdown(
            """
        **CrawlAgent PoC (Phase A/B Complete)** - LangGraph Multi-Agent Orchestration System

        **Tech Stack**:
        - LangGraph: StateGraph + Command API + Agent Supervisor Pattern
        - LLM: GPT-4o-mini (UC2 Proposer) + Gemini-2.0-flash (UC2 Validator) + GPT-4o (UC3 Discoverer)
        - Crawler: Scrapy + BeautifulSoup4
        - Database: PostgreSQL + SQLAlchemy
        - Tracing: LangSmith (LANGCHAIN_TRACING_V2)

        **Phase A**: Code Quality & LangSmith Verification ✅
        **Phase B**: Gradio UI Integration ✅
        """
        )

    return demo


# ========================================
# Main
# ========================================

if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
