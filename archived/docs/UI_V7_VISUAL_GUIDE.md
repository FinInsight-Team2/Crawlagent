# CrawlAgent v7.0 Visual Guide

발표자를 위한 UI 시각적 가이드
생성: 2025-11-16

---

## 🎨 주요 시각적 요소

### 1. 헤더 (Hero Section)

**Before (v6.0)**:
```
# CrawlAgent v6.0 - PoC 검증 시스템
**객관적 데이터 중심의 겸손한 검증 결과를 제시합니다**
```

**After (v7.0)**:
```
┌─────────────────────────────────────────┐
│                                         │
│        CrawlAgent v7.0                  │  (Purple Gradient)
│     PoC 검증 시스템                     │  (Gray)
│                                         │
│  ● 객관적 데이터 중심의 겸손한 검증    │  (Pulsing Green Dot)
│  모든 수치는 실제 PostgreSQL DB 기반   │
│                                         │
└─────────────────────────────────────────┘
```
- **Effect**: fadeIn 0.8s
- **Colors**: Purple gradient (#667eea → #764ba2)
- **Status**: Pulsing green dot

---

### 2. UC 배지 (Badge)

**Before (v6.0)**:
```
[UC1: Quality Gate]  (Static, flat)
```

**After (v7.0)**:
```
┌──────────────────────┐
│ UC1: Quality Gate    │  (Green gradient bg)
└──────────────────────┘
      ↓ Hover
┌──────────────────────┐
│ UC1: Quality Gate    │  (Lifted + glow)
└──────────────────────┘
```
- **Hover**: translateY(-2px) + box-shadow
- **Gradient**: Linear-gradient background
- **Colors**: UC1(Green), UC2(Orange), UC3(Blue)

---

### 3. 메트릭 카드 (Metric Card)

**Before (v6.0)**:
```
┌─────────────────┐
│ 총 크롤링       │
│ 459개           │
│ (crawl_results) │
└─────────────────┘
```

**After (v7.0)**:
```
┌─────────────────┐
│ 총 크롤링       │
│ 459개           │
│ [crawl_results] │  (Badge)
└─────────────────┘
      ↓ Hover
┌─────────────────┐
│ 총 크롤링       │  (Lifted + Purple glow)
│ 459개           │
│ [crawl_results] │  (Purple gradient)
└─────────────────┘
```
- **Hover**: translateY(-4px) scale(1.01)
- **Glow**: Purple box-shadow
- **Badge**: Transforms to gradient on hover

---

### 4. 한계점 박스 (Limitation Box)

**Before (v6.0)**:
```
⚠️ 현실적 제약
• Yonhap Selector 성공률: 42.9%
• crawl_duration 미측정
```

**After (v7.0)**:
```
╔═══════════════════════════════╗  (Dashed red border)
║ ⚠️ 현실적 제약                ║  (Red gradient bg)
║                               ║
║ • Yonhap Selector: 42.9%      ║
║ • crawl_duration 미측정       ║
║                               ║
╚═══════════════════════════════╝
```
- **Border**: 2px dashed #ef4444
- **Background**: Red gradient
- **Animation**: fadeIn 0.5s

---

### 5. 데이터 소스 박스 (Data Source Box)

**Before (v6.0)**:
```
출처: PostgreSQL crawl_results 테이블
```

**After (v7.0)**:
```
│ 출처: PostgreSQL crawl_results 테이블
```
- **Left Border**: 3px solid Purple
- **Hover**: translateX(4px) + darker background

---

### 6. 탭 내비게이션 (Tabs)

**Before (v6.0)**:
```
[🎯 실시간 테스트] [🧠 아키텍처] [📊 검증] [🔍 조회]
```

**After (v7.0)**:
```
╔══════════════════╗  ┌────────┐  ┌────────┐  ┌────────┐
║ 🎯 실시간 테스트 ║  │ 🧠 아키 │  │ 📊 검증 │  │ 🔍 조회 │
╚══════════════════╝  └────────┘  └────────┘  └────────┘
  (Active: Purple gradient + shadow)
```
- **Active**: Purple gradient background
- **Shadow**: 0 4px 12px rgba(102, 126, 234, 0.4)
- **Hover**: Gray background

---

### 7. 테이블 행 (Table Row)

**Before (v6.0)**:
```
│ 1 │ Yonhap │ 453 │ 94.65 │ 42.9% │
```

**After (v7.0)**:
```
│ 1 │ Yonhap │ 453 │ 94.65 │ 42.9% │
      ↓ Hover
│ 1 │ Yonhap │ 453 │ 94.65 │ 42.9% │  (Highlighted + cursor pointer)
```
- **Hover**: background #3a3b3f + scale(1.005)
- **Cursor**: pointer
- **Transition**: 0.2s ease

---

### 8. 상태 인디케이터 (Status Indicator)

**Before (v6.0)**:
```
Success
```

**After (v7.0)**:
```
● Success  (Pulsing green dot)
```
- **Animation**: pulse 2s infinite
- **Glow**: box-shadow with colored glow
- **Colors**: Success(Green), Warning(Orange), Error(Red)

---

### 9. 스크롤바 (Scrollbar)

**Before (v6.0)**:
```
[Default browser scrollbar]
```

**After (v7.0)**:
```
Track: Dark (#2d2e32)
Thumb: Purple (#667eea)
Hover: Darker Purple (#764ba2)
```

---

### 10. 푸터 (Footer)

**Before (v6.0)**:
```
---
**CrawlAgent v6.0** | 객관적 데이터 중심 PoC 검증 시스템
모든 수치는 실제 DB 데이터 기반 | 과장 없음 | 한계점 명시
```

**After (v7.0)**:
```
─────────────────────────────────────────
       ✓ CrawlAgent v7.0 | 객관적 데이터 중심 PoC 검증 시스템
       모든 수치는 실제 DB 데이터 기반 | 과장 없음 | 한계점 명시
       
       [PostgreSQL DB] [LangGraph Supervisor] [2-Agent Consensus]
```
- **Checkmark**: Animated ✓
- **Badges**: Source attribution badges
- **Hover**: Badges transform to purple gradient

---

## 🎬 애니메이션 타이밍

| 요소 | 애니메이션 | 시간 |
|------|-----------|------|
| Header | fadeIn | 0.8s |
| Status Box | fadeIn | 0.5s |
| Checkmark | checkmark (rotate + scale) | 0.5s |
| Pulsing Dot | pulse (opacity) | 2s infinite |
| Hover | transform + shadow | 0.3s |
| Table Row | background + scale | 0.2s |

---

## 🎨 색상 팔레트

### UC Colors (Information)
```
UC1 Green:   #10b981  ████  Success, Reuse
UC2 Orange:  #f59e0b  ████  Warning, Healing
UC3 Blue:    #3b82f6  ████  Info, Discovery
```

### Theme Colors (Style)
```
Primary:     #667eea → #764ba2  ████  Purple Gradient
Background:  #1a1b1e  ████  Dark
Card:        #2d2e32  ████  Slightly lighter
Border:      #4a4b4f  ████  Gray
Text:        #e5e7eb  ████  Light gray
Secondary:   #9ca3af  ████  Medium gray
```

### Status Colors (Feedback)
```
Success:     #10b981  ████  Green
Warning:     #f59e0b  ████  Orange
Error:       #ef4444  ████  Red
Info:        #3b82f6  ████  Blue
```

---

## 📊 발표 시 강조 포인트

### 1. 헤더
- "v7.0은 theme.py의 프로페셔널 스타일을 적용했습니다"
- Pulsing dot 가리키며: "실시간 상태를 시각적으로 표현"

### 2. UC 배지
- Hover 시연: "마우스를 올리면 각 Use Case가 강조됩니다"
- "Green(UC1), Orange(UC2), Blue(UC3)로 정보 구조화"

### 3. 메트릭 카드
- Hover 시연: "데이터 카드도 인터랙티브합니다"
- Source badge 클릭: "모든 수치의 출처를 명시했습니다"

### 4. 한계점 박스
- "과장하지 않고 정직하게 한계를 명시합니다"
- "점선 테두리로 주의를 환기합니다"

### 5. 푸터 배지
- "사용된 기술 스택을 명확히 표시합니다"
- Hover 시연: "배지도 인터랙티브 효과가 있습니다"

---

## 🚀 데모 시나리오

### 시작 (5초)
1. 헤더 fadeIn 애니메이션 자연스럽게 표시
2. Pulsing dot 강조: "시스템이 활성 상태입니다"

### UC 배지 시연 (10초)
3. UC1/UC2/UC3 배지에 마우스 hover
4. "각 Use Case를 색상으로 구분했습니다"

### 메트릭 카드 (15초)
5. 총 크롤링 카드 hover
6. Source badge hover → purple gradient
7. "모든 데이터는 PostgreSQL에서 가져옵니다"

### 한계점 강조 (10초)
8. Limitation box 스크롤
9. "Yonhap 42.9% 같은 한계를 숨기지 않습니다"

### 푸터 (5초)
10. 푸터 배지들 hover
11. "PostgreSQL, LangGraph, 2-Agent Consensus 기반"

**총 데모 시간**: ~45초

---

**핵심 메시지**: v7.0은 **객관적 데이터**를 **세련되게 표현**합니다.

모든 애니메이션과 색상은 정보 전달 목적이며, 실제 DB 데이터를 기반으로 합니다.
