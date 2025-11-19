# CrawlAgent Documentation

**Last Updated**: 2025-11-19
**Version**: 1.0

---

## 📁 문서 구조

```
docs/
├── handoff/              # 핸드오프 관련 문서
├── development/          # 개발 가이드
├── reference/            # 참고 자료
├── archived/             # 구버전 문서
├── ui_diagrams/          # UI 다이어그램
└── workflow_diagrams/    # 워크플로우 다이어그램
```

---

## 📋 핸드오프 문서 (handoff/)

프로젝트 인수인계를 위한 필수 문서

| 문서 | 설명 | 우선순위 |
|------|------|----------|
| [FINAL_HANDOFF_REPORT.md](handoff/FINAL_HANDOFF_REPORT.md) | 최종 핸드오프 보고서 (완료 작업, 패키지 정보) | ⭐⭐⭐ |
| [QUICK_START_HANDOFF.md](handoff/QUICK_START_HANDOFF.md) | 10분 빠른 시작 가이드 | ⭐⭐⭐ |
| [HANDOFF_SUMMARY.md](handoff/HANDOFF_SUMMARY.md) | 최종 변경사항 요약 | ⭐⭐⭐ |
| [HANDOFF_CHECKLIST.md](handoff/HANDOFF_CHECKLIST.md) | 전달자/수신자 체크리스트 | ⭐⭐⭐ |
| [PROJECT_ANALYSIS_AND_HANDOFF.md](handoff/PROJECT_ANALYSIS_AND_HANDOFF.md) | 프로젝트 분석 및 핸드오프 가이드 | ⭐⭐ |

---

## 🛠️ 개발 가이드 (development/)

개발자를 위한 기술 문서

| 문서 | 설명 | 대상 |
|------|------|------|
| [CLAUDE_SKILLS_INTEGRATION.md](development/CLAUDE_SKILLS_INTEGRATION.md) | Claude Skills 통합 가이드 | AI 개발자 |
| [MANUAL_TEST_GUIDE.md](development/MANUAL_TEST_GUIDE.md) | 수동 테스트 가이드 | QA/테스터 |
| [TESTING.md](development/TESTING.md) | 테스트 가이드 (Unit/Integration/E2E) | 개발자 |
| [UC_TEST_GUIDE.md](development/UC_TEST_GUIDE.md) | Use Case별 테스트 가이드 | QA/개발자 |

---

## 📚 참고 자료 (reference/)

프로젝트 기획 및 기술 자료

| 문서 | 설명 | 용도 |
|------|------|------|
| [PRD_v2_RENEWED.md](reference/PRD_v2_RENEWED.md) | 제품 요구사항 문서 v2 | 기획 참고 |
| [PRESENTATION_SLIDES_V2.md](reference/PRESENTATION_SLIDES_V2.md) | 프레젠테이션 슬라이드 v2 | 발표 자료 |
| [SKILL_INTEGRATED.md](reference/SKILL_INTEGRATED.md) | 기술 통합 문서 | 아키텍처 참고 |
| [FILE_ORGANIZATION_REPORT.md](reference/FILE_ORGANIZATION_REPORT.md) | 파일 구조 보고서 | 프로젝트 구조 |
| [DATABASE_SCHEMA.md](reference/DATABASE_SCHEMA.md) | DB 스키마 정의 | DB 참고 |
| [CONFIGURATION.md](reference/CONFIGURATION.md) | 환경변수 설정 가이드 | 설정 참고 |

---

## 🗄️ 아카이브 (archived/)

구버전 문서 보관소

- `docs_old/` - 이전 버전의 docs/ 파일들
  - PRESENTATION_SLIDES.md (v1)
  - PRD.md (v1)
  - ppt_notes.md, ppt_troubleshooting_notes.md

---

## 🎨 다이어그램

### UI 다이어그램 (ui_diagrams/)
- Gradio UI 구조도
- Tab별 화면 설계

### 워크플로우 다이어그램 (workflow_diagrams/)
- Master Workflow 플로우차트
- UC1/UC2/UC3 프로세스 다이어그램

---

## 📖 읽기 순서 (신규 팀원용)

### 1단계: 핸드오프 이해 (30분)
1. [FINAL_HANDOFF_REPORT.md](handoff/FINAL_HANDOFF_REPORT.md) (15분)
2. [QUICK_START_HANDOFF.md](handoff/QUICK_START_HANDOFF.md) (10분)
3. [HANDOFF_CHECKLIST.md](handoff/HANDOFF_CHECKLIST.md) (5분)

### 2단계: 프로젝트 개요 (20분)
1. 루트의 [README.md](../README.md) (10분)
2. [reference/PRD_v2_RENEWED.md](reference/PRD_v2_RENEWED.md) (10분)

### 3단계: 개발 환경 (30분)
1. [reference/CONFIGURATION.md](reference/CONFIGURATION.md) (15분)
2. [development/TESTING.md](development/TESTING.md) (15분)

### 4단계: 심화 학습 (선택)
1. [SKILL_INTEGRATED.md](reference/SKILL_INTEGRATED.md) - 기술 아키텍처
2. [CLAUDE_SKILLS_INTEGRATION.md](development/CLAUDE_SKILLS_INTEGRATION.md) - AI 통합

---

## 🔗 관련 문서 링크

### 루트 레벨 핵심 문서
- [README.md](../README.md) - 프로젝트 메인 문서 (필수)

### HANDOFF_PACKAGE
- [HANDOFF_PACKAGE/](../HANDOFF_PACKAGE/) - 12개 프레젠테이션 문서

---

## 📝 문서 업데이트 정책

### 문서 버전 관리
- **v2** 파일이 최신 버전
- 구버전은 `archived/docs_old/`에 보관
- 중복 방지: HANDOFF_PACKAGE에 있으면 docs/에서 제거

### 새 문서 추가 시
1. 카테고리 결정 (handoff/development/reference)
2. 적절한 디렉토리에 추가
3. 이 README.md 업데이트

### 문서 수정 시
- Last Updated 날짜 업데이트
- 중요 변경사항은 CHANGELOG.md에 기록 (해당 시)

---

**문의**: [HANDOFF_CHECKLIST.md](handoff/HANDOFF_CHECKLIST.md) 참고
