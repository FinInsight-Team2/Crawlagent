# CrawlAgent 빠른 시작 가이드 (핸드오프용)

**버전**: v1.0 | **날짜**: 2025-11-19 | **소요 시간**: 10분

---

## 🚀 5분 안에 시작하기

### 1단계: 패키지 설치 (2분)

```bash
# Essential 패키지 압축 해제
cd /path/to/your/workspace
tar -xzf crawlagent_essential_v1.0_20251119.tar.gz
cd crawlagent
```

### 2단계: 환경 설정 (3분)

```bash
# .env 파일 생성
cp .env.example .env

# API 키 입력 (nano 또는 텍스트 에디터 사용)
nano .env
```

**필수 입력 사항** (2개):
```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**API 키 발급 링크**:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

### 3단계: 설치 및 실행 (5분)

```bash
# 전체 설정 (Poetry 설치 + DB 초기화)
make setup

# UI 실행
make start

# 브라우저에서 열기
open http://localhost:7860
```

---

## ✅ 환경 검증 (선택사항)

설치 전/후 환경 체크:

```bash
bash scripts/handoff_verification.sh
```

**기대 결과**: 5/8 이상 Pass (Python 버전, PostgreSQL 경고는 무시 가능)

---

## 🎯 첫 크롤링 테스트 (1분)

### Tab 1: 실시간 테스트

1. **URL 입력**:
   ```
   https://www.yonhapnewstv.co.kr/category/news/politics/all/20231
   ```

2. **카테고리 선택**: `politics`

3. **크롤링 실행** 버튼 클릭

4. **결과 확인**:
   - 상태 박스: UC1 → UC2 → 완료
   - 크롤링 결과 테이블: 제목, 본문, 품질 점수
   - 워크플로우 플로우차트 업데이트

---

## 📚 핵심 문서 (읽기 순서)

| 순서 | 문서 | 소요 시간 | 내용 |
|------|------|-----------|------|
| 1 | [README.md](README.md) | 5분 | 프로젝트 개요, 아키텍처 |
| 2 | [CONFIGURATION.md](CONFIGURATION.md) | 10분 | 환경변수 설정 |
| 3 | [HANDOFF_SUMMARY.md](HANDOFF_SUMMARY.md) | 10분 | 최종 변경사항 요약 |
| 4 | [TESTING.md](TESTING.md) | 15분 | 테스트 실행 및 작성 |
| 5 | [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | 15분 | DB 구조 및 쿼리 |

**총 소요 시간**: 55분

---

## 🔧 주요 Make 명령어

```bash
make setup          # 전체 설치 (최초 1회)
make start          # UI 실행
make test           # 테스트 실행
make db-init        # DB 초기화
make clean          # 캐시 정리
make docker-up      # Docker 전체 실행
make docker-down    # Docker 중지
```

---

## 📦 패키지 비교

| 패키지 | 크기 | 포함 | 용도 |
|--------|------|------|------|
| **Essential** | 236KB | src/, config, 문서 | **권장** - 프로덕션 배포 |
| **Full** | 19MB | 모든 코드 + 테스트 | 개발 환경 |

**선택 기준**:
- 배포만 필요? → Essential
- 개발 + 테스트? → Full

---

## 🐛 트러블슈팅 (자주 묻는 질문)

### Q1: "Poetry not found" 오류

```bash
curl -sSL https://install.python-poetry.org | python3 -
# 터미널 재시작
```

### Q2: "Database connection failed" 오류

```bash
# PostgreSQL 시작
docker-compose up -d db

# 연결 확인
docker-compose ps
```

### Q3: API 키 오류 (401 Unauthorized)

```bash
# .env 파일 확인
cat .env | grep API_KEY

# API 키 형식 체크
# OpenAI: sk-proj-로 시작
# Anthropic: sk-ant-로 시작
```

### Q4: "Port 7860 already in use" 오류

```bash
# 실행 중인 프로세스 확인
lsof -i :7860

# 프로세스 종료
kill -9 <PID>
```

**더 많은 트러블슈팅**: [HANDOFF_PACKAGE/09_TROUBLESHOOTING_REFERENCE.md](HANDOFF_PACKAGE/09_TROUBLESHOOTING_REFERENCE.md)

---

## 🎓 아키텍처 개요 (30초)

```
Master Supervisor (LangGraph)
    │
    ├─> UC1: Quality Gate (Rule-based, $0)
    │       └─> 80점 이상 → 통과
    │       └─> 80점 미만 → UC2
    │
    ├─> UC2: Self-Healing (2-Agent Consensus)
    │       ├─> Agent 1: Claude Sonnet 4.5 (Proposer)
    │       ├─> Agent 2: GPT-4o (Validator)
    │       └─> Consensus: 0.3×Claude + 0.3×GPT + 0.4×Quality
    │
    └─> UC3: New Site Discovery
            ├─> Agent 1: Claude Sonnet 4.5 (Discoverer)
            ├─> Agent 2: GPT-4o (Validator)
            └─> JSON-LD + BeautifulSoup
```

**핵심 철학**: "Learn Once, Reuse Forever"

---

## 📊 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.10+ | 3.11 |
| RAM | 4GB | 8GB+ |
| 저장공간 | 1GB | 5GB+ |
| Docker | 20.10+ | 최신 버전 |
| Poetry | 1.5+ | 1.7+ |

---

## 🔗 중요 링크

- **프로젝트 루트**: `/Users/charlee/Desktop/Intern/crawlagent/`
- **UI 주소**: http://localhost:7860
- **DB 연결**: `postgresql://crawlagent:password@localhost:5432/crawlagent`
- **로그 위치**: `logs/crawlagent.log`

---

## 📞 도움이 필요하신가요?

1. **문서 확인**: [HANDOFF_SUMMARY.md](HANDOFF_SUMMARY.md)
2. **트러블슈팅**: [HANDOFF_PACKAGE/09_TROUBLESHOOTING_REFERENCE.md](HANDOFF_PACKAGE/09_TROUBLESHOOTING_REFERENCE.md)
3. **설정 가이드**: [CONFIGURATION.md](CONFIGURATION.md)
4. **테스트 가이드**: [TESTING.md](TESTING.md)

---

## ✅ 핸드오프 체크리스트

**수신자 확인 사항**:

- [ ] 패키지 압축 해제 완료
- [ ] .env 파일 생성 및 API 키 입력 완료
- [ ] `make setup` 실행 성공
- [ ] `make start` 실행 및 UI 접속 성공
- [ ] Tab 1에서 첫 크롤링 테스트 성공
- [ ] 핵심 문서 3개 읽음 (README, CONFIGURATION, HANDOFF_SUMMARY)
- [ ] 환경 검증 스크립트 실행 (5/8 이상 Pass)

**모든 항목 체크 완료 시**: 핸드오프 성공! 🎉

---

**작성일**: 2025-11-19
**버전**: v1.0
**예상 소요 시간**: 총 10분 (설정) + 55분 (문서 읽기)
