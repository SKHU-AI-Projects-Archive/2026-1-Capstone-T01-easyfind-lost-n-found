# EasyFind Lost & Found — Frontend

CCTV 기반 분실물 탐지 시스템의 프론트엔드입니다.

---

## 📋 프로젝트 개요

실시간 CCTV 영상을 모니터링하고 분실물을 탐지하여 관리자가 효율적으로 분실물을 관리할 수 있는 웹 대시보드입니다.

### 주요 기능
- 실시간 CCTV 모니터링 (4채널 그리드)
- 분실물 탐지 결과 조회 및 필터링 (날짜/시간/물건종류/상태)
- 탐지 항목 클릭 시 상세 정보 및 상태 타임라인
- 누군가 가져간 물건 Before/After 영상 UI
- 카메라 모달 확대/축소 기능
- 실시간 알림 관리
- 시스템 설정 (카메라, 탐지 임계값, 알림)

---

## 📁 프로젝트 구조

```
frontend/
├── src/
│   ├── pages/
│   │   ├── dashboard.jsx        # 메인 모니터링 대시보드
│   │   ├── DetectionHistory.jsx # 분실물 탐지 이력
│   │   ├── Alerts.jsx           # 알림 관리
│   │   └── Settings.jsx         # 시스템 설정
│   ├── Layout.jsx               # 공통 레이아웃 (사이드바, 상단바)
│   ├── App.jsx                  # 라우터 설정
│   └── main.jsx                 # 진입점
├── public/
├── package.json
└── vite.config.js
```

---

## 💻 Installation

Node.js v24.14.1, npm v11.11.0 환경에서 실행합니다.

### step 1

repository를 복제합니다.

```bash
git clone https://github.com/SKHU-AI-Projects-Archive/2026-1-Capstone-T01-easyfind-lost-n-found.git
```

### step 2

frontend 폴더를 생성하고 Vite 프로젝트를 생성합니다.

```bash
mkdir frontend
cd frontend
npm create vite@latest . -- --template react
```

### step 3

react-router-dom을 설치합니다.

```bash
npm install react-router-dom
```

### step 4

실행에 필요한 패키지를 설치합니다.

```bash
npm install
```

### step 5

개발 서버를 실행합니다.

```bash
npm run dev
```

### step 6

브라우저에서 아래 주소로 접속합니다.

```
http://localhost:5173
```

---

## 🖥 페이지 구성

| 페이지 | 경로 | 설명 |
|--------|------|------|
| Monitoring | `/dashboard` | 실시간 CCTV 모니터링 |
| Detection History | `/detection-history` | 분실물 탐지 이력 조회 및 필터링 |
| Alerts | `/alerts` | 실시간 알림 관리 |
| Settings | `/settings` | 시스템 설정 |

---

## 🔧 기술 스택

| 항목 | 내용 |
|------|------|
| Framework | React + Vite |
| Routing | React Router DOM |
| 상태 관리 | React useState / localStorage |
| 스타일 | Inline CSS |