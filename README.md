# 🏙️ 아산시 스마트시티 자산관리 대시보드

> **Digital OASIS** - Smart Asset Management Platform v3.1  
> Slack ↔ Notion ↔ GitHub 자동 연동

[![Deploy Status](https://github.com/leesungho-ai/Asan-asset-management/actions/workflows/sync-and-deploy.yml/badge.svg)](https://github.com/leesungho-ai/Asan-asset-management/actions)

## 🔗 대시보드 URL

**https://leesungho-ai.github.io/Asan-asset-management/**

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

---

## ⚙️ GitHub 설정 (최초 1회)

### 1️⃣ Secrets 설정

`Settings > Secrets and variables > Actions`에서 추가:

| Secret 이름 | 값 | 필수 |
|------------|-----|:----:|
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

`Settings > Pages > Source` → **GitHub Actions** 선택

### 4️⃣ 첫 배포 실행

`Actions > Sync Notion & Deploy > Run workflow`

---

## 🔄 자동 동기화 스케줄

| 트리거 | 시간 | 동작 |
|--------|------|------|
| **스케줄** | 매일 09:00 KST | 노션 → GitHub 자동 동기화 |
| **Push** | main 브랜치 | 즉시 배포 |
| **수동** | Actions에서 | 원할 때 실행 |

---

## 📁 프로젝트 구조

```
Asan-asset-management/
├── index.html              # 메인 대시보드 (기존 디자인 유지)
├── package.json            # Node.js 의존성
├── .gitignore
├── README.md
│
├── .github/
│   └── workflows/
│       └── sync-and-deploy.yml   # GitHub Actions
│
├── scripts/
│   └── sync-notion-data.js       # 노션 API 동기화
│
└── data/
    └── dashboard-data.json       # 동기화된 데이터 (자동 생성)
```

---

## 📞 담당자

| 역할 | 이름 |
|------|------|
| PMO 관리자 | Danny (제일엔지니어링) |
| 기술/인프라 | 이성호 |
| 사업 총괄 | 김주용 |
| 계약/행정 | 임혁 |
| 구매/입찰 | 함정영 |

---

## 📝 변경 이력

### v3.1.0 (2025-11-28)
- GitHub Actions 자동 연동 시스템 추가
- 노션 API 동기화 스크립트 추가
- 외부 JSON 데이터 로드 기능 추가

### v3.0.0 (2025-11-27)
- 대시보드 UI 전면 개편
- 탭 기반 네비게이션 추가
- Chart.js 차트 시각화

---

© 2025 아산시 강소형 스마트시티 구축사업 | 제일엔지니어링 PMO
