# PPT 슬라이드 메모

## 슬라이드: "신뢰성 검증" (1장)

**제목:** Self-Healing 진위성 보장

**내용:**
- ✅ Selector Health Check (프로덕션급)
  - Fallback 유지 + Selector 손상 독립 감지
  - Quality=100이어도 UC2 트리거
  
- 🔍 투명성 보장
  - 전체 코드 공개 가능
  - LangSmith 트레이스 검증
  - 실시간 API 호출 확인

**메시지:** "시뮬레이션이 아닌 실제 Self-Healing"

---

## 라이브 데모 시 보여줄 것

1. Gradio UI 로그: `Selector Health: damage_count=3/3`
2. Chrome DevTools: Claude/GPT-4o API 호출
3. LangSmith: 전체 워크플로우 트레이스

**시간:** 1분 이내

---

작성일: 2025-11-18
용도: crawlagent-presentation.md 참고용
