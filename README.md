# 🏙️ 아산시 스마트시티 자산관리 대시보드 v4.0

> **Slack ↔ Notion ↔ GitHub 완전 자동 연동 시스템**

[![Deploy Status](https://github.com/leesungho-ai/Asan-asset-management/actions/workflows/sync-and-deploy.yml/badge.svg)](https://github.com/leesungho-ai/Asan-asset-management/actions)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen)](https://leesungho-ai.github.io/Asan-asset-management/)

---

## 📋 개요

아산시 강소형 스마트시티 구축사업의 자산관리 대시보드입니다.
**Slack #자산관리대장** 채널의 데이터가 **Notion**을 거쳐 **GitHub Pages**로 자동 배포됩니다.

**🔗 대시보드 URL**: https://leesungho-ai.github.io/Asan-asset-management/

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Slack       │     │     Notion      │     │  GitHub Pages   │
│  #자산관리대장  │ ──▶ │   자산관리 DB   │ ──▶ │   Dashboard     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   실시간 입력            MCP 동기화            Actions 배포
   데이터 수정              API 제공            자동 빌드
```

### 데이터 흐름

1. **Slack → Notion**: MCP(Model Context Protocol)를 통한 실시간 동기화
2. **Notion → GitHub**: GitHub Actions가 매일 3회 (09:00, 15:00, 21:00 KST) 자동 실행
3. **GitHub → Pages**: Tailwind CSS 빌드 후 자동 배포

---

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/leesungho-ai/Asan-asset-management.git
cd Asan-asset-management
```

### 2. 의존성 설치

```bash
npm install
```

### 3. 환경변수 설정

```bash
# .env 파일 생성 (로컬 테스트용)
echo "NOTION_API_KEY=your_notion_api_key" > .env
echo "NOTION_DATABASE_ID=2aa50aa9577d81ee9cd0e7e63b3fdf25" >> .env
```

### 4. 로컬 개발

```bash
# Tailwind CSS 빌드
npm run build:css

# 노션 데이터 동기화
npm run sync

# 대시보드 데이터 업데이트
npm run update

# 전체 빌드
npm run build
```

---

## ⚙️ GitHub 설정 (최초 1회)

### 1️⃣ Secrets 설정

`Settings > Secrets and variables > Actions`에서 추가:

| Secret 이름 | 설명 | 필수 |
|------------|------|:----:|
| `NOTION_API_KEY` | 노션 API 통합 키 | ✅ |
| `NOTION_DATABASE_ID` | `2aa50aa9577d81ee9cd0e7e63b3fdf25` | ✅ |
| `SLACK_WEBHOOK_URL` | Slack 알림용 Webhook | ❌ |

### 2️⃣ Notion API 키 발급

1. https://developers.notion.com/ 접속
2. **+ New Integration** 클릭
3. **Internal integration** 선택
4. 생성된 **Secret** 복사
5. 노션에서 자산관리 DB 열기 → **···** → **연결 추가** → 생성한 통합 선택

### 3️⃣ GitHub Pages 활성화

1. `Settings > Pages` 이동
2. **Source**를 **GitHub Actions**로 설정

### 4️⃣ 첫 배포 실행

`Actions > 🔄 Notion 동기화 & 배포 > Run workflow`

---

## 🔄 자동 동기화 스케줄

| 트리거 | 시간 (KST) | 설명 |
|--------|------------|------|
| 스케줄 | 09:00, 15:00, 21:00 | 매일 3회 자동 동기화 |
| Push | main 브랜치 | 즉시 빌드 및 배포 |
| 수동 | Actions에서 | 원할 때 실행 |

---

## 📁 프로젝트 구조

```
Asan-asset-management/
├── index.html                    # 메인 대시보드
├── package.json                  # Node.js 의존성
├── tailwind.config.js            # Tailwind CSS 설정
├── .gitignore
├── README.md
│
├── .github/
│   └── workflows/
│       └── sync-and-deploy.yml   # GitHub Actions 워크플로우
│
├── src/
│   └── input.css                 # Tailwind CSS 소스
│
├── dist/
│   └── output.css                # 빌드된 CSS (자동 생성)
│
├── scripts/
│   ├── sync-notion-data.js       # 노션 API 동기화 스크립트
│   └── update-dashboard.js       # 대시보드 데이터 업데이트
│
└── data/                         # 동기화된 JSON 데이터 (자동 생성)
    ├── assets.json
    ├── statistics.json
    ├── infra-projects.json
    ├── upcoming-assets.json
    ├── risks.json
    ├── budget.json
    ├── sync-info.json
    └── dashboard-data.json
```

---

## 📊 대시보드 기능

### KPI 지표
- 📦 총 등록 자산 수 및 총 자산 가치
- 📈 가동률, 예산 집행률, 보증기간 내 자산 비율
- ⏰ 사업 종료 D-Day 카운트다운

### 시각화
- 🥧 카테고리별 자산 분포 (도넛 차트)
- 📊 담당자별 자산 현황 (바 차트)
- 🏗️ 대형 인프라 프로젝트 진행률

### 데이터 테이블
- 🕐 최근 등록 자산 목록
- ⚠️ 리스크 관리 현황
- 💰 예산 집행 현황

---

## 🛠️ 기술 스택

| 구분 | 기술 |
|------|------|
| **Frontend** | HTML5, Tailwind CSS (PostCSS 빌드), Chart.js |
| **Backend** | Node.js, @notionhq/client |
| **CI/CD** | GitHub Actions |
| **Hosting** | GitHub Pages |
| **Data Source** | Notion API |

---

## 🔧 문제 해결

### Tailwind CSS 경고 해결

❌ 이전 (CDN 사용):
```html
<script src="https://cdn.tailwindcss.com"></script>
<!-- Warning: cdn.tailwindcss.com should not be used in production -->
```

✅ 현재 (프로덕션 빌드):
```html
<link rel="stylesheet" href="./dist/output.css">
```

### 동기화 실패 시

1. GitHub Secrets 확인 (`NOTION_API_KEY`, `NOTION_DATABASE_ID`)
2. Notion DB에 통합(Integration) 연결 확인
3. Actions 탭에서 로그 확인

---

## 📞 담당자

| 역할 | 이름 | 소속 |
|------|------|------|
| PMO 관리자 | Danny | 제일엔지니어링 |
| 기술/인프라 | 이성호 | - |
| 사업 총괄 | 김주용 | - |
| 계약/행정 | 임혁 | - |
| 구매/입찰 | 함정영 | - |

---

## 📝 변경 이력

### v4.0.0 (2025-12-02)
- ✅ Tailwind CSS 프로덕션 빌드 적용 (CDN 경고 해결)
- ✅ 완전한 Slack ↔ Notion ↔ GitHub 동기화 시스템 구축
- ✅ GitHub Actions 워크플로우 최적화 (매일 3회 동기화)
- ✅ 대시보드 UI/UX 개선

### v3.0.0 (2025-11-28)
- 대시보드 UI 전면 개편
- Notion API 연동 추가
- Chart.js 시각화

---

## 📄 라이선스

© 2025 아산시 강소형 스마트시티 구축사업 | 제일엔지니어링 PMO

---

**💬 문의**: 대시보드 관련 문의사항은 Slack **#자산관리대장** 채널을 이용해 주세요.
