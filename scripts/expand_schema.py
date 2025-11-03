"""
NewsFlow PoC - DB Schema Expansion Script
Phase 2.5: Agent Metadata 지원

실행: python scripts/expand_schema.py
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.storage.database import engine, get_db
from src.storage.models import Base

def expand_schema():
    """
    DB 스키마 확장:
    1. url_patterns 테이블 생성 (UC5: Pagination Learning)
    2. crawl_results 테이블 확장 (메타데이터 필드 추가)
    3. decision_logs 테이블 확장 (agent_metadata JSONB)
    4. selectors 테이블 확장 (confidence_score)
    """

    with engine.connect() as conn:
        print("[*] Phase 2.5: DB 스키마 확장 시작...")

        # 1. url_patterns 테이블 생성
        print("\n[1] url_patterns 테이블 생성 중...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS url_patterns (
                id SERIAL PRIMARY KEY,
                site_name VARCHAR(100) NOT NULL,
                pattern_type VARCHAR(50) NOT NULL,
                url_template VARCHAR(500) NOT NULL,
                confidence_score FLOAT NOT NULL,
                test_urls JSONB,
                verified_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),

                UNIQUE(site_name, pattern_type)
            );
        """))
        print("   [OK] url_patterns 테이블 생성 완료")

        # 2. crawl_results 테이블 확장
        print("\n[2] crawl_results 테이블 확장 중...")

        # article_id 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS article_id VARCHAR(50);
            """))
            print("   [OK] article_id 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] article_id 이미 존재하거나 추가 실패: {e}")

        # author 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS author VARCHAR(200);
            """))
            print("   [OK] author 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] author 이미 존재하거나 추가 실패: {e}")

        # word_count 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS word_count INTEGER;
            """))
            print("   [OK] word_count 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] word_count 이미 존재하거나 추가 실패: {e}")

        # summary 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS summary TEXT;
            """))
            print("   [OK] summary 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] summary 이미 존재하거나 추가 실패: {e}")

        # keywords 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS keywords TEXT[];
            """))
            print("   [OK] keywords 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] keywords 이미 존재하거나 추가 실패: {e}")

        # entities 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS entities JSONB;
            """))
            print("   [OK] entities 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] entities 이미 존재하거나 추가 실패: {e}")

        # data_quality 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS data_quality JSONB;
            """))
            print("   [OK] data_quality 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] data_quality 이미 존재하거나 추가 실패: {e}")

        # processing_metadata 추가
        try:
            conn.execute(text("""
                ALTER TABLE crawl_results
                ADD COLUMN IF NOT EXISTS processing_metadata JSONB;
            """))
            print("   [OK] processing_metadata 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] processing_metadata 이미 존재하거나 추가 실패: {e}")

        # 3. decision_logs 테이블 확장
        print("\n[3] decision_logs 테이블 확장 중...")
        try:
            conn.execute(text("""
                ALTER TABLE decision_logs
                ADD COLUMN IF NOT EXISTS agent_metadata JSONB;
            """))
            print("   [OK] agent_metadata 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] agent_metadata 이미 존재하거나 추가 실패: {e}")

        # 4. selectors 테이블 확장
        print("\n[4] selectors 테이블 확장 중...")
        try:
            conn.execute(text("""
                ALTER TABLE selectors
                ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 1.0;
            """))
            print("   [OK] confidence_score 컬럼 추가")
        except Exception as e:
            print(f"   [WARN] confidence_score 이미 존재하거나 추가 실패: {e}")

        # 5. 인덱스 생성
        print("\n[5] 인덱스 생성 중...")
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_url_patterns_site
                ON url_patterns(site_name);
            """))
            print("   [OK] url_patterns 인덱스 생성")
        except Exception as e:
            print(f"   [WARN] 인덱스 생성 실패: {e}")

        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_crawl_results_article_id
                ON crawl_results(article_id);
            """))
            print("   [OK] crawl_results article_id 인덱스 생성")
        except Exception as e:
            print(f"   [WARN] 인덱스 생성 실패: {e}")

        conn.commit()
        print("\n[OK] Phase 2.5: DB 스키마 확장 완료!")


def verify_schema():
    """스키마 확장 검증"""
    print("\n[CHECK] 스키마 검증 중...")

    with engine.connect() as conn:
        # url_patterns 테이블 확인
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'url_patterns';
        """))
        if result.fetchone():
            print("   [OK] url_patterns 테이블 존재")
        else:
            print("   [ERROR] url_patterns 테이블 없음")

        # crawl_results 컬럼 확인
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'crawl_results'
            AND column_name IN ('article_id', 'author', 'word_count', 'summary', 'keywords', 'entities', 'data_quality', 'processing_metadata');
        """))
        cols = [row[0] for row in result.fetchall()]
        print(f"   [OK] crawl_results 확장 컬럼: {len(cols)}개 ({', '.join(cols)})")

        # decision_logs 컬럼 확인
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'decision_logs'
            AND column_name = 'agent_metadata';
        """))
        if result.fetchone():
            print("   [OK] decision_logs agent_metadata 존재")

        # selectors 컬럼 확인
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'selectors'
            AND column_name = 'confidence_score';
        """))
        if result.fetchone():
            print("   [OK] selectors confidence_score 존재")


if __name__ == "__main__":
    try:
        expand_schema()
        verify_schema()
        print("\n[SUCCESS] Phase 2.5 완료! 다음 Phase로 진행 가능합니다.")
    except Exception as e:
        print(f"\n[ERROR] 에러 발생: {e}")
        import traceback
        traceback.print_exc()
