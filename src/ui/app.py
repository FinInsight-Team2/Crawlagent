"""
CrawlAgent - LangGraph Multi-Agent Orchestration System
Created: 2025-11-04
Updated: 2025-11-10 (Phase A/B Complete)

목적:
1. LangGraph 기반 통합 Master Graph 오케스트레이션
2. UC1 품질 검증 (규칙 기반, LLM 없음)
3. UC2 Self-Healing (GPT-4o-mini + Gemini-2.0-flash 2-Agent Consensus)
4. UC3 신규 사이트 Discovery (GPT-4o)
5. Gradio UI에서 3가지 시나리오 독립 테스트 가능

Phase A 완료:
- Claude → GPT 네이밍 리팩토링
- LLM 역할 명확화
- LangSmith 트레이싱 검증
- Phase A 검증 보고서 작성

Phase B 완료:
- Gradio UI Master Graph 테스트 탭 추가
- 개발자 모드 제거 및 UI 최적화
"""

import sys
sys.path.insert(0, '.')

import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple
import subprocess
import os
import json

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector, DecisionLog
from src.agents.uc1_quality_gate import validate_quality
from src.agents.nlp_search import parse_natural_query
from src.ui.theme import CrawlAgentDarkTheme, get_custom_css
from src.ui.components.langgraph_viz import create_langgraph_figure, get_state_description
from src.workflow.master_crawl_workflow import build_master_graph
import requests
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
    limit: int = 100
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
                (CrawlResult.title.contains(keyword)) |
                (CrawlResult.body.contains(keyword))
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

            data.append({
                "제목": r.title[:80] + "..." if len(r.title) > 80 else r.title,
                "본문 미리보기": body_preview,
                "카테고리": r.category_kr or r.category,
                "발행일": r.article_date.strftime("%Y-%m-%d") if r.article_date else "N/A",
                "품질": f"{r.quality_score}/100",
                "수집일시": r.created_at.strftime("%Y-%m-%d %H:%M"),
                "URL": r.url
            })

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
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8-sig')
    df.to_csv(temp_file.name, index=False)
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
            avg_quality_result = db.query(CrawlResult).with_entities(
                CrawlResult.quality_score
            ).all()
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
            "category_stats": category_stats
        }
    except Exception as e:
        return {"total": 0, "avg_quality": 0, "category_stats": {}}


# ========================================
# Gradio UI 생성
# ========================================

def create_app():
    """Gradio 앱 생성"""

    theme = CrawlAgentDarkTheme()

    with gr.Blocks(
        title="CrawlAgent - 지능형 뉴스 수집 시스템",
        theme=theme,
        css=get_custom_css()
    ) as demo:

        # ============================================
        # 헤더
        # ============================================
        gr.Markdown("""
        # 🕷️ CrawlAgent - LangGraph 멀티 에이전트 오케스트레이션

        **Phase A/B 완료**: 통합 Master Graph 기반 자율 크롤링 시스템

        - ✅ **UC1 품질 검증**: 규칙 기반 품질 평가 (~100ms)
        - ✅ **UC2 Self-Healing**: GPT-4o-mini + Gemini-2.0-flash 2-Agent Consensus
        - ✅ **UC3 신규 사이트**: GPT-4o 기반 자동 Selector Discovery
        - 🎯 **Master Graph 테스트**: 3가지 시나리오 독립 테스트 가능
        """)

        gr.Markdown("---")

        with gr.Tabs():

            # ============================================
            # Tab 1: 🚀 콘텐츠 수집
            # ============================================
            with gr.Tab("🚀 콘텐츠 수집"):
                gr.Markdown("""
                ## 웹 콘텐츠 자동 수집

                두 가지 수집 방식을 지원합니다:
                - **실시간 크롤링**: URL 1개 입력 → 즉시 수집 (시연용)
                - **배치 수집**: 날짜 + 카테고리 → 대량 수집 (실용)
                """)

                gr.Markdown("---")

                # 테스트 크롤링
                gr.Markdown("### 1️⃣ 테스트 크롤링 (단일 URL)")
                gr.Markdown("GPT-4o-mini가 콘텐츠 품질을 실시간으로 검증합니다 (5W1H 기반 점수 계산)")

                # URL 입력
                single_url = gr.Textbox(
                    label="📎 기사 URL",
                    placeholder="예: https://www.yna.co.kr/view/AKR20251104...",
                    lines=2
                )

                # 카테고리 및 실행 버튼
                with gr.Row():
                    single_category = gr.Dropdown(
                        label="📂 카테고리",
                        choices=["politics", "economy", "society", "international"],
                        value="economy",
                        scale=2
                    )
                    single_crawl_btn = gr.Button("🚀 지금 크롤링", variant="primary", size="lg", scale=1)

                # 사용 가이드 (접을 수 있음)
                with gr.Accordion("📖 사용 가이드", open=False):
                    gr.Markdown("""
                    **테스트 크롤링 사용법**
                    1. 연합뉴스 기사 URL 입력
                    2. 카테고리 선택 (경제/정치/사회/국제)
                    3. "지금 크롤링" 버튼 클릭
                    4. 3-5초 후 결과 확인

                    **AI 품질 검증 방식**
                    - AI가 실시간으로 뉴스 품질 판단
                    - 5W1H 점수 계산: 제목(20) + 본문(60) + 날짜(10) + URL(10)
                    - 95점 이상: 저장 / 미만: 자동 복구 시도
                    """)

                # Progress 표시기 추가
                single_progress = gr.Progress()

                single_output = gr.HTML(label="실시간 크롤링 결과")

                # 로그 출력 영역 (기본 열림)
                with gr.Accordion("📋 실시간 로그", open=True):
                    single_log = gr.Textbox(
                        label="실시간 로그",
                        lines=15,
                        max_lines=20,
                        interactive=False,
                        show_copy_button=True
                    )

                # 실시간 크롤링 함수
                def run_single_crawl(url: str, category: str, progress=single_progress) -> Tuple[str, str]:
                    """
                    단일 URL 크롤링 + UC1 검증 함수 (Gradio 연동)

                    Args:
                        url: 크롤링할 기사 URL
                        category: 카테고리 (politics/economy/society/international)

                    Returns:
                        Tuple[str, str]: (HTML 결과 메시지, 로그 텍스트)
                    """
                    if not url:
                        gr.Warning("⚠️ URL을 입력해주세요")
                        return (
                            """<div class='status-box status-warning'>
                            <h3 style='margin: 0;'>⚠️ URL 입력 필요</h3>
                            </div>""",
                            ""
                        )

                    try:
                        # Progress: 시작
                        progress(0, desc="🚀 크롤링 시작 중...")
                        start_time = datetime.now()

                        # Progress: HTML 페칭
                        progress(0.2, desc="📡 HTML 페이지 가져오는 중...")

                        # Scrapy 크롤링
                        cmd = [
                            "poetry", "run", "scrapy", "crawl", "yonhap",
                            "-a", f"start_urls={url}",
                            "-a", f"category={category}",
                            "-s", "CLOSESPIDER_ITEMCOUNT=1"
                        ]

                        # Progress: Scrapy 실행
                        progress(0.4, desc="🕷️ Scrapy 크롤러 실행 중...")

                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            cwd=PROJECT_ROOT
                        )

                        # Progress: UC1 검증
                        progress(0.7, desc="🤖 GPT-4o-mini 품질 검증 중...")

                        elapsed = (datetime.now() - start_time).total_seconds()

                        # 로그 추출 (중요한 부분만)
                        log_lines = result.stdout.split('\n') if result.stdout else []
                        important_logs = []
                        for line in log_lines:
                            # 핵심 키워드만 필터링 (로그 폭발 방지)
                            if any(keyword in line for keyword in [
                                'UC1 Quality Gate', 'REJECT', 'ERROR', 'Spider closed'
                            ]):
                                # 타임스탬프 제거
                                if '[yonhap]' in line:
                                    # "2025-11-04 08:15:02 [yonhap] INFO:" 형식에서 날짜/시간 제거
                                    parts = line.split('[yonhap]')
                                    if len(parts) > 1:
                                        clean_line = '[yonhap]' + parts[1]
                                        important_logs.append(clean_line.strip())
                                elif '| INFO |' in line or '| WARNING |' in line:
                                    # loguru 형식 로그 정리
                                    if '-' in line:
                                        msg = line.split('-', 1)[-1].strip()
                                        important_logs.append(msg)
                                else:
                                    important_logs.append(line.strip())

                        log_output = '\n'.join(important_logs[-50:]) if important_logs else "로그를 찾을 수 없습니다"  # 최근 50줄

                        # Progress: DB 확인
                        progress(0.9, desc="💾 데이터베이스 확인 중...")

                        # DB 확인
                        db = next(get_db())
                        article = db.query(CrawlResult).filter(CrawlResult.url == url).first()

                        # Progress: 완료
                        progress(1.0, desc="✅ 완료!")

                        if article:
                            gr.Info(f"✅ 크롤링 성공! 품질 점수: {article.quality_score}/100")
                            # UC1 결과 파싱
                            reasoning = article.llm_reasoning or "N/A"

                            html_output = f"""
                            <div class='status-box status-success'>
                                <h3 style='margin: 0 0 15px 0;'>✅ 크롤링 성공!</h3>

                                <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 10px 0;'>
                                    <p style='margin: 5px 0;'><strong>📰 제목:</strong> {article.title[:100]}...</p>
                                    <p style='margin: 5px 0;'><strong>📂 카테고리:</strong> {article.category_kr or article.category}</p>
                                    <p style='margin: 5px 0;'><strong>📅 발행일:</strong> {article.article_date}</p>
                                    <p style='margin: 5px 0;'><strong>⭐ 품질 점수:</strong> <span style='font-size: 1.3em; color: #10b981;'>{article.quality_score}/100</span></p>
                                    <p style='margin: 5px 0;'><strong>⏱️ 소요 시간:</strong> {elapsed:.1f}초</p>
                                </div>

                                <div style='background: rgba(255,255,255,0.03); padding: 15px; border-radius: 6px; margin: 10px 0;'>
                                    <h4 style='margin: 0 0 10px 0;'>🤖 AI 품질 검증 판단</h4>
                                    <p style='margin: 5px 0; white-space: pre-wrap; opacity: 0.9;'>{reasoning}</p>
                                </div>
                            </div>
                            """
                            return (html_output, log_output)
                        else:
                            gr.Warning("⚠️ AI 품질 기준 미달로 저장되지 않았습니다")
                            html_output = f"""
                            <div class='status-box status-error'>
                                <h3 style='margin: 0;'>❌ 크롤링 실패</h3>
                                <p style='margin: 10px 0 0 0;'>AI가 품질 기준 미달로 판단하여 저장하지 않았습니다.</p>
                            </div>
                            """
                            return (html_output, log_output)

                    except subprocess.TimeoutExpired:
                        gr.Error("⏱️ 타임아웃 (30초 초과) - 다시 시도해주세요")
                        return (
                            """<div class='status-box status-error'>
                            <h3 style='margin: 0;'>⏱️ 타임아웃 (30초 초과)</h3>
                            </div>""",
                            "타임아웃 발생"
                        )
                    except Exception as e:
                        gr.Error(f"❌ 오류 발생: {str(e)}")
                        return (
                            f"""<div class='status-box status-error'>
                            <h3 style='margin: 0;'>❌ 오류 발생</h3>
                            <p style='margin: 10px 0 0 0;'>{str(e)}</p>
                            </div>""",
                            f"에러: {str(e)}"
                        )

                # 테스트 크롤링 버튼
                single_crawl_btn.click(
                    fn=run_single_crawl,
                    inputs=[single_url, single_category],
                    outputs=[single_output, single_log]
                )

                gr.Markdown("---")

                # 자동 스케줄러 안내
                gr.Markdown("### 2️⃣ 자동 일간 수집")
                gr.Markdown("""
                **일간 뉴스 자동 수집은 "⏰ 자동 스케줄" 탭에서 설정하세요!**

                - 매일 자동으로 뉴스 수집
                - 시간과 카테고리 설정 가능
                - 수집 기록 조회 가능

                👉 **[⏰ 자동 스케줄]** 탭으로 이동하세요
                """)

            # ============================================
            # Tab 2: 🧠 AI 처리 시스템
            # ============================================
            with gr.Tab("🧠 AI 처리 시스템"):
                gr.Markdown("""
                ## LangGraph 멀티 에이전트 시스템

                **CrawlAgent 핵심 아키텍처**: Master Graph + 3개 Use Case Agents

                ### 2-Agent LLM 전략:
                - **GPT-4o-mini**: UC2 Proposer (빠른 CSS Selector 제안)
                - **Gemini-2.0-flash**: UC2 Validator (독립 검증)
                - **GPT-4o**: UC3 Discoverer (신규 사이트 DOM 분석)

                ### Weighted Consensus (UC2):
                - GPT Confidence: 30%
                - Gemini Confidence: 30%
                - Extraction Quality: 40%
                - **Threshold**: 0.6 (60%)
                """)

                gr.Markdown("---")

                # Master Graph 전체 구조 시각화
                gr.Markdown("### 🎯 Master Graph Supervisor Routing")
                gr.Markdown("""
                **진정한 Multi-Agent Orchestration**: Supervisor가 모든 라우팅 결정을 수행합니다.

                각 UC는 작업 완료 후 Supervisor로 복귀하며, Supervisor가 State를 분석하여 다음 UC로 라우팅합니다.
                """)

                # Master Graph 다이어그램 (PNG)
                gr.Image(
                    value=os.path.join(PROJECT_ROOT, "docs", "master_workflow_graph.png"),
                    label="Master Graph Architecture",
                    show_label=True,
                    show_download_button=False,
                    container=True,
                    height=300
                )

                gr.Markdown("**주요 라우팅 경로**:")
                gr.Markdown("""
                1. **UC1 성공 (정상 크롤링)**:
                   ```
                   START → Supervisor → UC1 → Supervisor → END
                   ```

                2. **UC1 실패 → UC2 Self-Healing (Consensus 성공)**:
                   ```
                   START → Supervisor → UC1 → Supervisor → UC2 → Supervisor → UC1 → Supervisor → END
                   ```
                   ⚠️ UC2가 Consensus에 성공하면 새 Selector로 UC1 재시도

                3. **UC1 실패 → UC2 Self-Healing (Consensus 실패)**:
                   ```
                   START → Supervisor → UC1 → Supervisor → UC2 → Supervisor → END (Human Review)
                   ```

                4. **UC1 실패 + Selector 없음 → UC3 Discovery**:
                   ```
                   START → Supervisor → UC1 → Supervisor → UC3 → Supervisor → END
                   ```

                **핵심**: 모든 UC는 Supervisor로 복귀하며, Supervisor가 State를 분석하여 다음 액션을 결정합니다.
                """)

                gr.Markdown("---")

                # AI 품질 검증 워크플로우
                gr.Markdown("### 📊 UC1 품질 검증 워크플로우 (상세)")
                gr.Markdown("규칙 기반 품질 검증 (LLM 없음, ~100ms)")

                # 전체 너비 시각화
                langgraph_plot = gr.Plot(
                    value=create_langgraph_figure(),
                    label="Interactive Workflow Visualization"
                )

                # State 구조 설명 (접을 수 있음)
                with gr.Accordion("📦 State 구조 상세보기", open=False):
                    gr.Markdown(get_state_description())

                gr.Markdown("---")

                # UC2 자동 복구 설명
                gr.Markdown("### 🔄 UC2 Self-Healing System")
                gr.Markdown("""
                **목적**: 사이트 구조 변경 시 30-60초 내 자동 복구

                **2-Agent Consensus 흐름**:
                1. **GPT-4o-mini (Proposer)**: HTML 재분석 → 새 CSS Selector 제안 (3개 후보)
                2. **Gemini-2.0-flash (Validator)**: 독립 검증 (샘플 10개 추출)
                3. **Weighted Consensus**: GPT 30% + Gemini 30% + Extraction 40%
                4. **Threshold 0.6 통과 시**: DB 자동 업데이트 → UC1 복귀
                5. **Threshold 미달 시**: DecisionLog 기록 → Human Review

                **Human Review**:
                - Consensus < 0.6일 때 자동 트리거
                - 2개 AI의 제안 및 근거 표시
                - 관리자가 최종 승인/거부
                """)

                gr.Markdown("### 🆕 UC3 신규 사이트 Discovery (3-Tool + 2-Agent + Consensus)")
                gr.Markdown("""
                **목적**: 신규 사이트 추가 시 CSS Selector 자동 생성 (Phase 1-3 완료)

                **🔧 3-Tool 시스템**:
                1. **Tavily Web Search**: GitHub/StackOverflow에서 유사 사이트 CSS 패턴 검색
                   - 목적: 외부 지식 활용 (다른 개발자의 솔루션)
                   - 출력: 3개 검색 결과
                2. **Firecrawl HTML Preprocessing**: HTML 토큰 90% 감소
                   - 목적: LLM 입력 최적화 (비용 절감)
                   - 효과: 206KB → 1.4KB (99.3% 감소)
                3. **BeautifulSoup DOM Analyzer**: 통계적 DOM 구조 분석
                   - 목적: H1/H2 태그, data-* 속성 등 실제 패턴 발견
                   - 출력: 제목/본문/날짜 후보 각 3개

                **🤖 2-Agent Consensus**:
                1. **GPT-4o Proposer**: 3-Tool 결과를 종합하여 CSS 셀렉터 제안
                   - 입력: Tavily + Firecrawl + BeautifulSoup 결과
                   - 출력: title/body/date 셀렉터 + confidence (0.0-1.0)
                2. **Gemini 2.0 Flash Lite Validator**: 실제 HTML에서 검증
                   - 입력: GPT-4o 제안 + raw_html (full HTML)
                   - 검증: validate_selector_tool로 각 셀렉터 테스트
                   - 출력: validation_details + overall_confidence

                **📊 Weighted Consensus**:
                - 공식: `0.3×GPT + 0.3×Gemini + 0.4×Extraction Quality`
                - Threshold: **0.7** (UC2보다 높음, 기준 데이터 없으므로)
                - 네이버 뉴스 테스트: **0.89** ✅ (자동 DB 저장)

                **Self-Healing**:
                - Consensus ≥ 0.7: DB 자동 저장
                - Consensus < 0.7: Human Review (Slack 알림)
                - Fallback: Gemini 실패 시 GPT-4o-mini 대체
                """)

                gr.Markdown("---")

                # Decision Log 조회
                gr.Markdown("### 📋 UC2/UC3 처리 기록 (DecisionLog)")

                refresh_log_btn = gr.Button("🔄 기록 새로고침", size="sm")
                log_output = gr.Dataframe(
                    label="2-Agent Consensus 기록 (UC2 Human Review 대기 포함)",
                    headers=["ID", "URL", "Site", "Consensus", "Retry", "Created"],
                    interactive=False
                )

                def refresh_decision_log() -> pd.DataFrame:
                    """
                    Decision Log 조회 (UC2/UC3 합의 기록)

                    Returns:
                        pd.DataFrame: Decision Log 결과 (ID, URL, Site, Consensus, Retry, Created)
                    """
                    try:
                        db = next(get_db())
                        logs = db.query(DecisionLog).order_by(DecisionLog.created_at.desc()).limit(20).all()
                        db.close()

                        if not logs:
                            return pd.DataFrame({"메시지": ["아직 처리 기록이 없습니다 (UC2/UC3 실행 시 생성)"]})

                        data = []
                        for log in logs:
                            data.append({
                                "ID": log.id,
                                "URL": log.url[:50] + "...",
                                "Site": log.site_name,
                                "Consensus": "✅" if log.consensus_reached else "❌",
                                "Retry": log.retry_count,
                                "Created": log.created_at.strftime("%Y-%m-%d %H:%M")
                            })

                        return pd.DataFrame(data)
                    except Exception as e:
                        return pd.DataFrame({"오류": [str(e)]})

                refresh_log_btn.click(
                    fn=refresh_decision_log,
                    outputs=log_output
                )

            # ============================================
            # Tab 3: 🎯 Master Graph 테스트 (Phase A/B)
            # ============================================
            with gr.Tab("🎯 Master Graph 테스트"):
                gr.Markdown("""
                ## Master Graph 멀티 에이전트 오케스트레이션 테스트

                **Phase A 검증**: LangGraph 기반 통합 오케스트레이션 시스템

                이 탭에서 3가지 유스케이스를 독립적으로 테스트하고 LangSmith에서 Trace를 확인할 수 있습니다.
                """)

                gr.Markdown("---")

                # 3가지 유스케이스 상세 설명
                gr.Markdown("### 🎯 3가지 유스케이스 (Use Cases)")

                with gr.Accordion("✅ UC1: 품질 검증 (Quality Validation)", open=False):
                    gr.Markdown("""
                    **목적**: 규칙 기반 품질 검증으로 크롤링된 데이터의 품질을 즉시 평가

                    **특징**:
                    - **LLM 사용 없음**: 순수 규칙 기반 (속도: ~100ms)
                    - **비용 없음**: LLM API 호출 0회 ($0)
                    - **평가 기준**: 제목(20점) + 본문(60점) + 날짜(10점) + URL(10점) = 총 100점

                    **워크플로우**:
                    ```
                    START → Supervisor → UC1 Validation → Supervisor → END
                    ```

                    **판정**:
                    - Quality Score ≥ 80: **즉시 저장** (next_action=save)
                    - Quality Score < 80: **UC2 또는 UC3로 라우팅** (Supervisor 결정)

                    **실제 URL 예시**: 연합뉴스 정상 기사
                    """)

                with gr.Accordion("🔄 UC2: Self-Healing (2-Agent Consensus)", open=False):
                    gr.Markdown("""
                    **목적**: 사이트 구조 변경 시 30-60초 내 자동 복구

                    **특징**:
                    - **2-Agent Consensus**: GPT-4o-mini (Proposer) + Gemini-2.0-flash (Validator)
                    - **Weighted Score**: 0.3×GPT + 0.3×Gemini + 0.4×Extraction Quality
                    - **Threshold**: 0.6 (60% 이상 시 자동 DB 업데이트)

                    **워크플로우**:
                    ```
                    START → Supervisor → UC1 (실패) → Supervisor → UC2 Self-Healing → Supervisor → END
                    ```

                    **프로세스**:
                    1. GPT-4o-mini: HTML 재분석 → 새 CSS Selector 3개 제안
                    2. Gemini-2.0-flash: 독립 검증 (샘플 10개 추출)
                    3. Weighted Consensus 계산
                    4. Consensus ≥ 0.6: DB 자동 업데이트 → UC1 복귀
                    5. Consensus < 0.6: DecisionLog 기록 → Human Review

                    **실제 URL 예시**: 연합뉴스 기사 (기존 Selector 수동 파괴하여 테스트)
                    """)

                with gr.Accordion("🆕 UC3: 신규 사이트 Discovery (3-Tool + 2-Agent + Consensus)", open=False):
                    gr.Markdown("""
                    **목적**: 신규 사이트 추가 시 CSS Selector 자동 생성

                    **특징**:
                    - **3-Tool**: Tavily (외부 지식) + Firecrawl (토큰 축소) + BeautifulSoup (DOM 분석)
                    - **2-Agent Consensus**: GPT-4o (Proposer) + Gemini-2.0-flash-lite (Validator)
                    - **Weighted Score**: 0.3×GPT + 0.3×Gemini + 0.4×Extraction Quality
                    - **Threshold**: 0.7 (70% 이상 시 자동 DB 저장)

                    **워크플로우**:
                    ```
                    START → Supervisor → UC3 Discovery
                      ↓
                    3-Tool 병렬 실행 (Tavily + Firecrawl + BeautifulSoup)
                      ↓
                    GPT-4o Proposer (3-Tool 종합 분석)
                      ↓
                    Gemini Validator (실제 HTML 검증)
                      ↓
                    Consensus 계산 (0.3×GPT + 0.3×Gemini + 0.4×Extract)
                      ↓
                    ≥ 0.7? → save_selectors : human_review
                      ↓
                    Supervisor → END
                    ```

                    **프로세스**:
                    1. HTML 다운로드 + 3-Tool 실행
                    2. GPT-4o: 3-Tool 결과 종합 → CSS 셀렉터 제안
                    3. Gemini: validate_selector_tool로 실제 추출 테스트
                    4. Consensus ≥ 0.7: DB 저장 (네이버 뉴스: 0.89 ✅)
                    5. Consensus < 0.7: DecisionLog 기록 → Human Review

                    **실제 URL 예시**: 아무 SSR 뉴스 사이트 (예: 조선일보, 중앙일보 등)
                    """)

                gr.Markdown("---")

                gr.Markdown("""
                **테스트 방법**:
                1. 아래에서 시나리오를 선택하세요
                2. 실제 URL을 입력하세요 (기본값: 연합뉴스 샘플)
                3. "테스트 실행" 버튼 클릭
                4. 결과에서 UC2/UC3 메트릭을 확인하세요
                5. LangSmith에서 Trace를 확인하세요 (하단 링크)
                """)

                gr.Markdown("---")

                # 시나리오 선택
                gr.Markdown("### 테스트 시나리오 선택")

                with gr.Row():
                    scenario_choice = gr.Radio(
                        label="시나리오",
                        choices=[
                            "1. UC1 성공 (정상 크롤링)",
                            "2. UC1 실패 → UC2 (Self-Healing)",
                            "3. UC3 신규 사이트 (Discovery)"
                        ],
                        value="1. UC1 성공 (정상 크롤링)"
                    )

                with gr.Row():
                    test_url_input = gr.Textbox(
                        label="테스트 URL (기본값: 연합뉴스 샘플 URL)",
                        placeholder="https://www.yna.co.kr/view/AKR20251108033551030",
                        value="https://www.yna.co.kr/view/AKR20251108033551030",
                        scale=3
                    )
                    run_test_btn = gr.Button("🚀 테스트 실행", variant="primary", size="lg", scale=1)

                # 테스트 결과
                test_output = gr.HTML(label="테스트 결과")

                # 워크플로우 히스토리 (접을 수 있음)
                with gr.Accordion("📋 Workflow History (LangGraph Traces)", open=True):
                    workflow_history = gr.Textbox(
                        label="Workflow Path",
                        lines=15,
                        interactive=False,
                        show_copy_button=True
                    )

                # LangSmith 링크
                gr.Markdown("""
                ---
                ### 🔍 LangSmith Tracing

                **Trace 확인**: [https://smith.langchain.com/o/default/projects/p/crawlagent-poc](https://smith.langchain.com/o/default/projects/p/crawlagent-poc)

                각 테스트 실행 후 LangSmith에서 다음을 확인하세요:
                - Supervisor routing 결정
                - UC별 State 변화
                - LLM 호출 여부 (UC1: 0회, UC2: 2회, UC3: 1회)
                - Consensus 계산 (UC2만 해당)
                """)

                # 테스트 함수
                def run_master_graph_test(scenario: str, test_url: str) -> tuple:
                    """
                    Master Graph 테스트 실행

                    Args:
                        scenario: 선택된 시나리오
                        test_url: 테스트할 URL

                    Returns:
                        tuple: (HTML 결과, Workflow History 텍스트)
                    """
                    try:
                        from datetime import datetime
                        start_time = datetime.now()

                        # Scenario 파싱
                        scenario_num = scenario[0]  # "1", "2", "3"

                        # Master Graph 빌드
                        graph = build_master_graph()

                        # HTML 다운로드
                        response = requests.get(test_url, timeout=10)
                        response.raise_for_status()
                        html_content = response.text

                        # 시나리오별 초기 State 설정
                        if scenario_num == "1":
                            # UC1 성공 (정상 사이트)
                            initial_state = {
                                "url": test_url,
                                "site_name": "yonhap",
                                "html_content": html_content,
                                "failure_count": 0,
                                "quality_passed": None,
                                "quality_score": None,
                                "next_action": None
                            }
                            expected_path = "Supervisor → UC1 → Supervisor → END"

                        elif scenario_num == "2":
                            # UC1 실패 → UC2 (불량 Selector로 시뮬레이션)
                            initial_state = {
                                "url": test_url,
                                "site_name": "yonhap",
                                "html_content": html_content,
                                "failure_count": 1,
                                "quality_passed": False,
                                "quality_score": 30,
                                "next_action": "heal"
                            }
                            expected_path = "Supervisor → UC1 (internal UC2) → Supervisor → END"

                        else:  # scenario_num == "3"
                            # UC3 신규 사이트
                            initial_state = {
                                "url": test_url,
                                "site_name": "test_newsite_gradio",
                                "html_content": html_content,
                                "failure_count": 0,
                                "quality_passed": None,
                                "quality_score": None,
                                "next_action": "uc3"
                            }
                            expected_path = "Supervisor → UC3 → Supervisor → END"

                        # Master Graph 실행
                        result = graph.invoke(initial_state)

                        elapsed = (datetime.now() - start_time).total_seconds()

                        # Workflow History 추출
                        workflow_path = []
                        workflow_path.append(f"Expected Path: {expected_path}\n")
                        workflow_path.append(f"Execution Time: {elapsed:.2f}s\n")
                        workflow_path.append(f"\nState Transitions:\n")
                        workflow_path.append(f"{'='*60}\n")

                        # 결과 State 분석
                        workflow_path.append(f"\nFinal State:\n")
                        workflow_path.append(f"  - URL: {result.get('url')}\n")
                        workflow_path.append(f"  - Site: {result.get('site_name')}\n")
                        workflow_path.append(f"  - Quality Score: {result.get('quality_score')}\n")
                        workflow_path.append(f"  - Quality Passed: {result.get('quality_passed')}\n")
                        workflow_path.append(f"  - Next Action: {result.get('next_action')}\n")
                        workflow_path.append(f"  - Failure Count: {result.get('failure_count')}\n")

                        if result.get('uc2_triggered'):
                            workflow_path.append(f"\n  UC2 Triggered:\n")
                            workflow_path.append(f"    - UC2 Success: {result.get('uc2_success')}\n")
                            workflow_path.append(f"    - GPT Proposal: {bool(result.get('gpt_proposal'))}\n")
                            workflow_path.append(f"    - Gemini Validation: {bool(result.get('gemini_validation'))}\n")
                            workflow_path.append(f"    - Consensus Score: {result.get('consensus_score')}\n")

                        if result.get('uc3_triggered'):
                            workflow_path.append(f"\n  UC3 Triggered:\n")
                            workflow_path.append(f"    - UC3 Success: {result.get('uc3_success')}\n")
                            workflow_path.append(f"    - GPT Analysis: {bool(result.get('gpt_analysis'))}\n")
                            workflow_path.append(f"    - Confidence: {result.get('confidence')}\n")

                        workflow_history_text = "".join(workflow_path)

                        # HTML 결과
                        if result.get('quality_passed'):
                            status_class = "status-success"
                            status_icon = "✅"
                            status_msg = "테스트 성공 (UC1 품질 검증 통과)"
                        elif result.get('uc2_success'):
                            status_class = "status-success"
                            status_icon = "✅"
                            status_msg = "테스트 성공 (UC2 Self-Healing 완료)"
                        elif result.get('uc3_success'):
                            status_class = "status-success"
                            status_icon = "✅"
                            status_msg = "테스트 성공 (UC3 Discovery 완료)"
                        else:
                            status_class = "status-warning"
                            status_icon = "⚠️"
                            status_msg = "테스트 부분 성공 (Human Review 필요 가능)"

                        html_result = f"""
                        <div class='{status_class}' style='padding: 20px; border-radius: 8px; margin: 10px 0;'>
                            <h3 style='margin: 0 0 15px 0;'>{status_icon} {status_msg}</h3>

                            <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 10px 0;'>
                                <p style='margin: 5px 0;'><strong>시나리오:</strong> {scenario}</p>
                                <p style='margin: 5px 0;'><strong>URL:</strong> {test_url[:80]}...</p>
                                <p style='margin: 5px 0;'><strong>실행 시간:</strong> {elapsed:.2f}초</p>
                                <p style='margin: 5px 0;'><strong>품질 점수:</strong> {result.get('quality_score', 'N/A')}</p>
                                <p style='margin: 5px 0;'><strong>최종 액션:</strong> {result.get('next_action', 'N/A')}</p>
                            </div>
                        """

                        # UC2 메트릭 표시 (Self-Healing)
                        if result.get('uc2_triggered'):
                            consensus = result.get('uc2_consensus_result', {})
                            gpt_conf = consensus.get('gpt_confidence', 0)
                            gemini_conf = consensus.get('gemini_confidence', 0)
                            consensus_score = consensus.get('consensus_score', 0)

                            html_result += f"""
                            <div style='background: rgba(59, 130, 246, 0.1); padding: 15px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #3b82f6;'>
                                <h4 style='margin: 0 0 10px 0;'>🔄 UC2 Self-Healing Metrics (2-Agent Consensus)</h4>
                                <table style='width: 100%; border-collapse: collapse; color: #e5e7eb;'>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px; width: 50%;'><strong>GPT-4o-mini Confidence:</strong></td>
                                        <td style='padding: 8px;'>{gpt_conf:.2f} <span style='opacity: 0.7;'>(가중치 30%)</span></td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Gemini-2.0-flash Confidence:</strong></td>
                                        <td style='padding: 8px;'>{gemini_conf:.2f} <span style='opacity: 0.7;'>(가중치 30%)</span></td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Extraction Quality:</strong></td>
                                        <td style='padding: 8px;'>자동 계산 <span style='opacity: 0.7;'>(가중치 40%)</span></td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Weighted Consensus Score:</strong></td>
                                        <td style='padding: 8px;'><span style='color: #10b981; font-weight: bold; font-size: 1.1em;'>{consensus_score:.2f}</span></td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Threshold (통과 기준):</strong></td>
                                        <td style='padding: 8px;'>0.60</td>
                                    </tr>
                                    <tr>
                                        <td style='padding: 8px;'><strong>Formula:</strong></td>
                                        <td style='padding: 8px; font-family: monospace; opacity: 0.8;'>0.3×GPT + 0.3×Gemini + 0.4×Extract</td>
                                    </tr>
                                </table>
                                <p style='margin: 10px 0 0 0; opacity: 0.8; font-size: 0.95em;'>
                                    ✅ Consensus ≥ 0.6: 자동 DB 업데이트<br>
                                    ❌ Consensus < 0.6: Human Review 트리거
                                </p>
                            </div>
                            """

                        # UC3 메트릭 표시 (Discovery)
                        if result.get('uc3_triggered'):
                            uc3_result = result.get('uc3_discovery_result', {})
                            confidence = uc3_result.get('confidence', 0)
                            selectors = uc3_result.get('discovered_selectors', {})

                            title_sel = selectors.get('title_selector', 'N/A')
                            body_sel = selectors.get('body_selector', 'N/A')
                            date_sel = selectors.get('date_selector', 'N/A')

                            html_result += f"""
                            <div style='background: rgba(16, 185, 129, 0.1); padding: 15px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #10b981;'>
                                <h4 style='margin: 0 0 10px 0;'>🆕 UC3 Discovery Metrics (GPT-4o DOM Analysis)</h4>
                                <table style='width: 100%; border-collapse: collapse; color: #e5e7eb;'>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px; width: 30%;'><strong>GPT-4o Confidence:</strong></td>
                                        <td style='padding: 8px;'><span style='color: #10b981; font-weight: bold; font-size: 1.1em;'>{confidence:.2f}</span></td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Success Threshold:</strong></td>
                                        <td style='padding: 8px;'>Confidence ≥ 0.7 AND Success Rate ≥ 80%</td>
                                    </tr>
                                    <tr style='background: rgba(255,255,255,0.03);'>
                                        <td colspan='2' style='padding: 8px; font-weight: bold;'>Discovered CSS Selectors:</td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Title Selector:</strong></td>
                                        <td style='padding: 8px; font-family: monospace; font-size: 0.9em; color: #3b82f6;'>{title_sel}</td>
                                    </tr>
                                    <tr style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
                                        <td style='padding: 8px;'><strong>Body Selector:</strong></td>
                                        <td style='padding: 8px; font-family: monospace; font-size: 0.9em; color: #3b82f6;'>{body_sel}</td>
                                    </tr>
                                    <tr>
                                        <td style='padding: 8px;'><strong>Date Selector:</strong></td>
                                        <td style='padding: 8px; font-family: monospace; font-size: 0.9em; color: #3b82f6;'>{date_sel}</td>
                                    </tr>
                                </table>
                                <p style='margin: 10px 0 0 0; opacity: 0.8; font-size: 0.95em;'>
                                    이 Selector들이 DB에 저장되어 향후 크롤링에 사용됩니다.
                                </p>
                            </div>
                            """

                        html_result += """
                            <p style='margin-top: 15px; opacity: 0.8;'>
                                📊 Workflow History 탭에서 상세 경로를 확인하세요<br>
                                🔍 LangSmith에서 Trace를 확인하려면 위 링크를 클릭하세요
                            </p>
                        </div>
                        """

                        return (html_result, workflow_history_text)

                    except requests.exceptions.RequestException as e:
                        error_html = f"""
                        <div class='status-error' style='padding: 20px; border-radius: 8px;'>
                            <h3>❌ URL 다운로드 실패</h3>
                            <p>{str(e)}</p>
                        </div>
                        """
                        return (error_html, f"Error: {str(e)}")

                    except Exception as e:
                        error_html = f"""
                        <div class='status-error' style='padding: 20px; border-radius: 8px;'>
                            <h3>❌ 테스트 실패</h3>
                            <p>{str(e)}</p>
                        </div>
                        """
                        import traceback
                        error_trace = traceback.format_exc()
                        return (error_html, f"Error: {str(e)}\n\n{error_trace}")

                # 이벤트 핸들러
                run_test_btn.click(
                    fn=run_master_graph_test,
                    inputs=[scenario_choice, test_url_input],
                    outputs=[test_output, workflow_history]
                )

            # ============================================
            # Tab 4: 🔍 데이터 조회
            # ============================================
            with gr.Tab("🔍 데이터 조회"):

                # 상단 통계
                stats = get_stats_summary()
                gr.Markdown(f"""
                ## 📊 수집 통계

                - **총 수집 개수**: {stats['total']}개
                - **평균 품질**: {stats['avg_quality']}/100
                - **카테고리별**: 정치({stats['category_stats'].get('politics', 0)}) / 경제({stats['category_stats'].get('economy', 0)}) / 사회({stats['category_stats'].get('society', 0)}) / 국제({stats['category_stats'].get('international', 0)})
                """)

                gr.Markdown("---")

                # 자연어 검색 (새로 추가)
                gr.Markdown("### 💬 자연어 검색 (AI)")
                gr.Markdown("일상 언어로 검색하세요. AI가 자동으로 조건을 분석합니다.")

                with gr.Row():
                    nl_query = gr.Textbox(
                        label="🗣️ 자연어 검색",
                        placeholder='예: "경제 뉴스 중 삼성 관련 최근 1주일", "11월 7일 정치 기사"',
                        lines=1,
                        scale=4
                    )
                    nl_search_btn = gr.Button("🤖 AI 검색", variant="primary", size="lg", scale=1)

                # AI 파싱 결과 표시
                nl_parse_output = gr.HTML(label="AI 파싱 결과")

                with gr.Accordion("💡 자연어 검색 예시", open=False):
                    gr.Markdown("""
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
                    """)

                gr.Markdown("---")

                # 검색 필터 (기존)
                gr.Markdown("### 🔍 상세 검색 필터")

                with gr.Row():
                    keyword_input = gr.Textbox(
                        label="🔎 키워드",
                        placeholder="제목 또는 본문 검색",
                        lines=1
                    )
                    category_filter = gr.Dropdown(
                        label="📂 카테고리",
                        choices=["all", "politics", "economy", "society", "international"],
                        value="all"
                    )

                with gr.Row():
                    date_from_input = gr.Textbox(
                        label="📅 시작일 (YYYY-MM-DD)",
                        placeholder="2025-11-01",
                        lines=1
                    )
                    date_to_input = gr.Textbox(
                        label="📅 종료일 (YYYY-MM-DD)",
                        placeholder="2025-11-04",
                        lines=1
                    )
                    min_quality_slider = gr.Slider(
                        label="⭐ 최소 품질",
                        minimum=0,
                        maximum=100,
                        value=0,
                        step=10
                    )

                search_btn = gr.Button("🔍 검색", variant="primary", size="lg")

                # 결과 표시
                results_df = gr.Dataframe(
                    label="검색 결과",
                    interactive=False
                )

                # CSV 다운로드
                download_btn = gr.Button("📥 CSV 다운로드", size="lg")
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
                            parse_html
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
                    outputs=[keyword_input, category_filter, date_from_input, date_to_input, min_quality_slider, nl_parse_output]
                ).then(
                    fn=search_articles,
                    inputs=[keyword_input, category_filter, date_from_input, date_to_input, min_quality_slider],
                    outputs=results_df
                )

                # 검색 실행 (기존)
                search_btn.click(
                    fn=search_articles,
                    inputs=[keyword_input, category_filter, date_from_input, date_to_input, min_quality_slider],
                    outputs=results_df
                )

                # CSV 다운로드
                download_btn.click(
                    fn=download_csv,
                    inputs=results_df,
                    outputs=download_file
                )

                gr.Markdown("---")

                # 기사 상세보기
                gr.Markdown("### 📄 기사 상세보기")
                gr.Markdown("검색 결과에서 URL을 복사하여 붙여넣으세요")

                with gr.Row():
                    detail_url = gr.Textbox(
                        label="URL 입력",
                        placeholder="https://www.yna.co.kr/view/...",
                        lines=1,
                        scale=4
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
                        title = article.title.replace('<', '&lt;').replace('>', '&gt;')
                        body = article.body.replace('<', '&lt;').replace('>', '&gt;') if article.body else "본문 없음"
                        reasoning = article.llm_reasoning.replace('<', '&lt;').replace('>', '&gt;') if article.llm_reasoning else "N/A"

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

                detail_btn.click(
                    fn=get_article_detail,
                    inputs=detail_url,
                    outputs=detail_output
                )

            # ============================================
            # Tab 5: 🗑️ 데이터 관리
            # ============================================
            with gr.Tab("🗑️ 데이터 관리"):
                gr.Markdown("""
                ## 데이터베이스 관리

                **수집된 기사 데이터를 관리합니다.**

                테스트 및 개발 중 데이터 정리가 필요한 경우 사용하세요.

                ---

                ## 데이터 삭제 및 정리

                **⚠️ 주의: 삭제된 데이터는 복구할 수 없습니다!**
                """)

                gr.Markdown("---")

                # 조건별 삭제
                gr.Markdown("### 1️⃣ 조건별 삭제")

                with gr.Row():
                    with gr.Column():
                        delete_category = gr.Dropdown(
                            label="📂 카테고리",
                            choices=["economy", "politics", "society", "international"],
                            value="economy"
                        )

                        delete_date = gr.Textbox(
                            label="📅 삭제할 날짜 (YYYY-MM-DD)",
                            placeholder="비워두면 카테고리 전체 삭제",
                            lines=1
                        )

                        delete_btn = gr.Button("🗑️ 선택 삭제", variant="stop", size="lg")

                    with gr.Column():
                        gr.Markdown("""
                        **삭제 예시:**

                        1. **카테고리 전체 삭제**: 날짜 비우고 카테고리 선택
                        2. **특정 날짜만 삭제**: 날짜 + 카테고리 선택
                        """)

                delete_output = gr.HTML()

                gr.Markdown("---")

                # 전체 초기화
                gr.Markdown("### 2️⃣ 전체 데이터 초기화")
                gr.Markdown("**⚠️ 위험: 모든 수집 데이터가 삭제됩니다!**")

                with gr.Row():
                    confirm_text = gr.Textbox(
                        label="확인용 텍스트 입력",
                        placeholder="'DELETE ALL'을 정확히 입력하세요",
                        lines=1
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
                    fn=delete_articles,
                    inputs=[delete_category, delete_date],
                    outputs=delete_output
                )

                reset_btn.click(
                    fn=reset_all,
                    inputs=confirm_text,
                    outputs=reset_output
                )

            # ============================================
            # Tab 6: ⏰ 자동 스케줄
            # ============================================
            with gr.Tab("⏰ 자동 스케줄"):
                gr.Markdown("""
                ## 자동 뉴스 수집 스케줄러

                매일 정해진 시간에 자동으로 뉴스를 수집하도록 설정할 수 있습니다.

                **주의**: 이 UI는 스케줄 설정만 저장합니다. 실제 자동 실행은 시스템 cron 또는 systemd 타이머로 구성해야 합니다.
                """)

                gr.Markdown("---")

                # 스케줄 설정
                gr.Markdown("### 1️⃣ 스케줄 설정")

                with gr.Row():
                    schedule_enabled = gr.Checkbox(label="🔔 자동 수집 활성화", value=False)

                with gr.Row():
                    schedule_hour = gr.Slider(
                        label="⏰ 실행 시간 (시)",
                        minimum=0,
                        maximum=23,
                        value=2,
                        step=1
                    )
                    schedule_categories = gr.CheckboxGroup(
                        label="📂 수집 카테고리",
                        choices=["economy", "politics", "society", "international"],
                        value=["economy"]
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
                    interactive=False
                )

                # cron 설정 안내
                with gr.Accordion("🛠️ 시스템 자동 실행 설정 방법", open=False):
                    gr.Markdown("""
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
                    """)

                # Helper functions
                def save_schedule(enabled: bool, hour: int, categories: list) -> str:
                    """스케줄 설정 저장"""
                    import json
                    try:
                        schedule_config = {
                            "enabled": enabled,
                            "hour": int(hour),
                            "categories": categories,
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        with open('/tmp/crawl_schedule.json', 'w') as f:
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
                        if not os.path.exists('/tmp/crawl_schedule.json'):
                            return """
                            <div class='status-box status-info'>
                                <h3>ℹ️ 설정된 스케줄 없음</h3>
                                <p>위에서 스케줄을 설정하고 저장하세요.</p>
                            </div>
                            """

                        with open('/tmp/crawl_schedule.json', 'r') as f:
                            config = json.load(f)

                        enabled = config.get('enabled', False)
                        hour = config.get('hour', 0)
                        categories = config.get('categories', [])
                        updated_at = config.get('updated_at', 'N/A')

                        # 다음 실행 시간 계산
                        now = datetime.now()
                        next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                        if next_run < now:
                            next_run += timedelta(days=1)

                        status_class = 'status-success' if enabled else 'status-warning'
                        status_icon = '🟢' if enabled else '🔴'

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
                        results = db.query(CrawlResult).filter(
                            CrawlResult.crawl_date >= date.today() - timedelta(days=10)
                        ).order_by(CrawlResult.created_at.desc()).limit(100).all()

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
                                    "avg_duration": []
                                }
                            history[key]["count"] += 1
                            if r.crawl_duration_seconds:
                                history[key]["avg_duration"].append(r.crawl_duration_seconds)

                        # DataFrame 생성
                        data = []
                        for (crawl_date, category), stats in sorted(history.items(), key=lambda x: x[1]["created_at"], reverse=True)[:10]:
                            avg_dur = sum(stats["avg_duration"]) / len(stats["avg_duration"]) if stats["avg_duration"] else 0
                            data.append({
                                "실행일시": stats["created_at"].strftime("%Y-%m-%d %H:%M"),
                                "카테고리": category,
                                "상태": "✅ 완료",
                                "수집 개수": f"{stats['count']}개",
                                "소요 시간": f"{avg_dur:.1f}초" if avg_dur > 0 else "N/A"
                            })

                        return pd.DataFrame(data) if data else pd.DataFrame({"메시지": ["기록 없음"]})

                    except Exception as e:
                        return pd.DataFrame({"오류": [str(e)]})

                # Event handlers
                save_schedule_btn.click(
                    fn=save_schedule,
                    inputs=[schedule_enabled, schedule_hour, schedule_categories],
                    outputs=schedule_output
                )

                refresh_schedule_btn.click(
                    fn=get_schedule_status,
                    outputs=schedule_status
                )

                refresh_history_btn.click(
                    fn=get_schedule_history,
                    outputs=schedule_history
                )

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
        gr.Markdown("""
        **CrawlAgent PoC (Phase A/B Complete)** - LangGraph Multi-Agent Orchestration System

        **Tech Stack**:
        - LangGraph: StateGraph + Command API + Agent Supervisor Pattern
        - LLM: GPT-4o-mini (UC2 Proposer) + Gemini-2.0-flash (UC2 Validator) + GPT-4o (UC3 Discoverer)
        - Crawler: Scrapy + BeautifulSoup4
        - Database: PostgreSQL + SQLAlchemy
        - Tracing: LangSmith (LANGCHAIN_TRACING_V2)

        **Phase A**: Code Quality & LangSmith Verification ✅
        **Phase B**: Gradio UI Integration ✅
        """)

    return demo


# ========================================
# Main
# ========================================

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
