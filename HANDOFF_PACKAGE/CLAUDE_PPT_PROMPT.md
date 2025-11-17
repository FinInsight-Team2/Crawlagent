# CrawlAgent PPT 제작용 Claude 프롬프트

## Claude.ai 프로젝트 설정

### 업로드할 파일 (순서대로)
1. `03_PRESENTATION_SLIDES_V2.md` (필수 - PPT 스크립트)
2. `04_SKILL_INTEGRATED.md` (필수 - 로직 설명)
3. `02_PRD_v2_RENEWED.md` (참고 - 트러블슈팅)
4. `01_EXECUTIVE_SUMMARY.md` (참고 - ROI 데이터)

---

## Claude에게 보낼 프롬프트

```
안녕하세요! CrawlAgent PoC 프로젝트 발표용 PowerPoint 슬라이드를 만들어주세요.

## 배경
- 프로젝트: CrawlAgent (Multi-Agent Web Crawling System)
- 목표: 경영진 + 개발팀에게 3주간 개발 성과 발표
- 발표 시간: 20분
- 청중: 기술적 배경 있음 (개발자 50%, 경영진 50%)

## 요구사항

### 1. 슬라이드 구성 (12장)
업로드한 `03_PRESENTATION_SLIDES_V2.md` 파일을 기반으로:

1. **타이틀 슬라이드**
   - 제목: "CrawlAgent PoC - Phase 1 Complete"
   - 부제: "Learn Once, Reuse Forever"
   - 날짜: 2025-11-18

2. **문제 정의** (Slide 2)
   - 기존 LLM 크롤링 비용: $30/1,000 articles
   - 사이트 구조 변경 시 다운타임 발생
   - 신규 사이트 추가 시 수동 작업 30분

3. **솔루션 개요** (Slide 3)
   - UC1: Quality Gate (Rule-based, $0, 98%+ success)
   - UC2: Self-Healing (2-Agent Consensus, $0.002, 31.7s)
   - UC3: Discovery (Zero-Shot, $0.033, 100% success)
   - Mermaid 다이어그램 포함 (UC1 → Supervisor → UC2 → UC3)

4. **UC1 로직 상세** (Slide 4)
   - JSON-LD Smart Extraction (95%+ 사이트)
   - 5W1H Quality 검증 (Title 20%, Body 50%, Date 20%)
   - Python 코드 스니펫 포함:
     ```python
     if json_ld.quality >= 0.7:
         title = json_ld["headline"]
         body = json_ld["articleBody"]
         # LLM 호출 SKIP → 비용 $0
     ```

5. **UC2 로직 상세** (Slide 5)
   - 2-Agent Consensus (Claude + GPT-4o)
   - Site-specific HTML Hints (실시간 HTML 분석)
   - Weighted Consensus 공식:
     ```
     Consensus = Claude * 0.3 + GPT-4o * 0.3 + Quality * 0.4
     ```
   - Before/After: Consensus 0.36 → 0.88

6. **UC3 로직 상세** (Slide 6)
   - Zero-Shot Learning (Few-Shot Examples 활용)
   - Discoverer + Validator 패턴
   - UC1 Auto-Retry (데이터 수집 보장)

7. **트러블슈팅 사례** (Slide 7-8)
   - Issue #1: UC2 Infinite Loop (retry_count 버그)
   - Issue #2: UC2 Consensus Failure (0.36 → 0.88)
   - Issue #3: UC3 Data Not Saved (UC1 retry 추가)
   - Issue #4: Claude API JSON Error (Multi-provider Fallback)
   - 각 이슈마다: 증상 → 근본 원인 → 해결 방법 → 결과

8. **검증 결과** (Slide 9)
   - 총 크롤링: 459개 기사
   - 성공률: 100%
   - 평균 Quality: 97.44
   - 8개 SSR 사이트 검증 (yonhap 453개, donga 1개, bbc 2개 등)
   - UC별 성능:
     - UC1: 1.5s, $0
     - UC2: 31.7s, $0.002
     - UC3: 5-42s, $0.033

9. **ROI 분석** (Slide 10)
   - 기존: $30,000/년 (100만 기사)
   - CrawlAgent: $0.35/년
   - 절감: 99.89%
   - ROI: 94,627x

10. **4가지 핵심 혁신** (Slide 11)
    - Site-specific HTML Hints
    - JSON-LD Smart Extraction
    - 2-Agent Consensus
    - Multi-provider Fallback

11. **Phase 2 로드맵** (Slide 12)
    - Q1 2026: SPA 지원, 80% 테스트 커버리지
    - Q2 2026: Kubernetes, Multi-tenancy
    - Q3-Q4 2026: Multi-language, API-first

12. **Q&A 슬라이드**

### 2. 디자인 가이드라인
- **색상**:
  - Primary: #2563EB (Blue)
  - Success: #10B981 (Green)
  - Warning: #F59E0B (Orange)
  - Error: #EF4444 (Red)
- **폰트**:
  - 제목: Sans-serif, Bold, 32pt
  - 본문: Sans-serif, Regular, 16pt
  - 코드: Monospace, 12pt
- **레이아웃**:
  - 각 슬라이드는 3-5개 bullet points
  - 코드 스니펫은 최대 10줄
  - 다이어그램은 슬라이드 1/2 크기

### 3. 출력 형식
다음 중 하나를 선택해주세요:

**옵션 A**: Markdown 형식 (Marp 호환)
```markdown
---
marp: true
theme: default
---

# Slide 1 Title
- Bullet 1
- Bullet 2
```

**옵션 B**: Google Slides 복사용 (각 슬라이드를 구분된 섹션으로)

**옵션 C**: PowerPoint XML (직접 .pptx 생성 가능한 경우)

### 4. 특별 요청
- 트러블슈팅 사례는 **Before/After 비교** 형식으로
- 코드 스니펫은 **주석 포함** (한글)
- 다이어그램은 **Mermaid 코드 제공** (나중에 PNG로 변환)
- 각 슬라이드에 **발표자 노트** 추가 (what to say)

## 참고 파일
- `03_PRESENTATION_SLIDES_V2.md`: 슬라이드 스크립트 (이미 완성)
- `04_SKILL_INTEGRATED.md`: UC1/UC2/UC3 로직 상세
- `02_PRD_v2_RENEWED.md`: 트러블슈팅 사례 상세
- `01_EXECUTIVE_SUMMARY.md`: ROI 및 비즈니스 임팩트

---

시작해주세요!
```

---

## Claude 응답 후 작업

### 1. Marp으로 PPT 변환 (VSCode)
```bash
# VSCode Extension 설치
1. "Marp for VS Code" 검색 → 설치
2. Command Palette (Cmd+Shift+P)
3. "Marp: Export Slide Deck" → PPTX 선택
```

### 2. Google Slides로 수동 작성
```
1. https://slides.google.com
2. "Blank" 프레젠테이션 생성
3. Claude가 제공한 각 슬라이드 내용 복사/붙여넣기
4. 다이어그램은 Excalidraw로 재작성
5. File → Download → Microsoft PowerPoint (.pptx)
```

### 3. 다이어그램 렌더링
```
# Mermaid 다이어그램을 PNG로 변환
1. https://mermaid.live 접속
2. Claude가 제공한 Mermaid 코드 붙여넣기
3. "Download PNG" 클릭
4. PPT에 이미지 삽입
```

---

## 체크리스트

PPT 완성 전 확인 사항:
- [ ] 12장 슬라이드 모두 작성
- [ ] 각 UC별 로직 코드 스니펫 포함
- [ ] 트러블슈팅 4가지 사례 포함
- [ ] 검증 결과 데이터 (459개, 8개 사이트)
- [ ] ROI 계산 (99.89% 절감)
- [ ] 다이어그램 3개 이상 (워크플로우, Consensus, Fallback)
- [ ] 발표자 노트 작성
- [ ] 20분 발표 시간 맞춤 (슬라이드당 1.5-2분)

---

## 문의
- CrawlAgent Team
- Email: crawlagent-team@example.com
