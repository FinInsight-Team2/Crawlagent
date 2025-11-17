# Archived Documents

이 디렉토리는 프로젝트 개발 과정에서 생성된 초기 기획서 및 다이어그램을 보관합니다.

## 파일 목록

### `original_proposal.pdf`
- **파일명**: `ai_web_crawler_proposal_20251020061635.pdf` (원본)
- **생성일**: 2025년 10월 20일
- **설명**: CrawlAgent 프로젝트의 최초 기획서
- **용도**: 초기 비전, 요구사항, 아키텍처 설계 참고
- **참고사항**:
  - 현재 구현된 프로젝트는 **MVP/PoC** 수준
  - 기획서의 모든 기능을 구현하지 못한 것은 당연함
  - Phase 1 완료 시점 기준 약 **65% 구현**

### `master_workflow_graph.png`
- **파일명**: `master_workflow_graph.png` (원본)
- **생성일**: 2025년 11월 10일
- **설명**: CrawlAgent 워크플로우 다이어그램
- **내용**:
  - LangGraph Supervisor Pattern
  - UC1 (Quality Gate) / UC2 (Self-Healing) / UC3 (Discovery) 흐름
- **일치도**: 현재 구현과 **90% 일치**
- **차이점**:
  - UI 시각화 미구현 (기획서 p.21 "페이지 미리보기")
  - Distributed Supervisor 추가됨 (기획서에 없었으나 개선사항)

## 기획서 vs 구현 비교

| 항목 | 기획서 요구사항 | 현재 구현 (Phase 1) |
|------|----------------|---------------------|
| **UC1 Quality Gate** | ✅ | ✅ 100% 완료 |
| **UC2 Self-Healing** | ✅ | ✅ 90% 완료 |
| **UC3 Discovery** | ✅ | ✅ 85% 완료 |
| **SPA 지원** | ✅ Playwright | ❌ 미구현 (Phase 2) |
| **UI 자동 필드 제안** | ✅ | ❌ 미구현 (Phase 2) |
| **다양한 사이트** | ✅ 커뮤니티, 쇼핑몰 | ⚠️ 뉴스 전용 (Phase 1) |

## 참고 문서

- **현재 상태**: [../PRD.md](../PRD.md)
- **아키텍처**: [../ARCHITECTURE_EXPLANATION.md](../ARCHITECTURE_EXPLANATION.md)
- **향후 계획**: [../EXPANSION_ROADMAP.md](../EXPANSION_ROADMAP.md) (예정)

---

**아카이빙 날짜**: 2025-11-17
**아카이빙 사유**: 프로젝트 전달 준비 및 문서 정리
