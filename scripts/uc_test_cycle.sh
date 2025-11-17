#!/bin/bash
# UC2/UC3 반복 테스트 자동화 스크립트

set -e  # Exit on error

CRAWLAGENT_ROOT="/Users/charlee/Desktop/Intern/crawlagent"
cd "$CRAWLAGENT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo -e "${BLUE}UC2/UC3 반복 테스트 사이클${NC}"
echo "========================================================================"
echo ""

# Function to show menu
show_menu() {
    echo -e "${YELLOW}다음 작업을 선택하세요:${NC}"
    echo ""
    echo "  [UC2 Self-Healing 테스트]"
    echo "  1) UC2 준비: yonhap Selector 강력 손상"
    echo "  2) UC2 복구: yonhap Selector 원상 복구"
    echo ""
    echo "  [UC3 Discovery 테스트]"
    echo "  3) UC3 준비: donga Selector 삭제"
    echo ""
    echo "  [빠른 사이클]"
    echo "  4) UC2 사이클: 손상 → [테스트] → 복구"
    echo "  5) UC3 사이클: 삭제 → [테스트]"
    echo "  6) 전체 사이클: UC2 → UC3 → UC1 검증"
    echo ""
    echo "  [상태 확인]"
    echo "  7) 현재 Selector 상태 확인"
    echo "  8) 최근 크롤링 결과 확인"
    echo ""
    echo "  0) 종료"
    echo ""
    echo -n "선택: "
}

# Function: UC2 Damage
uc2_damage() {
    echo -e "${YELLOW}[UC2] yonhap Selector 강력 손상 중...${NC}"
    PYTHONPATH="$CRAWLAGENT_ROOT" poetry run python scripts/uc2_strong_damage.py
    echo ""

    # Enable UC2_DEMO_MODE
    echo -e "${YELLOW}[UC2] UC2_DEMO_MODE 활성화 중 (Fallback 비활성화)...${NC}"
    sed -i '' 's/UC2_DEMO_MODE=false/UC2_DEMO_MODE=true/' "$CRAWLAGENT_ROOT/.env"
    echo ""

    echo -e "${GREEN}✅ UC2 준비 완료!${NC}"
    echo ""
    echo -e "${BLUE}다음 단계:${NC}"
    echo "  1. Gradio UI (http://localhost:7860) 열기"
    echo "  2. '실시간 크롤링' 탭"
    echo "  3. URL: https://www.yna.co.kr/view/AKR20251117142000030"
    echo "  4. '크롤링 시작' 클릭"
    echo "  5. UC2 Self-Healing 관찰"
    echo ""
}

# Function: UC2 Restore
uc2_restore() {
    echo -e "${YELLOW}[UC2] yonhap Selector 복구 중...${NC}"
    PYTHONPATH="$CRAWLAGENT_ROOT" poetry run python scripts/uc2_strong_damage.py --restore
    echo ""

    # Disable UC2_DEMO_MODE
    echo -e "${YELLOW}[UC2] UC2_DEMO_MODE 비활성화 중 (Fallback 재활성화)...${NC}"
    sed -i '' 's/UC2_DEMO_MODE=true/UC2_DEMO_MODE=false/' "$CRAWLAGENT_ROOT/.env"
    echo ""

    echo -e "${GREEN}✅ UC2 복구 완료!${NC}"
    echo ""
}

# Function: UC3 Reset
uc3_reset() {
    echo -e "${YELLOW}[UC3] donga Selector 삭제 중...${NC}"
    PYTHONPATH="$CRAWLAGENT_ROOT" poetry run python scripts/demo_uc3_reset_donga.py
    echo ""
    echo -e "${GREEN}✅ UC3 준비 완료!${NC}"
    echo ""
    echo -e "${BLUE}다음 단계:${NC}"
    echo "  1. Gradio UI (http://localhost:7860) 열기"
    echo "  2. '실시간 크롤링' 탭"
    echo "  3. URL: https://www.donga.com/news/Economy/article/all/20251117/132786563/1"
    echo "  4. '크롤링 시작' 클릭"
    echo "  5. UC3 Discovery → UC1 Auto-Retry 관찰"
    echo ""
}

# Function: UC2 Full Cycle
uc2_cycle() {
    echo -e "${BLUE}========== UC2 전체 사이클 시작 ==========${NC}"
    echo ""

    # Step 1: Damage
    uc2_damage

    # Wait for user
    echo -e "${YELLOW}Gradio UI에서 테스트를 완료한 후 Enter를 누르세요...${NC}"
    read -r

    # Step 2: Restore
    uc2_restore

    echo -e "${GREEN}========== UC2 사이클 완료 ==========${NC}"
    echo ""
}

# Function: UC3 Full Cycle
uc3_cycle() {
    echo -e "${BLUE}========== UC3 전체 사이클 시작 ==========${NC}"
    echo ""

    # Step 1: Reset
    uc3_reset

    # Wait for user
    echo -e "${YELLOW}Gradio UI에서 테스트를 완료한 후 Enter를 누르세요...${NC}"
    read -r

    echo -e "${GREEN}========== UC3 사이클 완료 ==========${NC}"
    echo ""
    echo -e "${BLUE}다음 테스트: 같은 URL로 UC1 자동 라우팅 확인${NC}"
    echo "  → https://www.donga.com/news/Economy/article/all/20251117/132786563/1"
    echo "  → UC1으로 직접 라우팅되어야 함 (\$0 비용)"
    echo ""
}

# Function: Full E2E Cycle
full_cycle() {
    echo -e "${BLUE}========== 전체 E2E 사이클 시작 ==========${NC}"
    echo ""

    # UC2
    echo -e "${YELLOW}[1/3] UC2 Self-Healing 테스트${NC}"
    uc2_cycle

    # UC3
    echo -e "${YELLOW}[2/3] UC3 Discovery 테스트${NC}"
    uc3_cycle

    # UC1 Verification
    echo -e "${YELLOW}[3/3] UC1 자동 라우팅 검증${NC}"
    echo "  테스트 1: yonhap URL → UC1 직접 라우팅"
    echo "  테스트 2: donga URL → UC1 직접 라우팅"
    echo ""

    echo -e "${GREEN}========== 전체 E2E 사이클 완료 ==========${NC}"
    echo ""
}

# Function: Check Status
check_status() {
    echo -e "${BLUE}========== 현재 Selector 상태 ==========${NC}"
    PYTHONPATH="$CRAWLAGENT_ROOT" poetry run python -c "
from sqlalchemy.orm import Session
from src.storage.models import Selector
from src.storage.database import engine

db = Session(engine)

# yonhap
yonhap = db.query(Selector).filter(Selector.site_name == 'yonhap').first()
if yonhap:
    print(f'yonhap:')
    print(f'  title: {yonhap.title_selector}')
    print(f'  body: {yonhap.body_selector}')
    print(f'  success: {yonhap.success_count}, failure: {yonhap.failure_count}')

    if 'nonexistent' in yonhap.title_selector:
        print('  ⚠️  손상됨 (UC2 준비 상태)')
    elif 'wrong' in yonhap.title_selector:
        print('  ⚠️  약하게 손상됨')
    else:
        print('  ✅ 정상')

print()

# donga
donga = db.query(Selector).filter(Selector.site_name == 'donga').first()
if donga:
    print(f'donga:')
    print(f'  title: {donga.title_selector}')
    print(f'  success: {donga.success_count}, failure: {donga.failure_count}')
    print('  ✅ 존재함')
else:
    print('donga:')
    print('  ❌ Selector 없음 (UC3 준비 상태)')

db.close()
"
    echo ""
}

# Function: Check Recent Results
check_results() {
    echo -e "${BLUE}========== 최근 크롤링 결과 (10건) ==========${NC}"
    PYTHONPATH="$CRAWLAGENT_ROOT" poetry run python -c "
from sqlalchemy.orm import Session
from src.storage.models import CrawlResult
from src.storage.database import engine
from datetime import datetime, timedelta

db = Session(engine)

recent_time = datetime.utcnow() - timedelta(hours=1)
results = db.query(CrawlResult).filter(
    CrawlResult.created_at >= recent_time
).order_by(CrawlResult.created_at.desc()).limit(10).all()

for r in results:
    time_str = r.created_at.strftime('%H:%M:%S')
    print(f'{time_str} | {r.site_name:10s} | Q={r.quality_score:3.0f} | {r.title[:40] if r.title else \"N/A\"}')

db.close()
"
    echo ""
}

# Main loop
while true; do
    echo ""
    show_menu
    read -r choice
    echo ""

    case $choice in
        1)
            uc2_damage
            ;;
        2)
            uc2_restore
            ;;
        3)
            uc3_reset
            ;;
        4)
            uc2_cycle
            ;;
        5)
            uc3_cycle
            ;;
        6)
            full_cycle
            ;;
        7)
            check_status
            ;;
        8)
            check_results
            ;;
        0)
            echo -e "${GREEN}종료합니다.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}잘못된 선택입니다.${NC}"
            ;;
    esac

    echo -e "${YELLOW}계속하려면 Enter를 누르세요...${NC}"
    read -r
done
