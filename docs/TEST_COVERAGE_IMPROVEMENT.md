# Test Coverage 개선 보고서

**작성일**: 2025-11-12
**작업 범위**: Phase 3 완료 후 Test Coverage 개선 작업
**목표**: 19% → 60%+ Coverage
**실제 달성**: 19% → 21% (Phase 1 완료)

---

## 📊 Test Coverage 현황

### Before (Phase 3 완료 시점)
- **Total**: 19% (528/2787 statements)
- **Test Files**: 14개
- **Test Cases**: 14개
- **Status**: 8 passed, 1 failed, 5 errors

### After (신규 테스트 추가)
- **Total**: 21% (698/3344 statements)
- **Test Files**: 16개 (+2개)
- **Test Cases**: 52개 (+38개)
- **Status**: 46 passed, 1 failed, 5 errors

### 개선 지표
- **Coverage 증가**: +2% (19% → 21%)
- **Test Cases 증가**: +271% (14 → 52)
- **통과율**: 88.5% (46/52)

---

## 🆕 신규 추가 테스트

### 1. Cost Tracker 테스트 (18개)

**파일**: `tests/test_cost_tracker.py`

#### TestCostCalculation (5 tests)
- ✅ `test_calculate_cost_openai_gpt4o_mini`: OpenAI GPT-4o-mini 비용 계산
- ✅ `test_calculate_cost_gemini_flash`: Gemini Flash 무료 tier 확인
- ✅ `test_calculate_cost_unknown_provider`: Unknown provider 처리
- ✅ `test_calculate_cost_unknown_model`: Unknown model 처리
- ✅ `test_calculate_cost_zero_tokens`: 0 토큰 처리

#### TestCostLogging (2 tests)
- ✅ `test_log_cost_to_db_success`: DB 저장 성공
- ✅ `test_log_cost_with_minimal_params`: 최소 파라미터 저장

#### TestCostAnalytics (6 tests)
- ✅ `test_get_total_cost`: 총 비용 조회
- ✅ `test_get_total_cost_by_provider`: Provider별 비용
- ✅ `test_get_total_cost_by_use_case`: Use Case별 비용
- ✅ `test_get_total_cost_by_site`: Site별 비용
- ✅ `test_get_total_cost_with_date_filter`: 날짜 필터링
- ✅ `test_get_cost_breakdown`: 비용 분석 breakdown

#### TestPricingTable (2 tests)
- ✅ `test_pricing_table_structure`: Pricing 테이블 구조
- ✅ `test_openai_pricing`: OpenAI 가격 확인
- ✅ `test_gemini_pricing`: Gemini 가격 확인

#### TestEdgeCases (3 tests)
- ✅ `test_large_token_count`: 매우 큰 토큰 수
- ✅ `test_case_insensitive_provider`: 대소문자 구분 없음

**Coverage 결과**:
- `src/monitoring/cost_tracker.py`: **61%** (127 statements, 50 miss)

### 2. Healthcheck API 테스트 (20개)

**파일**: `tests/test_healthcheck.py`

#### TestDatabaseHealth (3 tests)
- ✅ `test_check_database_health_success`: DB 연결 성공
- ✅ `test_connection_pool_metrics`: Connection Pool 메트릭 (Phase 3.3 검증)
- ✅ `test_table_counts`: 테이블 레코드 수

#### TestSystemHealth (4 tests)
- ✅ `test_check_system_health_success`: 시스템 리소스 체크
- ✅ `test_cpu_metrics`: CPU 사용률 (0-100%)
- ✅ `test_memory_metrics`: Memory 사용률 + 가용 메모리
- ✅ `test_disk_metrics`: Disk 사용률 + 남은 공간

#### TestCostMetrics (3 tests)
- ✅ `test_get_cost_metrics_success`: 비용 메트릭 조회
- ✅ `test_cost_metrics_types`: 데이터 타입 검증
- ✅ `test_today_cost_not_exceed_total`: 오늘 비용 <= 총 비용

#### TestArticleMetrics (3 tests)
- ✅ `test_get_article_metrics_success`: 기사 메트릭 조회
- ✅ `test_article_metrics_types`: 데이터 타입 검증
- ✅ `test_last_24h_not_exceed_total`: 최근 24h <= 총 기사 수

#### TestUptimeTracking (2 tests)
- ✅ `test_get_uptime_seconds`: Uptime 조회
- ✅ `test_uptime_increases`: Uptime 증가 확인

#### TestHealthCheckIntegration (2 tests)
- ✅ `test_all_health_checks_pass`: 모든 Health Check 통과
- ✅ `test_full_health_response_structure`: 전체 Response 구조

#### TestHealthCheckErrors (2 tests)
- ✅ `test_database_health_handles_error_gracefully`: DB 에러 처리
- ✅ `test_system_health_handles_error_gracefully`: System 에러 처리

#### TestPrometheusMetrics (1 test)
- ✅ `test_metrics_format`: Prometheus 메트릭 형식

**Coverage 결과**:
- `src/monitoring/healthcheck.py`: **47%** (161 statements, 86 miss)

---

## 🧪 테스트 실행 결과

### 전체 테스트 (UC2 제외)

```bash
poetry run pytest tests/ --ignore=tests/uc2/ --cov=src
```

**결과**:
- **Total Tests**: 52개
- **Passed**: 46개 (88.5%)
- **Failed**: 1개 (1.9%)
- **Errors**: 5개 (9.6%)

### 실패/에러 분석

#### ❌ Failed (1개)
1. `tests/test_uc3_new_site.py::test_known_site`
   - **원인**: OpenAI API 401 Unauthorized
   - **영향**: UC3 (New Site Discovery) 테스트 불가
   - **해결책**: 유효한 OpenAI API 키 필요

#### ⚠️ Errors (5개)
모두 Master Workflow E2E 테스트:
1. `test_uc1_success_flow`
2. `test_uc1_success_with_rule_based_supervisor`
3. `test_uc1_success_with_llm_supervisor`
4. `test_uc1_success_state_transitions`
5. `test_uc1_success_final_result_structure`

**원인**: LangGraph 설정 문제 (UC1은 규칙 기반이지만 E2E 테스트에서 에러)

---

## 📦 Module별 Coverage

### 신규 모듈
| Module | Statements | Miss | Cover |
|--------|-----------|------|-------|
| `src/monitoring/cost_tracker.py` | 127 | 50 | **61%** |
| `src/monitoring/healthcheck.py` | 161 | 86 | **47%** |

### 기존 모듈
| Module | Statements | Miss | Cover |
|--------|-----------|------|-------|
| `src/workflow/uc1_validation.py` | 163 | 78 | **52%** |
| `src/workflow/uc2_hitl.py` | 589 | 517 | **12%** |
| `src/workflow/uc3_new_site.py` | 672 | 564 | **16%** |
| `src/storage/models.py` | 160 | 32 | **80%** |
| `src/storage/database.py` | 27 | 4 | **85%** |

---

## 🔍 Coverage 낮은 이유 분석

### 1. OpenAI/Gemini API 키 문제 (Critical)
- **영향도**: 전체 시스템의 66% (UC2 + UC3)
- **현상**: 모든 API 키가 401 Unauthorized 반환
- **해결 필요**: 유효한 API 키 확보

### 2. E2E 테스트 에러
- **영향도**: Master Workflow 통합 테스트
- **현상**: LangGraph 설정 문제
- **해결 필요**: E2E 테스트 환경 재구성

### 3. UC2 테스트 제외
- **영향도**: UC2 전체 (589 statements)
- **현상**: `exit(1)` 호출로 pytest 실패
- **해결 필요**: UC2 테스트 리팩토링

### 4. 미구현 테스트 영역
- Exceptions module (494 lines) - 테스트 없음
- Workflow retry logic - 테스트 없음
- Database transaction rollback - 테스트 없음
- API error fallback logic - 테스트 없음

---

## 🎯 다음 단계

### Phase 2: Coverage 40% 달성

#### 1. UC2 테스트 수정 (High Priority)
```bash
# UC2 테스트 파일에서 exit(1) 제거
tests/uc2/test_full_workflow.py
tests/uc2/test_integration.py
```

**예상 증가**: +12% (589 statements 추가)

#### 2. Exceptions 테스트 추가 (Medium Priority)
```python
tests/test_exceptions.py  # 신규 생성
```

**예상 증가**: +8% (494 statements 추가)

#### 3. Workflow Integration 테스트 (Medium Priority)
```python
tests/test_workflow_integration.py  # 신규 생성
```

**예상 증가**: +5%

#### 4. Database Transactions 테스트 (Low Priority)
```python
tests/test_database_transactions.py  # 신규 생성
```

**예상 증가**: +3%

### 예상 Coverage 로드맵

| Phase | 작업 | Coverage | 증가 |
|-------|------|----------|------|
| **현재** | Cost + Healthcheck 테스트 | 21% | - |
| **Phase 2** | UC2 수정 + Exceptions | 40% | +19% |
| **Phase 3** | Workflow Integration | 50% | +10% |
| **Phase 4** | OpenAI API 복구 + UC3 | 60% | +10% |
| **목표** | Production-Ready | **80%** | +20% |

---

## 💡 권장 사항

### 즉시 실행 가능 (API 키 불필요)
1. ✅ **UC2 테스트 수정**: `exit(1)` 제거
2. ✅ **Exceptions 테스트 추가**: 독립적으로 테스트 가능
3. ✅ **Database 테스트 추가**: 트랜잭션, Rollback 등

### API 키 확보 후 실행
4. ⏳ **UC3 테스트 활성화**: GPT-4o + Gemini 검증
5. ⏳ **E2E 테스트 복구**: Master Workflow 통합

### Production 배포 전 필수
6. ⏳ **80% Coverage 달성**: 모든 critical path 테스트
7. ⏳ **CI/CD Pipeline**: GitHub Actions 자동 테스트
8. ⏳ **Performance 테스트**: 부하 테스트 (1,000 articles/day)

---

## 📝 결론

### 성과 요약
- ✅ **38개 신규 테스트 추가** (Cost Tracker 18 + Healthcheck 20)
- ✅ **Coverage 2% 증가** (19% → 21%)
- ✅ **Phase 3 검증 완료** (Cost Tracking + Monitoring)

### 주요 블로커
- ❌ **OpenAI API 키 401 에러** → UC2/UC3 테스트 불가
- ❌ **UC2 테스트 `exit(1)`** → 589 statements 미반영
- ❌ **E2E 테스트 에러** → LangGraph 설정 문제

### 다음 우선순위
1. **UC2 테스트 수정** (즉시 가능, +12% 예상)
2. **Exceptions 테스트 추가** (즉시 가능, +8% 예상)
3. **OpenAI API 키 확보** (블로커 해소)

**목표**: 2주 내 60% Coverage 달성 → Production-Ready
