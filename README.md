# 원자력공학 문헌 주간 다이제스트

매주 원자력공학 주요 5개 저널의 신규 논문을 수집해 **누적 DB → 대화형 대시보드 → Excel → 요약 메일**을 자동 생성합니다.
ChatGPT/Codex에서 운영하던 시스템(`legacy/codex-handoff/`)을 GitHub Actions 기반으로 이전한 버전입니다.

## 1. 동작 방식

```
매주 월 07:00 KST (GitHub Actions, 클라우드에서 실행 — 연구실 PC 불필요)
  ├─ Crossref: 지난주(월~일) DOI 신규 등록 논문 수집
  ├─ OpenAlex: 저자 소속 국가, Open Access 여부, 초록(있는 경우)
  ├─ 제목 한글 번역 (Claude API → 없으면 MyMemory)          ※ DOI별 캐시
  ├─ SQLite 누적 DB 갱신 (data/literature.sqlite, DOI 중복 제거)
  ├─ 대시보드 HTML (docs/index.html, docs/archive/날짜.html)
  ├─ 메일 본문 HTML (outputs/email-날짜.html) + Excel (outputs/…xlsx)
  ├─ 메일 발송 (Gmail SMTP, 인라인 HTML, UTF-8) — 같은 주 중복 발송 방지
  └─ 결과를 저장소에 커밋 (git 이력 = 회차별 백업)
월 12:00 KST 재시도 — 오전 실행이 실패했을 때만 다시 수행
실패 시 → GitHub가 계정 메일로 실패 알림 발송 (SMTP 설정 시 별도 실패 알림 메일도 발송)
놓친 주가 있으면 → 다음 실행 때 빠진 주를 자동으로 먼저 수집(backfill)
```

## 2. 최초 설정 (1회, 약 10분)

GitHub 저장소 → **Settings → Secrets and variables → Actions** 에서 등록합니다.

| 종류 | 이름 | 값 | 필수 |
|---|---|---|---|
| Secret | `SMTP_USER` | 발송용 Gmail 주소 — 등록하지 않으면 메일 없이 대시보드만 갱신 | 선택 |
| Secret | `SMTP_PASSWORD` | Gmail **앱 비밀번호** 16자리 (아래 참고) | 선택 |
| Secret | `ANTHROPIC_API_KEY` | Claude API 키 — 제목 번역 품질 향상 | 선택 (권장) |
| Secret | `ELSEVIER_API_KEY` | Elsevier 개발자 키 — ScienceDirect 링크/PII 보강 | 선택 |
| Variable | `DASHBOARD_URL` | 대시보드 주소를 바꿀 때만 (기본값: https://malmok2.github.io/PaperCollection/) | 선택 |
| Variable | `DIGEST_RECIPIENTS` | 수신자, 쉼표 구분 (기본값: `config/settings.json`) | 선택 |

**Gmail 앱 비밀번호 만들기**: Google 계정 → 보안 → 2단계 인증 켜기 → "앱 비밀번호" 검색 → 이름 입력(예: digest) → 생성된 16자리 복사.
(일반 비밀번호는 SMTP 로그인에 쓸 수 없습니다.)

**수동 실행/테스트**: 저장소 → **Actions → Weekly nuclear literature digest → Run workflow**
- `run_date`: 처리할 주의 월요일 (비우면 이번 주)
- `no_email`: 메일 없이 결과물만 생성
- `force_email`: 이미 보낸 주도 다시 발송

> 예약 실행(schedule)은 **저장소의 기본 브랜치**에 있는 워크플로만 동작합니다.

## 3. 대시보드 공개 방식

대시보드는 `docs/index.html` 단일 파일(외부 라이브러리 없음)입니다.

**GitHub Pages**(공개 저장소)로 게시합니다: <https://malmok2.github.io/PaperCollection/>
설정: Settings → Pages → Source: *GitHub Actions*. 매 실행 후 자동 재배포되며, 지난 회차는 `archive/날짜.html`에 남습니다.

기존 `nuclear-literature-dashboard.ssrmin.chatgpt.site`는 Codex 전용 호스팅이라 여기서 갱신할 수 없습니다.

## 4. 로컬 실행

```bash
pip install -r requirements.txt
python -m pipeline.run_weekly                         # 이번 주
python -m pipeline.run_weekly --run-date 2026-09-21   # 특정 주
python -m pipeline.run_weekly --skip-collect --no-email   # DB로 결과물만 재생성
python -m pipeline.send_email --test                  # 한글 인코딩 테스트 메일 (SMTP 환경변수 필요)
```

## 5. 설정 변경 — `config/settings.json` 한 파일

| 키 | 내용 |
|---|---|
| `journals` | 수집 저널명: ISSN |
| `topics` | 1차 연구 영역 분류 키워드 규칙 (제목+초록, 앞 순서가 우선) |
| `watchlists` | 연구실 관심 분야 추적기 키워드 |
| `translation_glossary` | 번역 용어집 (Claude 번역 시 적용) |
| `recipients`, `email_subject`, `dashboard_url` | 메일 설정 |
| `country_names` | 국가 코드 → 한글명 |

기존에는 같은 규칙이 3개 파일(`update_weekly_database.py`, `build_digest.py`, `init_literature_database.py`)에 중복돼 있었습니다.

## 6. 폴더 구조

```
config/settings.json        설정 (저널, 토픽, 관심분야, 수신자, 용어집)
pipeline/                   파이프라인 코드 (run_weekly.py가 진입점)
data/literature.sqlite      누적 DB (운영본; 백업은 git 이력)
data/translations_ko.json   DOI별 한글 제목 캐시
data/raw/                   회차별 수집 원자료
docs/                       대시보드 (Pages 게시 대상)
outputs/                    메일 HTML, Excel
state/latest-run.json       마지막 실행 결과 / state/sent-runs.json 발송 이력
legacy/codex-handoff/       이전 Codex 버전 코드와 인수인계 문서 (참고용)
```

## 7. 알려진 한계

- "신규"의 기준은 Crossref **DOI 등록일(created)** 입니다. 온라인 공개일·권호일과 다를 수 있습니다.
- Crossref에 Elsevier 초록은 거의 없습니다. 초록은 OpenAlex에 있는 경우에만 채워집니다(기존 DB 344편은 초록 0편).
- 토픽 분류는 키워드 규칙입니다. 2026-09-07~13 주간 기준 55편 중 14편(25%)이 "기타 원자력"으로 남았습니다.
- 국가 정보는 OpenAlex 소속기관 데이터에 의존합니다(현재 커버리지 약 82%).
