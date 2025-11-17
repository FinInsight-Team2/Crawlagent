# CrawlAgent PoC - 라이브 데모 스크립트

작성일: 2025-11-16
총 소요 시간: 5-6분 (3개 시나리오)

---

## 사전 준비 (발표 전)

### 1. 시스템 실행 확인

```bash
# 1. PostgreSQL 실행 확인
docker ps | grep postgres

# 2. Gradio UI 실행 (백그라운드)
cd /Users/charlee/Desktop/Intern/crawlagent
nohup poetry run python -m src.ui.app > /tmp/gradio.log 2>&1 &

# 3. 브라우저 열기
open http://localhost:7860

# 4. 백업용 터미널 준비 (에러 시 로그 확인용)
tail -f /tmp/gradio.log
```

### 2. 데모용 URL 준비

```bash
# 클립보드에 복사해두기
# Donga (UC3):
https://www.donga.com/news/article/all/20231114/122212345/1

# Yonhap (UC2):
https://www.yna.co.kr/view/AKR20231114000100001
```

### 3. Selector 상태 확인

```bash
# 현재 Selector 상태 확인
poetry run python scripts/reset_selector_demo.py --show

# 모두 정상이면 OK
```

---

## Scenario 1: UC3 New Site Discovery (동아일보)

**소요 시간**: 2분
**목표**: Selector가 없을 때 자동으로 발견하는 과정 시연

### Step 1: Selector 삭제 (준비)

```bash
# 터미널에서 실행
cd /Users/charlee/Desktop/Intern/crawlagent
poetry run python scripts/reset_selector_demo.py --uc3-demo
```

**화면 출력**:
```
✅ UC3 시연 준비 완료!
   - 동아일보 Selector를 DB에서 완전 삭제
   - 이제 UC 테스트 탭에서 동아일보 URL 크롤링 시 UC3가 트리거됩니다.
```

### Step 2: Gradio UI에서 크롤링

1. **브라우저에서 http://localhost:7860 접속**
2. **"UC 테스트" 탭 클릭**
3. **URL 입력**:
   ```
   https://www.donga.com/news/article/all/20231114/122212345/1
   ```
4. **"크롤링 시작" 버튼 클릭**

### Step 3: 결과 확인 (설명)

**화면에 표시될 내용**:

```
🔍 UC3: New Site Discovery 트리거
─────────────────────────────────────

이유: DB에 'donga' Selector가 없음

📊 2-Agent Consensus 진행 중...

Claude Sonnet 4.5 (Discoverer):
  Confidence: 0.93
  Proposed Selector:
    - title_selector: section.head_group > h1
    - body_selector: div.view_body
    - date_selector: ul.news_info > li:nth-of-type(2)

GPT-4o (Validator):
  Confidence: 1.00
  Validation: APPROVED

Consensus Score: 0.98 (Threshold: 0.5) ✅

✅ Selector 저장 완료!
📝 DB에 'donga' Selector 추가됨

🔄 UC1 재시도...

✅ 크롤링 성공!
─────────────────────────────────────
Title: 동아일보 뉴스 제목...
Body: 기사 본문 내용...
Quality Score: 100
Processing Time: 5.2초
Cost: $0.033
```

**발표자 멘트**:
> "보시는 것처럼 Selector가 없을 때 Claude와 GPT-4o가 협력하여 자동으로 Selector를 발견했습니다. Consensus 점수는 0.98로 임계값 0.5를 훨씬 넘었고, 이제 DB에 저장되었습니다."

---

## Scenario 2: UC1 Reuse ($0 비용 증명)

**소요 시간**: 1분
**목표**: 같은 사이트를 다시 크롤링하면 LLM 호출 없이 $0 비용

### Step 1: 동일 URL 재입력

1. **"UC 테스트" 탭에서 동일 URL 입력**:
   ```
   https://www.donga.com/news/article/all/20231114/122212345/1
   ```
   (또는 다른 동아일보 URL도 가능)

2. **"크롤링 시작" 버튼 클릭**

### Step 2: 결과 확인 (설명)

**화면에 표시될 내용**:

```
✅ UC1: Quality Gate 통과
─────────────────────────────────────

이유: DB에 'donga' Selector 존재

📝 Selector 정보:
  - title_selector: section.head_group > h1
  - body_selector: div.view_body
  - 성공 횟수: 6회

✅ 크롤링 성공!
─────────────────────────────────────
Title: 동아일보 뉴스 제목...
Body: 기사 본문 내용...
Quality Score: 100
Processing Time: 0.5초 ⚡ (10배 빠름!)
Cost: $0.000 💰 (LLM 호출 없음)
```

**발표자 멘트**:
> "이번에는 처리 시간이 0.5초로 10배 빠르고, 비용은 $0입니다. LLM을 전혀 호출하지 않았기 때문입니다. 이것이 바로 'Learn Once, Reuse Forever' 철학입니다."

---

## Scenario 3: UC2 Self-Healing (연합뉴스)

**소요 시간**: 2-3분
**목표**: Selector가 손상되었을 때 자동으로 수정하는 과정 시연

### Step 1: Selector 손상 (준비)

```bash
# 터미널에서 실행
poetry run python scripts/reset_selector_demo.py --uc2-demo
```

**화면 출력**:
```
✅ UC2 시연 준비 완료!
   - 연합뉴스 body_selector를 'div.wrong-selector-intentional-error-for-uc2-demo'로 수정
   - 이제 UC 테스트 탭에서 연합뉴스 URL 크롤링 시 UC2가 트리거됩니다.
```

### Step 2: Gradio UI에서 크롤링

1. **"UC 테스트" 탭에서 연합뉴스 URL 입력**:
   ```
   https://www.yna.co.kr/view/AKR20231114000100001
   ```

2. **"크롤링 시작" 버튼 클릭**

### Step 3: 결과 확인 (설명)

**화면에 표시될 내용**:

```
❌ UC1: Quality Gate 실패
─────────────────────────────────────

이유: Quality Score 45 < 80 (Threshold)

🔧 UC2: Self-Healing 트리거
─────────────────────────────────────

📊 2-Agent Consensus 진행 중...

Claude Proposer:
  Confidence: 0.85
  Proposed Fix:
    - body_selector: article.article-wrap01

GPT-4o Validator:
  Confidence: 0.90
  Validation: APPROVED

Consensus Score: 0.87 (Threshold: 0.5) ✅

✅ Selector 자동 수정 완료!
📝 DB 'yonhap' body_selector 업데이트됨

🔄 UC1 재시도...

✅ 크롤링 성공!
─────────────────────────────────────
Title: 연합뉴스 제목...
Body: 기사 본문 내용...
Quality Score: 95
Processing Time: 4.8초
Cost: $0.025
```

**발표자 멘트**:
> "Selector가 손상되어 품질 점수가 45점으로 떨어졌습니다. 하지만 UC2 Self-Healing이 자동으로 트리거되어 Claude와 GPT-4o가 협력하여 Selector를 수정했고, 재시도 후 성공했습니다. 이것이 자동 복구 시스템입니다."

---

## 데모 후 복원 (필수!)

```bash
# 모든 Selector를 원래 상태로 복원
poetry run python scripts/reset_selector_demo.py --restore
```

**화면 출력**:
```
🎉 총 2개 Selector 복원 완료!
✅ yonhap Selector 복원 완료 (UPDATE)
✅ donga Selector 복원 완료 (INSERT)
```

---

## 트러블슈팅 (긴급 상황 대비)

### 문제 1: Gradio UI가 안 열림

```bash
# 1. 프로세스 확인
lsof -i :7860

# 2. 강제 종료
kill -9 <PID>

# 3. 재시작
poetry run python -m src.ui.app
```

### 문제 2: DB 연결 실패

```bash
# 1. Docker 확인
docker ps

# 2. DB 재시작
docker-compose restart postgres

# 3. 연결 테스트
docker exec -it crawlagent-postgres-1 psql -U crawlagent -d crawlagent -c "SELECT COUNT(*) FROM selectors;"
```

### 문제 3: UC3가 트리거 안 됨

```bash
# Selector가 이미 있는지 확인
poetry run python scripts/reset_selector_demo.py --show

# 있으면 삭제 후 재시도
poetry run python scripts/reset_selector_demo.py --uc3-demo
```

### 문제 4: 시연 중 에러 발생

**백업 플랜**: 사전 녹화 비디오 재생

```bash
# 미리 녹화해두기 (QuickTime Player)
# 1. Cmd + Shift + 5
# 2. 전체 화면 녹화
# 3. 3개 시나리오 모두 녹화
# 4. /tmp/crawlagent_demo.mov 저장
```

---

## 체크리스트 (발표 당일)

### 발표 30분 전

- [ ] PostgreSQL Docker 실행 확인
- [ ] Gradio UI 실행 확인 (http://localhost:7860)
- [ ] Selector 상태 확인 (`--show`)
- [ ] 데모 URL 클립보드에 복사
- [ ] 백업 비디오 준비 (/tmp/crawlagent_demo.mov)

### 발표 직전 (5분 전)

- [ ] 브라우저 탭 정리 (http://localhost:7860만 열기)
- [ ] 터미널 2개 준비 (1개: 명령어, 1개: 로그)
- [ ] 네트워크 안정성 확인 (OpenAI, Anthropic API)

### 발표 후

- [ ] Selector 복원 (`--restore`)
- [ ] Gradio UI 종료
- [ ] Docker 정리 (`docker-compose down`)

---

## 예상 타이밍

| 시나리오 | 소요 시간 | 누적 |
|---------|---------|------|
| UC3 Discovery | 2분 | 2분 |
| UC1 Reuse | 1분 | 3분 |
| UC2 Self-Healing | 2-3분 | 5-6분 |

**여유 시간**: 발표 총 15분 - 슬라이드 10분 - 데모 6분 = **약 -1분** (빠듯함!)

**권장**: 슬라이드 9분으로 단축 또는 UC2 시나리오 생략 (UC3만으로도 충분)

---

*이 스크립트는 실제 시연 가능한 내용입니다. Mock 데이터 없음.*
