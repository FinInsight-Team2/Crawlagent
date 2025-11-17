# UC2/UC3 반복 테스트 가이드

## 🎯 목표
UC2 Self-Healing과 UC3 Discovery를 반복적으로 테스트하여 검증

---

## 📁 파일 구조

```
scripts/
├── uc2_strong_damage.py      # UC2: yonhap Selector 강력 손상/복구
├── demo_uc3_reset_donga.py   # UC3: donga Selector 삭제
└── uc_test_cycle.sh          # 대화형 테스트 자동화 스크립트
```

---

## 🚀 빠른 시작

### **방법 1: 대화형 스크립트 사용 (추천)**

```bash
cd /Users/charlee/Desktop/Intern/crawlagent
./scripts/uc_test_cycle.sh
```

메뉴에서 선택:
- `1`: UC2 손상 → Gradio UI에서 테스트
- `2`: UC2 복구
- `3`: UC3 준비 (donga 삭제) → Gradio UI에서 테스트
- `4`: UC2 전체 사이클 (손상 → 테스트 → 복구)
- `5`: UC3 전체 사이클 (삭제 → 테스트)
- `6`: 전체 E2E (UC2 → UC3 → UC1 검증)
- `7`: 현재 Selector 상태 확인
- `8`: 최근 크롤링 결과 확인

---

### **방법 2: 수동 실행**

#### **UC2 Self-Healing 테스트**

**1단계: 준비**
```bash
cd /Users/charlee/Desktop/Intern/crawlagent
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/uc2_strong_damage.py
```

**2단계: Gradio UI 테스트**
- URL: http://localhost:7860
- "실시간 크롤링" 탭
- URL 입력: `https://www.yna.co.kr/view/AKR20251117142000030`
- "크롤링 시작" 클릭

**예상 결과**:
```
→ UC1 FAIL (title/date 추출 실패)
→ UC2 Self-Healing 트리거
→ Claude Proposer (0.90+)
→ GPT-4o Validator (0.90+)
→ Consensus 0.75+
→ Selector UPDATE
→ UC1 Retry → SUCCESS
```

**3단계: 복구**
```bash
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/uc2_strong_damage.py --restore
```

**4단계: UC1 자동 라우팅 검증**
- 같은 URL 다시 크롤링
- UC2 없이 UC1만 실행되어야 함 ($0 비용)

---

#### **UC3 Discovery 테스트**

**1단계: 준비**
```bash
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/demo_uc3_reset_donga.py
```

**2단계: Gradio UI 테스트**
- URL: `https://www.donga.com/news/Economy/article/all/20251117/132786563/1`
- "크롤링 시작" 클릭

**예상 결과**:
```
→ Selector 없음
→ UC3 Discovery
→ Claude Proposer (0.95+)
→ GPT-4o Validator (0.90+)
→ Consensus 0.90+
→ Selector INSERT
→ UC1 Auto-Retry (수정된 워크플로우)
→ 데이터 저장 성공
```

**3단계: UC1 자동 라우팅 검증**
- 같은 URL 다시 크롤링
- UC3 없이 UC1만 실행되어야 함 ($0 비용)

---

## 🔄 반복 테스트 사이클

### **시나리오 1: UC2 단독 검증 (3회 반복)**

```bash
for i in {1..3}; do
    echo "=== Round $i ==="

    # 손상
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/uc2_strong_damage.py

    # [수동] Gradio UI에서 테스트
    read -p "Gradio UI 테스트 완료 후 Enter..."

    # 복구
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/uc2_strong_damage.py --restore

    echo ""
done
```

### **시나리오 2: UC3 단독 검증 (3회 반복)**

```bash
for i in {1..3}; do
    echo "=== Round $i ==="

    # 삭제
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/demo_uc3_reset_donga.py

    # [수동] Gradio UI에서 테스트
    read -p "Gradio UI 테스트 완료 후 Enter..."

    echo ""
done
```

### **시나리오 3: E2E 통합 검증**

```
1. UC2 Self-Healing 테스트
2. UC1 자동 라우팅 확인 (yonhap)
3. UC3 Discovery 테스트
4. UC1 자동 라우팅 확인 (donga)
5. 전체 워크플로우 검증 완료
```

---

## 📊 상태 확인 명령어

### **현재 Selector 상태**

```bash
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python -c "
from sqlalchemy.orm import Session
from src.storage.models import Selector
from src.storage.database import engine

db = Session(engine)

# yonhap
yonhap = db.query(Selector).filter(Selector.site_name == 'yonhap').first()
print(f'yonhap: {yonhap.title_selector}')
print(f'  failure_count: {yonhap.failure_count}')

# donga
donga = db.query(Selector).filter(Selector.site_name == 'donga').first()
if donga:
    print(f'donga: {donga.title_selector}')
else:
    print('donga: 없음 (UC3 준비 완료)')

db.close()
"
```

### **최근 크롤링 결과**

```bash
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python -c "
from sqlalchemy.orm import Session
from src.storage.models import CrawlResult
from src.storage.database import engine
from datetime import datetime, timedelta

db = Session(engine)

recent = datetime.utcnow() - timedelta(minutes=10)
results = db.query(CrawlResult).filter(
    CrawlResult.created_at >= recent
).order_by(CrawlResult.created_at.desc()).limit(5).all()

for r in results:
    print(f'{r.site_name:10s} | Q={r.quality_score:3.0f} | {r.title[:50] if r.title else \"N/A\"}')

db.close()
"
```

---

## ✅ 성공 기준

### **UC2 Self-Healing**
- ✅ UC1 실패 감지 (quality < 80)
- ✅ UC2 트리거 (failure_count >= 3)
- ✅ Consensus 0.75 이상
- ✅ Selector 업데이트 성공
- ✅ UC1 재시도 성공 (quality = 100)
- ✅ 다음 크롤링 시 UC1 직접 라우팅

### **UC3 Discovery**
- ✅ Selector 없음 감지
- ✅ UC3 트리거
- ✅ Consensus 0.50 이상
- ✅ Selector INSERT 성공
- ✅ UC1 자동 재실행 (수정된 워크플로우)
- ✅ 데이터 수집 성공 (quality = 100)
- ✅ 다음 크롤링 시 UC1 직접 라우팅

---

## 🐛 트러블슈팅

### **UC2가 트리거되지 않음**

**증상**: UC1이 계속 성공함 (quality=100)

**원인**: UC1의 강력한 Fallback 로직
- Title: `og:title` meta tag
- Date: `article:published_time` meta tag
- Body: Trafilatura 자동 추출

→ Selector가 손상되어도 fallback이 성공하여 UC2가 트리거되지 않음

**해결**: UC2_DEMO_MODE 사용 (uc_test_cycle.sh가 자동 처리)

```bash
# 방법 1: 자동화 스크립트 (추천)
./scripts/uc_test_cycle.sh
# → 선택 1번 선택 시 UC2_DEMO_MODE 자동 활성화

# 방법 2: 수동 설정
# .env 파일 수정
UC2_DEMO_MODE=true  # UC2 테스트용 (Fallback 비활성화)
UC2_DEMO_MODE=false # 프로덕션용 (Fallback 활성화)
```

**주의**: UC2_DEMO_MODE=true 상태에서는 Fallback이 비활성화되므로 프로덕션 사용 금지!

### **UC3가 데이터를 저장하지 않음**

**증상**: Selector는 생성되지만 CrawlResult 없음

**원인**: 이전 워크플로우 (UC3 → END)

**해결**: ✅ 이미 수정됨 (UC3 → UC1 Auto-Retry)

---

## 📈 테스트 로그 확인

### **실시간 서버 로그**

```bash
# 서버 로그에서 UC 관련 필터링
# (서버가 백그라운드로 실행 중이라면 불가능)

# 대신 Gradio UI 하단의 로그 출력 확인
```

### **LangSmith 트레이스**

- URL: https://smith.langchain.com
- 프로젝트: `crawlagent-poc`
- 각 실행의 상세 트레이스 확인 가능

---

## 🎓 학습 포인트

1. **UC2 Self-Healing**: 손상된 Selector를 2-Agent Consensus로 자동 복구
2. **UC3 Discovery**: 새 사이트를 자동으로 학습하고 Selector 생성
3. **UC1 Auto-Routing**: UC2/UC3 완료 후 추가 비용 없이 자동 라우팅
4. **Fallback Resilience**: Meta 태그와 Trafilatura로 강건한 추출
5. **Consensus Mechanism**: Claude + GPT-4o 교차 검증으로 신뢰성 확보

---

**작성일**: 2025-11-18
**버전**: v1.0
