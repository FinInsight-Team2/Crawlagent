"""
CrawlAgent - LangGraph Multi-Agent Web Crawler
Created: 2025-11-04
Updated: 2025-11-04

목적:
1. LangGraph 기반 멀티 에이전트 시스템 시연
2. UC1 (GPT-4o-mini Quality Gate) 작동 확인
3. UC2/UC3 (Self-Healing) 미래 확장 준비
4. HITL (Human-in-the-Loop) 개입 가능
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
        title="CrawlAgent - LangGraph Multi-Agent Crawler",
        theme=theme,
        css=get_custom_css()
    ) as demo:

        # ============================================
        # 헤더
        # ============================================
        gr.Markdown("""
        # 🕷️ CrawlAgent - LangGraph Multi-Agent Web Crawler

        **GPT-4o-mini 기반 지능형 뉴스 수집 시스템 with LangGraph**

        - ✅ **UC1 Quality Gate**: GPT-4o-mini 품질 검증 (작동 중)
        - 🔄 **UC2 Self-Healing**: 2-Agent 자동 복구 (준비 중)
        - 🆕 **UC3 신규 사이트**: AI 기반 Selector 생성 (준비 중)
        - 🧠 **LangGraph**: 조건부 라우팅, State 관리, HITL 개입
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

                    **UC1 Quality Gate 작동 방식**
                    - GPT-4o-mini가 실시간으로 품질 판단
                    - 5W1H 점수 계산: 제목(20) + 본문(60) + 날짜(10) + URL(10)
                    - 95점 이상: 저장 / 미만: 자동 복구 시도
                    """)

                # Progress 표시기 추가
                single_progress = gr.Progress()

                single_output = gr.HTML(label="실시간 크롤링 결과")

                # 로그 출력 영역 (접을 수 있음)
                with gr.Accordion("📋 크롤링 로그", open=False):
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
                            # 더 넓은 범위로 로그 캡처
                            if any(keyword in line for keyword in [
                                '[yonhap]', 'UC1 Quality Gate', 'PASS', 'REJECT',
                                'SUCCESS', 'ERROR', 'DUPLICATE', '증분 수집',
                                'STAGE 1', 'STAGE 2', 'Found', 'Queued', 'Saved'
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
                                    <h4 style='margin: 0 0 10px 0;'>🤖 UC1 Quality Gate 판단</h4>
                                    <p style='margin: 5px 0; white-space: pre-wrap; opacity: 0.9;'>{reasoning}</p>
                                </div>
                            </div>
                            """
                            return (html_output, log_output)
                        else:
                            gr.Warning("⚠️ UC1 품질 기준 미달로 저장되지 않았습니다")
                            html_output = f"""
                            <div class='status-box status-error'>
                                <h3 style='margin: 0;'>❌ 크롤링 실패</h3>
                                <p style='margin: 10px 0 0 0;'>UC1이 품질 기준 미달로 판단하여 저장하지 않았습니다.</p>
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

                # 일간 수집
                gr.Markdown("### 2️⃣ 일간 수집 (날짜 기반)")
                gr.Markdown("특정 날짜의 모든 기사를 자동으로 수집합니다 (페이지네이션 + 중복 제거)")

                # 날짜 및 카테고리
                with gr.Row():
                    batch_date = gr.Textbox(
                        label="📅 수집 날짜 (YYYY-MM-DD)",
                        value=datetime.now().strftime("%Y-%m-%d"),
                        placeholder="2025-11-04",
                        lines=1,
                        scale=2
                    )
                    batch_category = gr.Dropdown(
                        label="📂 카테고리",
                        choices=["politics", "economy", "society", "international"],
                        value="economy",
                        scale=2
                    )
                    batch_crawl_btn = gr.Button("🚀 일간 수집 시작", variant="primary", size="lg", scale=1)

                # 일간 수집 가이드
                with gr.Accordion("📖 일간 수집 가이드", open=False):
                    gr.Markdown("""
                    **일간 수집 방식**
                    - 선택한 날짜의 모든 기사 자동 수집 (페이지네이션)
                    - 자동 중복 제거 (URL 기준)
                    - 다음날 기사 발견 시 자동 중단 (증분 수집)
                    - 평균 소요 시간: 30-60초 (10-20개 기사)

                    **사용 시나리오**
                    - 매일 밤 자동 실행 (스케줄러)
                    - 또는 수동으로 특정 날짜 수집

                    **주의사항**
                    - 타임아웃: 300초 (5분)
                    - 수집 결과는 "데이터 조회" 탭에서 확인
                    """)

                # Progress 표시기 추가
                batch_progress = gr.Progress()

                batch_output = gr.HTML(label="일간 수집 결과")

                # 일간 수집 로그 (접을 수 있음)
                with gr.Accordion("📋 일간 수집 로그", open=False):
                    batch_log = gr.Textbox(
                        label="실시간 로그",
                        lines=20,
                        max_lines=30,
                        interactive=False,
                        show_copy_button=True
                    )

                # 일간 수집 함수 (실시간 로그 스트리밍)
                def run_batch_crawl(target_date: str, category: str, progress=batch_progress) -> Tuple[str, str]:
                    """
                    일간 배치 크롤링 실행 함수 (Gradio 연동)

                    특정 날짜의 모든 기사를 페이지네이션으로 수집하며,
                    중복 제거 및 증분 수집 (다음날 기사 발견 시 중단) 적용

                    Args:
                        target_date: 수집 날짜 (YYYY-MM-DD 형식)
                        category: 카테고리 (politics/economy/society/international)

                    Returns:
                        Tuple[str, str]: (HTML 결과 메시지, 로그 텍스트)
                    """
                    if not target_date:
                        gr.Warning("⚠️ 날짜를 입력해주세요 (YYYY-MM-DD 형식)")
                        return (
                            """<div class='status-box status-warning'>
                            <h3 style='margin: 0;'>⚠️ 날짜 입력 필요</h3>
                            </div>""",
                            ""
                        )

                    try:
                        # Progress: 시작
                        progress(0, desc=f"🚀 {target_date} 일간 수집 시작...")
                        start_time = datetime.now()

                        cmd = [
                            "poetry", "run", "scrapy", "crawl", "yonhap",
                            "-a", f"target_date={target_date}",
                            "-a", f"category={category}"
                        ]

                        # Progress: Scrapy 시작
                        progress(0.1, desc="🕷️ Scrapy 크롤러 초기화 중...")

                        # Popen으로 실시간 로그 캡처
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            cwd=PROJECT_ROOT,
                            bufsize=1,  # 라인 버퍼링
                            universal_newlines=True
                        )

                        # 실시간 로그 수집
                        important_logs = []
                        timeout_seconds = 300  # 120초 → 300초 (5분)로 증가
                        elapsed_seconds = 0
                        article_count = 0  # 수집 개수 추적

                        while True:
                            # 0.5초마다 체크 (실시간 느낌)
                            import time
                            time.sleep(0.5)
                            elapsed_seconds += 0.5

                            # Progress 업데이트 (시간 기반)
                            progress_pct = min(0.1 + (elapsed_seconds / timeout_seconds) * 0.8, 0.9)
                            progress(progress_pct, desc=f"📰 기사 수집 중... ({article_count}개)")

                            # 타임아웃 체크
                            if elapsed_seconds >= timeout_seconds:
                                process.kill()
                                gr.Error("⏱️ 타임아웃 (300초 초과) - 더 최근 날짜를 선택하세요")
                                return (
                                    """<div class='status-box status-error'>
                                    <h3 style='margin: 0;'>⏱️ 타임아웃 (300초 초과)</h3>
                                    <p style='margin: 10px 0 0 0;'>크롤링이 너무 오래 걸립니다. 더 최근 날짜를 선택하세요.</p>
                                    </div>""",
                                    '\n'.join(important_logs) if important_logs else "타임아웃 발생"
                                )

                            # 프로세스 종료 여부 체크
                            if process.poll() is not None:
                                # 남은 로그 읽기
                                for line in process.stdout:
                                    if any(keyword in line for keyword in [
                                        '[yonhap]', 'UC1 Quality Gate', 'PASS', 'REJECT',
                                        'SUCCESS', 'ERROR', 'DUPLICATE', '증분 수집',
                                        'STAGE 1', 'STAGE 2', 'Found', 'Queued', 'Saved',
                                        'PAGINATION', '최대 페이지'
                                    ]):
                                        # 타임스탬프 제거
                                        if '[yonhap]' in line:
                                            parts = line.split('[yonhap]')
                                            if len(parts) > 1:
                                                clean_line = '[yonhap]' + parts[1]
                                                important_logs.append(clean_line.strip())
                                        else:
                                            important_logs.append(line.strip())
                                break

                            # 실시간 로그 읽기
                            line = process.stdout.readline()
                            if line:
                                # 수집 개수 추적 (PASS 키워드로 판단)
                                if 'PASS' in line or 'Saved' in line:
                                    article_count += 1

                                if any(keyword in line for keyword in [
                                    '[yonhap]', 'UC1 Quality Gate', 'PASS', 'REJECT',
                                    'SUCCESS', 'ERROR', 'DUPLICATE', '증분 수집',
                                    'STAGE 1', 'STAGE 2', 'Found', 'Queued', 'Saved',
                                    'PAGINATION', '최대 페이지'
                                ]):
                                    # 타임스탬프 제거
                                    if '[yonhap]' in line:
                                        parts = line.split('[yonhap]')
                                        if len(parts) > 1:
                                            clean_line = '[yonhap]' + parts[1]
                                            important_logs.append(clean_line.strip())
                                    else:
                                        important_logs.append(line.strip())

                        elapsed = (datetime.now() - start_time).total_seconds()
                        log_output = '\n'.join(important_logs) if important_logs else "로그를 찾을 수 없습니다"

                        # Progress: DB 확인
                        progress(0.95, desc="💾 데이터베이스 확인 중...")

                        # DB 확인
                        db = next(get_db())
                        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

                        articles = db.query(CrawlResult).filter(
                            CrawlResult.article_date == target_date_obj,
                            CrawlResult.category == category
                        ).all()

                        db.close()

                        # Progress: 완료
                        progress(1.0, desc="✅ 완료!")

                        if articles:
                            gr.Info(f"✅ 일간 수집 완료! {len(articles)}개 기사 저장됨")
                            count = len(articles)
                            avg_quality = sum(a.quality_score for a in articles) / count

                            html_output = f"""
                            <div class='status-box status-success'>
                                <h3 style='margin: 0 0 15px 0;'>✅ 일간 수집 완료!</h3>
                                <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 6px; margin: 10px 0;'>
                                    <p style='margin: 5px 0;'><strong>📅 수집 날짜:</strong> {target_date}</p>
                                    <p style='margin: 5px 0;'><strong>📂 카테고리:</strong> {category}</p>
                                    <p style='margin: 5px 0;'><strong>📊 수집 개수:</strong> <span style='font-size: 1.3em; color: #10b981;'>{count}개</span></p>
                                    <p style='margin: 5px 0;'><strong>⭐ 평균 품질:</strong> {avg_quality:.1f}/100</p>
                                    <p style='margin: 5px 0;'><strong>⏱️ 소요 시간:</strong> {elapsed:.1f}초</p>
                                </div>
                                <p style='margin: 15px 0 0 0;'>✨ "데이터 조회" 탭에서 결과를 확인할 수 있습니다.</p>
                            </div>
                            """
                            return (html_output, log_output)
                        else:
                            gr.Info("ℹ️ 수집된 콘텐츠가 없습니다 (중복 또는 품질 미달)")
                            html_output = f"""
                            <div class='status-box status-info'>
                                <h3 style='margin: 0;'>ℹ️ 수집된 콘텐츠 없음</h3>
                                <p style='margin: 10px 0 0 0;'>해당 날짜의 콘텐츠가 없거나 모두 중복입니다.</p>
                            </div>
                            """
                            return (html_output, log_output)

                    except Exception as e:
                        gr.Error(f"❌ 일간 수집 오류: {str(e)}")
                        return (
                            f"""<div class='status-box status-error'>
                            <h3 style='margin: 0;'>❌ 오류 발생</h3>
                            <p style='margin: 10px 0 0 0;'>{str(e)}</p>
                            </div>""",
                            f"에러: {str(e)}"
                        )

                batch_crawl_btn.click(
                    fn=run_batch_crawl,
                    inputs=[batch_date, batch_category],
                    outputs=[batch_output, batch_log]
                )

            # ============================================
            # Tab 2: 🧠 LangGraph Agent
            # ============================================
            with gr.Tab("🧠 LangGraph Agent"):
                gr.Markdown("""
                ## LangGraph 멀티 에이전트 시스템

                **CrawlAgent의 핵심: LangGraph 기반 조건부 라우팅**

                - UC1, UC2, UC3가 State 기반으로 자동 라우팅
                - Human-in-the-Loop (HITL) 개입 가능
                - Decision Log 추적
                """)

                gr.Markdown("---")

                # UC1 Validation Workflow
                gr.Markdown("### 📊 UC1 Validation Workflow")
                gr.Markdown("GPT-4o-mini 기반 품질 검증 흐름 (5W1H 점수 계산 → 조건부 라우팅)")

                # 전체 너비 시각화
                langgraph_plot = gr.Plot(
                    value=create_langgraph_figure(),
                    label="Interactive Workflow Visualization"
                )

                # State 구조 설명 (접을 수 있음)
                with gr.Accordion("📦 ValidationState 구조 상세보기", open=False):
                    gr.Markdown(get_state_description())

                gr.Markdown("---")

                # UC2/UC3 설명
                gr.Markdown("### 🔄 UC2: Self-Healing (준비 중)")
                gr.Markdown("""
                **목적**: 사이트 구조 변경 시 30-60초 내 자동 복구

                **워크플로우**:
                1. GPT-4o Analyzer: HTML 재분석 → 새 Selector 생성 (3개 후보)
                2. Gemini Validator: 독립 검증 (샘플 10개 추출)
                3. 2-Agent 합의: Confidence ≥ 0.7 AND Valid=true
                4. PostgreSQL 업데이트 → 재크롤링

                **HITL 개입**:
                - 합의 실패 시 수동 승인 요청
                - GPT 후보 3개 표시
                - Gemini 검증 결과 표시
                """)

                gr.Markdown("### 🆕 UC3: 신규 사이트 (준비 중)")
                gr.Markdown("""
                **목적**: 신규 사이트 추가 시 Selector 자동 생성

                **워크플로우**: UC2와 동일 (처음부터 2-Agent 활성화)
                """)

                gr.Markdown("---")

                # Decision Log 조회
                gr.Markdown("### 📋 Decision Log (UC2/UC3용)")

                refresh_log_btn = gr.Button("🔄 Log 새로고침", size="sm")
                log_output = gr.Dataframe(
                    label="Decision Log (GPT + Gemini 합의 기록)",
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
                            return pd.DataFrame({"메시지": ["아직 Decision Log가 없습니다 (UC2/UC3 실행 시 생성)"]})

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
            # Tab 4: 🗑️ 데이터 관리
            # ============================================
            with gr.Tab("🗑️ 데이터 관리"):
                gr.Markdown("""
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

        # Footer
        gr.Markdown("---")
        gr.Markdown("""
        **CrawlAgent v1.0** - LangGraph Multi-Agent Self-Healing Web Crawler
        Built with Scrapy + LangGraph + GPT-4o-mini + PostgreSQL
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
