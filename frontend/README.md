# EasyFind — Frontend

CCTV 기반 분실물 탐지 시스템 **[EasyFind](../README.md)** 의 웹 대시보드입니다.
백엔드(`main.py`)가 제공하는 REST/MJPEG API를 소비해 **실시간 모니터링**과 **소급 검색** UI를 제공합니다.

---

## 주요 기능

- **실시간 모니터링** — 백엔드에서 카메라 목록을 받아 동적 그리드 구성, MJPEG 스트림, 모달 확대/이동
- **탐지 이력** — 방치/유실 탐지 기록 조회·필터(날짜/시간/카메라/상태) + 상태 타임라인
- **알림** — SEPARATED / SUSPECTED / LOST 상태 실시간 알림
- **정밀 검색 (Precise Detection)** — 시각·물건 묘사(한/영)로 과거 영상을 소급 검색. 진행률 표시 + **발견 즉시 타임라인 카드로 누적**, 중지/일시정지/재개 지원
- **설정** — 카메라, 탐지 임계값, 알림 옵션 (localStorage)

---

## 백엔드 연동

프론트엔드는 백엔드 API(기본 `http://localhost:5000`)를 호출합니다. **먼저 프로젝트 루트에서 백엔드를 실행**하세요.

```bash
# 프로젝트 루트
python main.py -c configs/multi_cam.yaml
```

| 기능 | 엔드포인트 |
|------|-----------|
| 카메라 목록 | `GET /api/cameras` |
| 실시간 영상 | `GET /video_feed/<pipe_name>` (MJPEG) |
| 탐지 이력 | `GET /api/detections` |
| 알림 | `GET /api/alerts` |
| 상태 요약 | `GET /api/status` |
| 소급 검색 시작 | `POST /api/search` (cam, 시각범위, prompt) |
| 검색 상태·결과 | `GET /api/search/<job_id>` (진행률 + 실시간 구간) |
| 검색 제어 | `POST /api/search/<job_id>/{stop,pause,resume}` |
| 검색 가능 카메라 | `GET /api/archive_cams` |
| 검색 썸네일 | `GET /search_thumb/<job_id>/<name>` |

---

## 프로젝트 구조

```
frontend/
├── src/
│   ├── pages/
│   │   ├── dashboard.jsx        # 실시간 모니터링 대시보드
│   │   ├── DetectionHistory.jsx # 분실물 탐지 이력
│   │   ├── Alerts.jsx           # 알림 관리
│   │   ├── PreciseDection.jsx   # 정밀(소급) 검색
│   │   └── Settings.jsx         # 시스템 설정
│   ├── Layout.jsx               # 공통 레이아웃 (사이드바 · 상단바, /api/status 폴링)
│   ├── App.jsx                  # 라우터 설정
│   └── main.jsx                 # 진입점
├── public/
├── package.json
└── vite.config.js
```

---

## 페이지 구성

| 페이지 | 경로 | 설명 |
|--------|------|------|
| Monitoring | `/dashboard` | 실시간 CCTV 모니터링 |
| Detection History | `/detection-history` | 분실물 탐지 이력 조회·필터 |
| Alerts | `/alerts` | 실시간 알림 관리 |
| **Precise Detection** | `/precise-detection` | 시각·물건 묘사 기반 과거 영상 소급 검색 |
| Settings | `/settings` | 시스템 설정 |

`/` 접속 시 `/dashboard`로 리다이렉트됩니다.

---

## 실행

Node.js 18+ 환경 권장.

```bash
git clone https://github.com/sylee-skhu/2026-1-Capstone-T01-easyfind-lost-n-found.git
cd 2026-1-Capstone-T01-easyfind-lost-n-found/frontend

npm install
npm run dev -- --host
```

개발 서버는 `http://localhost:5173` 에서 열립니다. (백엔드가 `:5000`에 떠 있어야 데이터가 표시됩니다.)

| 스크립트 | 설명 |
|----------|------|
| `npm run dev` | 개발 서버 (HMR) |
| `npm run build` | 프로덕션 빌드 (`dist/`) |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run lint` | ESLint 검사 |

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| Framework | React 19 + Vite |
| Routing | React Router DOM 7 |
| 상태 관리 | React Hooks (useState/useEffect/useRef) · localStorage |
| 서버 통신 | `fetch` (REST 폴링 + MJPEG `<img>` 스트림) |
| 스타일 | Inline CSS |
