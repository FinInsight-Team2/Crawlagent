"""
NewsFlow PoC - Environment Verification Script
Purpose: Pre-session health check before starting UC1/UC2 development

Run: python scripts/verify_environment.py
"""

import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_postgres():
    """Check PostgreSQL container status"""
    print("[1/5] Checking PostgreSQL...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=newsflow-postgres", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "Up" in result.stdout:
            print("   [OK] PostgreSQL container is running")
            return True
        else:
            print("   [ERROR] PostgreSQL container not running")
            print("   [FIX] Run: docker-compose up -d")
            return False
    except FileNotFoundError:
        print("   [ERROR] Docker not found")
        return False
    except Exception as e:
        print(f"   [ERROR] Failed to check Docker: {e}")
        return False

def check_database_data():
    """Check if crawl data exists"""
    print("\n[2/5] Checking Database Data...")
    try:
        from src.storage.database import get_db
        from src.storage.models import CrawlResult

        db = next(get_db())
        try:
            count = db.query(CrawlResult).filter_by(site_name='yonhap').count()
            if count > 0:
                print(f"   [OK] Found {count} articles in database")

                # Quality score check
                results = db.query(CrawlResult).filter_by(site_name='yonhap').all()
                scores = [r.quality_score for r in results if r.quality_score]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    print(f"   [OK] Average quality score: {avg_score:.1f}")
                return True
            else:
                print("   [ERROR] No articles found in database")
                print("   [FIX] Run: scrapy crawl yonhap")
                return False
        finally:
            db.close()
    except Exception as e:
        print(f"   [ERROR] Failed to query database: {e}")
        print("   [FIX] Check PostgreSQL connection and schema")
        return False

def check_dependencies():
    """Check Python dependencies"""
    print("\n[3/5] Checking Python Dependencies...")
    try:
        import langgraph
        print(f"   [OK] langgraph {langgraph.__version__}")
    except ImportError:
        print("   [ERROR] langgraph not installed")
        return False

    try:
        import gradio
        print(f"   [OK] gradio {gradio.__version__}")
    except ImportError:
        print("   [ERROR] gradio not installed")
        return False

    try:
        import scrapy
        print(f"   [OK] scrapy {scrapy.__version__}")
    except ImportError:
        print("   [ERROR] scrapy not installed")
        return False

    try:
        from langchain_openai import ChatOpenAI
        print("   [OK] langchain-openai installed")
    except ImportError:
        print("   [ERROR] langchain-openai not installed")
        return False

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("   [OK] langchain-google-genai installed")
    except ImportError:
        print("   [ERROR] langchain-google-genai not installed")
        return False

    return True

def check_documentation():
    """Check if documentation files exist"""
    print("\n[4/5] Checking Documentation...")

    docs_dir = Path(__file__).parent.parent.parent / "claudedocs"

    required_docs = [
        "claude.md",
        "newsflow-session-handoff.md",
        "newsflow-codebase-quality-report.md",
        "newsflow-langgraph-patterns-from-learning.md"
    ]

    all_exist = True
    for doc in required_docs:
        doc_path = docs_dir / doc
        if doc_path.exists():
            print(f"   [OK] {doc}")
        else:
            print(f"   [ERROR] {doc} not found")
            all_exist = False

    return all_exist

def check_environment_vars():
    """Check environment variables"""
    print("\n[5/5] Checking Environment Variables...")

    try:
        from dotenv import load_dotenv
        import os

        load_dotenv()

        required_vars = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "DATABASE_URL"]
        all_set = True

        for var in required_vars:
            value = os.getenv(var)
            if value and value != f"{var.lower()}...":
                print(f"   [OK] {var} is set")
            else:
                print(f"   [WARN] {var} not configured in .env")
                all_set = False

        return all_set
    except Exception as e:
        print(f"   [ERROR] Failed to load .env: {e}")
        return False

def main():
    """Run all verification checks"""
    print_header("NewsFlow PoC - Environment Verification")

    results = {
        "postgres": check_postgres(),
        "database": check_database_data(),
        "dependencies": check_dependencies(),
        "documentation": check_documentation(),
        "env_vars": check_environment_vars()
    }

    print_header("Verification Summary")

    all_passed = all(results.values())

    if all_passed:
        print("   [SUCCESS] All checks passed!")
        print("\n   You are ready to start UC1 development.")
        print("\n   Next steps:")
        print("   1. Complete learning (PRJ_02, 04, 05)")
        print("   2. Read claudedocs/newsflow-session-handoff.md")
        print("   3. Start new session with: @claude.md 읽고 이어서 진행하자")
    else:
        print("   [WARNING] Some checks failed.")
        print("\n   Failed checks:")
        for check, passed in results.items():
            if not passed:
                print(f"   - {check}")
        print("\n   Fix the issues above before starting UC1 development.")

    print("\n" + "="*60 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
