#!/usr/bin/env python3
"""
Gemini 백업 키 및 gemini-exp-1206 모델 테스트
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger


def test_primary_key():
    """Primary key 테스트"""
    print("\n" + "=" * 80)
    print("1️⃣  Primary Key 테스트 (GOOGLE_API_KEY)")
    print("=" * 80)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found")
        return False

    print(f"✅ API Key found: {api_key[:20]}...")

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-exp-1206", temperature=0, google_api_key=api_key)

        response = llm.invoke(
            [{"role": "user", "content": "Say 'Hello from Gemini 2.5 Pro!' in one sentence."}]
        )
        print(f"✅ Primary key SUCCESS")
        print(f"Response: {response.content}")
        return True

    except Exception as e:
        print(f"❌ Primary key FAILED: {e}")
        return False


def test_backup_key():
    """Backup key 테스트"""
    print("\n" + "=" * 80)
    print("2️⃣  Backup Key 테스트 (GOOGLE_API_KEY_BACKUP)")
    print("=" * 80)

    api_key = os.getenv("GOOGLE_API_KEY_BACKUP")
    if not api_key:
        print("❌ GOOGLE_API_KEY_BACKUP not found")
        return False

    print(f"✅ Backup API Key found: {api_key[:20]}...")

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-exp-1206", temperature=0, google_api_key=api_key)

        response = llm.invoke(
            [
                {
                    "role": "user",
                    "content": "Say 'Hello from Gemini 2.5 Pro Backup!' in one sentence.",
                }
            ]
        )
        print(f"✅ Backup key SUCCESS")
        print(f"Response: {response.content}")
        return True

    except Exception as e:
        print(f"❌ Backup key FAILED: {e}")
        return False


def test_css_selector_task():
    """실제 CSS Selector 작업 테스트"""
    print("\n" + "=" * 80)
    print("3️⃣  CSS Selector 분석 작업 테스트 (Backup Key)")
    print("=" * 80)

    api_key = os.getenv("GOOGLE_API_KEY_BACKUP")
    if not api_key:
        print("⚠️  Using primary key instead")
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ No API keys available")
        return False

    html_sample = """
    <article class="news-article">
        <h1 class="article-title">Breaking News: AI Advances</h1>
        <div class="article-body">
            <p>Artificial intelligence continues to advance...</p>
        </div>
        <time class="publish-date">2025-11-14</time>
    </article>
    """

    prompt = f"""Analyze this HTML and suggest CSS selectors for title, body, and date.

HTML:
{html_sample}

Return JSON format:
{{
    "title": "...",
    "body": "...",
    "date": "..."
}}
"""

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-exp-1206", temperature=0, google_api_key=api_key)

        response = llm.invoke([{"role": "user", "content": prompt}])
        print(f"✅ CSS Selector task SUCCESS")
        print(f"Response:\n{response.content[:500]}...")
        return True

    except Exception as e:
        print(f"❌ CSS Selector task FAILED: {e}")
        return False


def main():
    print("\n" + "=" * 80)
    print("🧪 Gemini 2.5 Pro Experimental (gemini-exp-1206) 백업 키 테스트")
    print("=" * 80)

    results = {
        "primary_key": test_primary_key(),
        "backup_key": test_backup_key(),
        "css_task": test_css_selector_task(),
    }

    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20s}: {status}")

    success_count = sum(results.values())
    total_count = len(results)

    print(
        f"\n총 {total_count}개 테스트 중 {success_count}개 성공 ({success_count/total_count*100:.0f}%)"
    )

    if all(results.values()):
        print("\n🎉 모든 테스트 통과! Gemini 2.5 Pro Experimental 사용 준비 완료!")
    else:
        print("\n⚠️  일부 테스트 실패. 로그를 확인하세요.")

    return results


if __name__ == "__main__":
    results = main()
