"""
CrawlAgent - 지능형 뉴스 수집 시스템
Created: 2025-11-04
Updated: 2025-11-08

목적:
1. AI 기반 뉴스 품질 검증
2. 자동 복구 시스템 (사이트 변경 감지)
3. 신규 사이트 자동 추가
4. 사람 검토 개입 가능
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
from src.ui.theme import CrawlAgentDarkTheme, get_custom_css
from src.ui.components.langgraph_viz import create_langgraph_figure, get_state_description
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
        # 🕷️ CrawlAgent - 지능형 뉴스 수집 시스템

        **AI 기반 뉴스 자동 수집 및 품질 검증**

        - ✅ **품질 검증**: AI가 뉴스 품질 자동 평가 (작동 중)
        - 🔄 **자동 복구**: 사이트 변경 감지 및 복구 (준비 중)
        - 🆕 **신규 사이트**: AI 기반 자동 추가 (준비 중)
        - 🧠 **지능형 처리**: 자동 라우팅, 상태 관리, 사람 검토
        """)

        # 개발자 모드 토글
        with gr.Row():
            with gr.Column(scale=8):
                pass  # 빈 공간
            with gr.Column(scale=2):
                dev_mode = gr.Checkbox(
                    label="🔧 개발자 모드",
                    value=False,
                    info="고급 기능 표시 (AI 시스템, DB 관리)"
                )

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
            # Tab 2: 🧠 AI 처리 시스템 (개발자 전용)
            # ============================================
            with gr.Tab("🧠 AI 처리 시스템 (🔧 개발자)"):
                # 개발자 모드 안내
                dev_notice_ai = gr.Markdown("""
                ## 🔒 개발자 전용 기능

                이 탭은 시스템 내부 동작을 확인하는 **개발자 전용 기능**입니다.

                **일반 사용자는 접근할 필요 없습니다:**
                - 크롤링: "🚀 콘텐츠 수집" 탭 사용
                - 검색: "🔍 데이터 조회" 탭 사용
                - 자동화: "⏰ 자동 스케줄" 탭 사용

                ---
                """, visible=True)

                ai_system_content = gr.Column(visible=False)

                with ai_system_content:
                    gr.Markdown("""
                    ## 지능형 뉴스 처리 시스템

                    **CrawlAgent의 핵심: AI 기반 자동 처리**

                    - 품질 검증, 자동 복구, 신규 사이트가 자동으로 처리됨
                    - 필요 시 사람 검토 개입 가능
                    - 모든 처리 기록 저장
                    """)

                    gr.Markdown("---")

                    # AI 품질 검증 워크플로우
                    gr.Markdown("### 📊 AI 품질 검증 워크플로우")
                    gr.Markdown("AI 기반 품질 검증 흐름 (5W1H 점수 계산 → 자동 처리)")

                    # 전체 너비 시각화
                    langgraph_plot = gr.Plot(
                        value=create_langgraph_figure(),
                        label="Interactive Workflow Visualization"
                    )

                    # State 구조 설명 (접을 수 있음)
                    with gr.Accordion("📦 처리 상태 구조 상세보기 (개발자용)", open=False):
                        gr.Markdown(get_state_description())

                    gr.Markdown("---")

                    # 자동 복구 설명
                    gr.Markdown("### 🔄 자동 복구 시스템 (준비 중)")
                    gr.Markdown("""
                    **목적**: 사이트 구조 변경 시 30-60초 내 자동 복구

                    **처리 흐름**:
                    1. AI 분석기: HTML 재분석 → 새 추출 규칙 생성 (3개 후보)
                    2. AI 검증기: 독립 검증 (샘플 10개 추출)
                    3. 2-AI 합의: 신뢰도 ≥ 0.7 AND 검증=통과
                    4. 데이터베이스 업데이트 → 재수집

                    **사람 검토 개입**:
                    - 합의 실패 시 수동 승인 요청
                    - AI 후보 3개 표시
                    - 검증 결과 표시
                    """)

                    gr.Markdown("### 🆕 신규 사이트 자동 추가 (준비 중)")
                    gr.Markdown("""
                    **목적**: 신규 사이트 추가 시 추출 규칙 자동 생성

                    **처리 흐름**: 자동 복구와 동일 (처음부터 2-AI 활성화)
                    """)

                    gr.Markdown("---")

                    # Decision Log 조회
                    gr.Markdown("### 📋 처리 기록 (자동 복구/신규 사이트용)")

                    refresh_log_btn = gr.Button("🔄 기록 새로고침", size="sm")
                    log_output = gr.Dataframe(
                        label="처리 기록 (2-AI 합의 기록)",
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
                                return pd.DataFrame({"메시지": ["아직 처리 기록이 없습니다 (자동 복구/신규 사이트 실행 시 생성)"]})

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

                # 개발자 모드 토글 이벤트 핸들러
                dev_mode.change(
                    fn=lambda dev: (gr.update(visible=not dev), gr.update(visible=dev)),
                    inputs=dev_mode,
                    outputs=[dev_notice_ai, ai_system_content]
                )

            # ============================================
            # Tab 3: 🔍 데이터 조회
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

                # 검색 필터
                gr.Markdown("### 🔍 검색 및 필터")

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

                # 검색 실행
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
            # Tab 4: 🗑️ 데이터 관리 (개발자 전용)
            # ============================================
            with gr.Tab("🗑️ 데이터 관리 (🔧 개발자)"):
                gr.Markdown("""
                ## 🔧 개발자 전용 기능

                **이 탭은 데이터 관리를 위한 개발자 전용 기능입니다.**

                일반 사용자는 이 기능을 사용할 필요가 없습니다.

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
            # Tab 5: ⏰ 자동 스케줄
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
            # Tab 6: 🤖 자동 복구 (개발자 전용)
            # ============================================
            with gr.Tab("🤖 자동 복구 (🔧 개발자)"):
                gr.Markdown("""
                ## 🔧 개발자 전용 기능

                **이 탭은 AI 제안 검토를 위한 개발자 전용 기능입니다.**

                일반 사용자는 이 기능을 사용할 필요가 없습니다.

                ---

                ## AI 제안 추출 규칙 승인/거부

                **2개의 AI**가 제안한 추출 규칙을 검토하고 최종 승인/거부하세요.
                승인 시 데이터베이스에 저장되어 자동으로 적용됩니다.

                **이 탭은 언제 사용하나요?**
                - 뉴스 사이트 구조가 변경되어 수집이 실패할 때
                - AI가 자동으로 새 추출 규칙을 제안하면 이 탭에서 확인
                - 신뢰할 수 있는 제안이면 승인, 아니면 거부
                """)

                gr.Markdown("---")

                # State management
                current_decision_id = gr.State(value=None)

                # Pending 목록 조회
                gr.Markdown("### 1️⃣ 승인 대기 중인 제안")

                refresh_btn = gr.Button("🔄 새로고침", size="sm")
                pending_list = gr.HTML()

                gr.Markdown("---")
                gr.Markdown("### 2️⃣ 제안 상세 내용")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 📌 기본 정보")
                        decision_info = gr.HTML()

                        gr.Markdown("#### 🤖 AI 제안")
                        gpt_proposal = gr.JSON(label="AI 제안 내용")

                    with gr.Column():
                        gr.Markdown("#### ✅ AI 검증")
                        gemini_validation = gr.JSON(label="AI 검증 결과")

                        gr.Markdown("#### 🎯 최종 결정")
                        with gr.Row():
                            approve_btn = gr.Button("✅ 승인", variant="primary", size="lg")
                            reject_btn = gr.Button("❌ 거부", variant="stop", size="lg")

                        decision_output = gr.HTML()

                # Helper functions
                def get_pending_decisions() -> str:
                    """승인 대기 중인 decision_logs 목록 조회"""
                    try:
                        db = next(get_db())
                        # consensus_reached=False인 로그 조회 (Human review 필요)
                        logs = db.query(DecisionLog).filter(
                            DecisionLog.consensus_reached == False
                        ).order_by(DecisionLog.created_at.desc()).limit(10).all()

                        if not logs:
                            return """
                            <div class='status-box status-info'>
                                <h3>ℹ️ 승인 대기 중인 제안이 없습니다</h3>
                                <p>자동 복구가 실행되면 여기에 표시됩니다.</p>
                            </div>
                            """

                        html = "<table style='width: 100%; border-collapse: collapse;'>"
                        html += "<tr style='background: #2d2d2d; font-weight: bold;'>"
                        html += "<th style='padding: 10px; border: 1px solid #444;'>ID</th>"
                        html += "<th style='padding: 10px; border: 1px solid #444;'>Site</th>"
                        html += "<th style='padding: 10px; border: 1px solid #444;'>URL</th>"
                        html += "<th style='padding: 10px; border: 1px solid #444;'>Retry</th>"
                        html += "<th style='padding: 10px; border: 1px solid #444;'>생성일시</th>"
                        html += "</tr>"

                        for log in logs:
                            html += "<tr>"
                            html += f"<td style='padding: 10px; border: 1px solid #444;'>{log.id}</td>"
                            html += f"<td style='padding: 10px; border: 1px solid #444;'>{log.site_name}</td>"
                            html += f"<td style='padding: 10px; border: 1px solid #444;'>{log.url[:50]}...</td>"
                            html += f"<td style='padding: 10px; border: 1px solid #444;'>{log.retry_count}</td>"
                            html += f"<td style='padding: 10px; border: 1px solid #444;'>{log.created_at.strftime('%Y-%m-%d %H:%M')}</td>"
                            html += "</tr>"

                        html += "</table>"
                        db.close()
                        return html

                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3>❌ 오류 발생</h3>
                            <p>{str(e)}</p>
                        </div>
                        """

                def load_decision(decision_id: int) -> Tuple[str, dict, dict, int]:
                    """특정 decision_log 로드"""
                    try:
                        db = next(get_db())
                        log = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()

                        if not log:
                            info_html = "<div class='status-box status-error'><h3>❌ Decision not found</h3></div>"
                            return info_html, {}, {}, None

                        info_html = f"""
                        <div class='status-box status-info'>
                            <h3>📋 Decision ID: {log.id}</h3>
                            <p><strong>Site:</strong> {log.site_name}</p>
                            <p><strong>URL:</strong> {log.url}</p>
                            <p><strong>Retry Count:</strong> {log.retry_count}</p>
                            <p><strong>Created:</strong> {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                        """

                        db.close()
                        return info_html, log.gpt_analysis or {}, log.gemini_validation or {}, log.id

                    except Exception as e:
                        error_html = f"<div class='status-box status-error'><h3>❌ {str(e)}</h3></div>"
                        return error_html, {}, {}, None

                def approve_decision(decision_id: int) -> str:
                    """제안 승인 및 selectors 테이블에 저장"""
                    if not decision_id:
                        return "<div class='status-box status-warning'><h3>⚠️ Decision ID가 없습니다</h3></div>"

                    try:
                        db = next(get_db())
                        log = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()

                        if not log or not log.gpt_analysis:
                            db.close()
                            return "<div class='status-box status-error'><h3>❌ Invalid decision log</h3></div>"

                        gpt = log.gpt_analysis

                        # selectors 테이블에 저장 (upsert)
                        selector = db.query(Selector).filter(Selector.site_name == log.site_name).first()

                        if selector:
                            # Update existing
                            selector.title_selector = gpt.get('title_selector', '')
                            selector.body_selector = gpt.get('body_selector', '')
                            selector.date_selector = gpt.get('date_selector', '')
                            selector.updated_at = datetime.utcnow()
                        else:
                            # Insert new
                            selector = Selector(
                                site_name=log.site_name,
                                title_selector=gpt.get('title_selector', ''),
                                body_selector=gpt.get('body_selector', ''),
                                date_selector=gpt.get('date_selector', ''),
                                site_type='ssr'
                            )
                            db.add(selector)

                        # Mark consensus as reached
                        log.consensus_reached = True

                        db.commit()
                        db.close()

                        return f"""
                        <div class='status-box status-success'>
                            <h3>✅ 승인 완료</h3>
                            <p>Site: <strong>{log.site_name}</strong></p>
                            <p>Selectors 테이블에 저장되었습니다.</p>
                        </div>
                        """

                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3>❌ 승인 실패</h3>
                            <p>{str(e)}</p>
                        </div>
                        """

                def reject_decision(decision_id: int) -> str:
                    """제안 거부 (decision_log만 업데이트)"""
                    if not decision_id:
                        return "<div class='status-box status-warning'><h3>⚠️ Decision ID가 없습니다</h3></div>"

                    try:
                        db = next(get_db())
                        log = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()

                        if not log:
                            db.close()
                            return "<div class='status-box status-error'><h3>❌ Decision not found</h3></div>"

                        # Mark as rejected (but keep for audit trail)
                        log.consensus_reached = False  # Keep false to indicate rejection
                        log.retry_count += 1  # Increment to track rejection

                        db.commit()
                        db.close()

                        return f"""
                        <div class='status-box status-warning'>
                            <h3>❌ 거부 완료</h3>
                            <p>Site: <strong>{log.site_name}</strong></p>
                            <p>자동 복구를 다시 실행하세요.</p>
                        </div>
                        """

                    except Exception as e:
                        return f"""
                        <div class='status-box status-error'>
                            <h3>❌ 거부 실패</h3>
                            <p>{str(e)}</p>
                        </div>
                        """

                # Event handlers
                refresh_btn.click(
                    fn=get_pending_decisions,
                    outputs=pending_list
                )

                # Load first pending decision on refresh
                def refresh_and_load():
                    try:
                        db = next(get_db())
                        log = db.query(DecisionLog).filter(
                            DecisionLog.consensus_reached == False
                        ).order_by(DecisionLog.created_at.desc()).first()
                        db.close()

                        if log:
                            return load_decision(log.id)
                        else:
                            info_html = "<div class='status-box status-info'><h3>ℹ️ No pending decisions</h3></div>"
                            return info_html, {}, {}, None
                    except Exception as e:
                        error_html = f"<div class='status-box status-error'><h3>❌ {str(e)}</h3></div>"
                        return error_html, {}, {}, None

                refresh_btn.click(
                    fn=refresh_and_load,
                    outputs=[decision_info, gpt_proposal, gemini_validation, current_decision_id]
                )

                approve_btn.click(
                    fn=approve_decision,
                    inputs=current_decision_id,
                    outputs=decision_output
                )

                reject_btn.click(
                    fn=reject_decision,
                    inputs=current_decision_id,
                    outputs=decision_output
                )

        # Footer
        gr.Markdown("---")
        gr.Markdown("""
        **CrawlAgent v1.0** - AI 기반 지능형 뉴스 수집 시스템
        Scrapy + AI 품질 검증 + 자동 복구 + PostgreSQL
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
