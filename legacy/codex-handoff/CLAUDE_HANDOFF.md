# 원자력공학 문헌 다이제스트 자동화 인수인계

작성일: 2026-09-23  
원 프로젝트 폴더: `C:\Users\Idaho_S\Documents\Codex\2026-08-30\n`

## 1. 프로젝트 목표

매주 원자력공학 주요 저널의 최근 논문을 수집하여 다음 결과물을 만드는 프로젝트다.

1. DOI 기준 누적 SQLite 데이터베이스
2. 사람이 열람하기 쉬운 Excel 데이터베이스
3. 논문 목록과 연구 동향을 보여주는 대화형 HTML 대시보드
4. Gmail 본문에서 바로 읽을 수 있는 요약 HTML 이메일
5. 매주 월요일 자동 수집·게시·메일 발송

최종 수신 주소는 `hysms@hanyang.ac.kr`이며, 공개 대시보드 주소는 아래와 같다.

- <https://nuclear-literature-dashboard.ssrmin.chatgpt.site>

## 2. 사용자가 확정한 요구사항

- 원자력공학 전반을 다룬다.
- 연구 관심 분야에 열수력, 다상유동·비등, 유동가시화, 안전·사고해석, 원자로물리, 핵연료·재료, Machine Learning, Digital Twin·PINN을 포함한다.
- 각 논문은 영문 제목 아래에 한글 번역 제목을 표시한다.
- 공개 Abstract를 확보할 수 있으면 활용하되, 불가능하면 제목과 공개 링크만으로도 수록한다.
- 논문별 모호한 “연구실 연관성” 문구보다는 전체 출판물의 연구 영역·동향 시각화를 우선한다.
- 저널 이름을 누르면 해당 저널 논문만 필터링한다.
- 토픽, 키워드, 국가, 저널×토픽, 저널×국가 요소도 클릭 필터로 동작한다.
- 국가별 논문 분포를 대시보드에 표시한다.
- 메일에는 HTML 파일을 첨부하지 않고, 요약 내용을 본문에 인라인 HTML로 넣는다.
- 전체 상호작용 기능은 공개 대시보드 링크에서 제공한다.
- 발송 주기는 매주 월요일 오전 9시(Asia/Seoul)로 결정했다.
- 논문 링크는 ScienceDirect 직접 URL보다 DOI URL(`https://doi.org/...`)을 우선한다. 공개 사이트 내부 브라우저에서 ScienceDirect가 연결을 거부하는 문제가 있었기 때문이다.

## 3. 수집 대상 저널

`work/collect_metadata.py`와 `work/collect_previous_period.py`에 다음 5개 저널이 하드코딩되어 있다.

| 저널 | ISSN |
|---|---|
| Nuclear Engineering and Design | 0029-5493 |
| Annals of Nuclear Energy | 0306-4549 |
| Nuclear Engineering and Technology | 1738-5733 |
| Progress in Nuclear Energy | 0149-1970 |
| Nuclear Technology | 0029-5450 |

현재 “최근 논문”의 기준은 출판사의 issue date가 아니라 **Crossref DOI created date**다. 대시보드와 이메일에도 이 점을 명시한다.

## 4. 데이터 소스와 처리 방식

- Crossref API: 대상 저널의 DOI 신규 등록 논문 수집
- Elsevier Article API: `10.1016/` DOI의 PII, ScienceDirect 링크, cover date, Open Access 여부 보강
- OpenAlex API: 저자 소속 국가와 교신저자 국가 추정
- MyMemory Translation API: 영문 제목의 한글 번역
- 논문 고유키: DOI 소문자 정규화 값

API 키는 코드에 저장되어 있지 않다. Elsevier API는 키 없이 호출하므로 일부 메타데이터가 비어 있을 수 있다. Abstract가 없을 때는 제목 기반 소개문을 생성한다.

## 5. 주요 폴더와 파일

### 실행·자동화

- `run_weekly_pipeline.ps1`: 전체 로컬 수집 파이프라인
- `install_weekly_task.cmd`: Windows 예약 작업 설치 진입점
- `install_weekly_task.ps1`: `Codex Nuclear Literature Weekly` 예약 작업 등록
- `weekly_pipeline_watcher.ps1`: 보조 감시 스크립트. 현재 예약 작업 설치 스크립트에서는 사용하지 않는다.
- `automation-state/latest-run.json`: 마지막 실행 결과와 산출물 경로
- `logs/weekly-pipeline-YYYY-MM-DD.log`: 실행 로그

### Python/Node 처리 코드

- `work/collect_metadata.py`: 현재 주 논문 수집 및 국가 정보 1차 보강
- `work/collect_previous_period.py`: 직전 주 비교용 논문 수집
- `work/translate_titles.py`: 제목 한글 번역과 DOI별 캐시 관리
- `work/update_weekly_database.py`: SQLite 갱신, 중복 제거, 백업, JSON export
- `work/enrich_countries.py`: DB에서 누락된 국가 정보 추가 보강
- `work/build_digest.py`: 대화형 대시보드 HTML 생성
- `work/build_email_digest.py`: 이메일 본문용 HTML 생성
- `work/build_literature_workbook.mjs`: Excel 생성
- `work/db_export.json`: 대시보드와 Excel 생성에 쓰는 DB export

### 산출물

- `outputs/nuclear-literature-digest-YYYY-MM-DD.html`
- `outputs/nuclear-literature-email-YYYY-MM-DD.html`
- `outputs/nuclear-literature-database.xlsx`
- `work/nuclear-literature-site/public/dashboard.html`: 게시 직전 대시보드 복사본

### 안정 보관용 데이터베이스

작업 폴더와 별도로 다음 위치에 보관한다.

`C:\Users\Idaho_S\Documents\Codex\nuclear-literature-db`

구조:

- `data/working.sqlite`: 운영 DB
- `backups/latest.sqlite`: 최신 복구본
- `backups/YYYY-MM-DD.sqlite`: 회차별 복구본
- `exports/nuclear-literature.xlsx`: 최신 Excel
- `raw/`: 회차별 Crossref 원자료
- `reports/`: 보관된 HTML
- `config/`: 저널·토픽 설정
- `logs/collection-history.log`: DB 수집 이력

2026-09-23 확인 기준 최신 백업은 `2026-09-14.sqlite`다.

## 6. 로컬 파이프라인 실행

PowerShell에서 프로젝트 루트로 이동한 다음 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_weekly_pipeline.ps1
```

특정 월요일을 실행 기준일로 지정할 수 있다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_weekly_pipeline.ps1 -RunDate "2026-09-21"
```

이 스크립트는 해당 월요일 직전 7일(월~일)을 현재 기간으로, 그 전 7일을 비교 기간으로 계산한다. 정상 처리 순서는 다음과 같다.

1. 현재 기간 Crossref/Elsevier/OpenAlex 수집
2. 비교 기간 Crossref 수집
3. 제목 번역
4. SQLite upsert 및 백업
5. 누락 국가 보강
6. 대시보드 HTML 생성
7. 이메일 HTML 생성
8. Excel 생성
9. 대시보드를 Sites 프로젝트의 `public/dashboard.html`로 복사
10. `automation-state/latest-run.json`에 성공/실패 기록

고정 실행 파일 경로는 현재 다음과 같이 하드코딩되어 있다.

- Python: `C:\Program Files\Python310\python.exe`
- Node: `C:\Program Files\nodejs\node.exe`

## 7. 토픽 분류와 연구실 관심 분야

DB의 1차 토픽 분류는 제목+공개 Abstract의 키워드 규칙을 이용한다.

- 열수력·유체
- 원자로물리·해석
- 안전·사고·리스크
- 핵연료·재료
- AI·디지털
- 방사선·계측
- 핵연료주기·폐기물
- 설계·운전·경제
- 기타 원자력

관심 분야 추적기는 다음 8개다.

- 열수력
- 다상유동·비등
- 유동가시화
- 안전·사고해석
- 원자로물리
- 핵연료·재료
- Machine Learning
- Digital Twin·PINN

분류 규칙은 `work/update_weekly_database.py`의 `TOPICS`와 `work/build_digest.py`의 `RESEARCH_AREAS`, `WATCHLISTS`에 있다. 현재 두 파일에 유사 규칙이 중복되어 있으므로 향후 JSON 설정 하나로 통합하는 것이 좋다.

## 8. 대시보드 기능

`work/build_digest.py`가 단일 정적 HTML을 만든다. 외부 JS 프레임워크 없이 HTML/CSS/JavaScript로 동작한다.

현재 포함된 기능:

- 누적 논문 수, 최신 기간 논문 수, 누적 수집 회차
- 저널별 필터
- 문서 유형 분포
- 연구 영역 분포
- 국가별 논문 분포
- 저널×국가 히트맵
- 제목 기반 연구 토픽 산점도
  - TF-IDF(1~2 gram) → Truncated SVD 2차원 투영
  - 가까운 점일수록 제목 어휘가 유사
- 주간 연구 토픽 추세
- 급상승 키워드
- 연구실 관심 분야 추적기
- 상위 연구 키워드
- 일별 DOI 등록 추이
- 저널×연구 토픽 히트맵
- 각 논문의 영문 제목, 한글 제목, 저자, 저널, 날짜, 국가, 소개, Abstract/DOI 링크
- 저널·토픽·키워드·관심 분야·국가의 조합 필터

공개 Sites 프로젝트:

- 로컬 경로: `work/nuclear-literature-site`
- 프로젝트 ID: `appgprj_6a941c701ea08191a7c14c27c6469f00`
- 공개 URL: <https://nuclear-literature-dashboard.ssrmin.chatgpt.site>
- 설정 파일: `work/nuclear-literature-site/.openai/hosting.json`

주의: 이 사이트의 재배포는 Codex의 Sites 도구를 이용해 수행했다. Claude 환경에서 같은 도구와 권한이 없으면 기존 URL 갱신이 불가능할 수 있으므로, GitHub Pages/Cloudflare Pages/Netlify 등으로 호스팅을 이전하거나 별도 배포 방식을 마련해야 한다.

## 9. 이메일 규칙

수신자: `hysms@hanyang.ac.kr`  
제목 형식: `[원자력 문헌 다이제스트] YYYY-MM-DD 주간 업데이트`

메일 HTML은 `work/build_email_digest.py`가 생성한다. 이메일 클라이언트 제약 때문에 상호작용형 필터·산점도 전체를 메일 본문에 넣지 않고 다음만 제공한다.

- 조사 기간
- 누적/신규 논문/수집 회차 요약
- 주간 연구 토픽 변화
- 저널별 신규 논문 수
- 최신 논문 목록
- 공개 대시보드 버튼

Gmail 전송 시 한글 깨짐을 막기 위해 다음 방식이 필수였다.

1. 이메일 HTML 파일을 UTF-8 **바이트**로 읽는다.
2. Base64URL로 인코딩한다.
3. MIME part를 `text/html`, `charset=UTF-8`, `content_disposition=inline`로 보낸다.
4. 문자열 HTML을 `body.content`에 직접 넣지 않고 `body.base64_url_content`를 사용한다.
5. HTML 파일을 첨부하지 않는다.
6. 보낸편지함에서 같은 제목이 있는지 확인해 중복 발송을 피한다.
7. 발송 후 보낸 메일을 다시 읽어 `원자력공학 최근 논문 다이제스트`, `주간 연구 토픽 변화`, `누적 논문` 등의 한글이 정상인지 확인한다.

주의: Gmail 발송은 로컬 SMTP 코드가 아니라 Codex에 연결된 Gmail 도구로 수행했다. 현재 저장소에는 Gmail 자격증명이나 발송 스크립트가 없다. Claude로 완전 자동화하려면 Gmail API OAuth 또는 SMTP/App Password를 별도로 구성해야 한다.

## 10. 자동화의 설계와 현재 상태

원래 설계는 두 단계다.

1. **월요일 오전 8시:** Windows 작업 스케줄러가 `run_weekly_pipeline.ps1` 실행
2. **월요일 오전 9시:** Codex heartbeat가 `latest-run.json`을 확인한 뒤 Sites 배포 및 Gmail 발송

Codex heartbeat의 검증 조건은 다음과 같았다.

- `status == success`
- `run_date`가 실행일 기준 가장 최근 월요일
- `dashboard_path`, `email_path`, `site_source_path`가 존재하고 비어 있지 않음
- 공개 사이트에서 `period_start`, `period_end`, `article_count` 확인
- 같은 제목의 발송 메일이 없을 것
- 발송 후 한글 인코딩 정상 확인

### 현재 발견된 문제

2026-09-21 자동 실행이 되지 않았다. 2026-09-23 확인 결과:

- Windows 예약 작업 `Codex Nuclear Literature Weekly`: **등록되어 있지 않음**
- `logs/weekly-pipeline-2026-09-21.log`: 없음
- `automation-state/latest-run.json`: `run_date = 2026-09-14`에서 멈춤
- 따라서 2026-09-21분 대시보드 갱신과 메일 발송은 하지 않았다.

`install_weekly_task.cmd`를 관리자 권한으로 한 번 실행하면 등록하도록 만들어 두었지만 실제 등록은 완료되지 않았다. 설치 성공 시 `Installation complete`와 다음 실행 시간이 표시되어야 한다.

또한 예약 작업의 principal은 `LogonType Interactive`이므로 사용자가 로그인된 상태여야 한다. 노트북이 꺼져 있거나 로그아웃 상태이면 실행되지 않을 수 있다. `StartWhenAvailable`, `WakeToRun`, 네트워크 필요 옵션은 설정되어 있다.

## 11. 마지막 정상 실행 상태

`automation-state/latest-run.json` 기준:

| 항목 | 값 |
|---|---|
| status | success |
| run_date | 2026-09-14 |
| period_start | 2026-09-07 |
| period_end | 2026-09-13 |
| article_count | 55 |
| recipient | hysms@hanyang.ac.kr |
| log | `logs/weekly-pipeline-2026-09-14.log` |

누적 DB에는 2026-08-30, 2026-09-07, 2026-09-14 백업이 있다.

## 12. Claude가 이어서 할 권장 작업

우선순위 순서:

1. `install_weekly_task.cmd`를 실행하거나 작업 스케줄러에 동일 작업을 직접 등록한다.
2. `Get-ScheduledTask -TaskName "Codex Nuclear Literature Weekly"`로 등록 여부와 다음 실행 시간을 확인한다.
3. 누락된 2026-09-21 회차를 수동 실행하고 로그/`latest-run.json`/DB integrity를 확인한다.
4. Claude 환경에 맞는 호스팅 배포 방식을 결정한다. 기존 Sites URL을 유지할 수 없으면 새 고정 URL로 이메일 템플릿을 수정한다.
5. Gmail API 또는 SMTP 방식의 발송 스크립트를 구현한다. 인라인 HTML과 UTF-8/Base64URL 규칙을 유지한다.
6. 발송 중복 방지용 상태 테이블 또는 `sent-runs.json`을 로컬에 추가한다.
7. `TOPICS`, `RESEARCH_AREAS`, `WATCHLISTS`, `COUNTRY_NAMES`, 저널 목록을 공용 JSON 설정으로 통합한다.
8. 현재 여러 파일에 하드코딩된 절대 경로를 프로젝트 설정 파일 또는 환경변수로 옮긴다.
9. 사이트와 메일의 DOI 링크가 새 탭/외부 브라우저로 정상 열리는지 검증한다.
10. 주간 실행이 실패하면 성공 메일을 보내지 말고 오류와 로그 경로만 알리도록 유지한다.

## 13. 알려진 제약과 주의사항

- “빠짐없이” 수집한다는 목표는 Crossref 등록 데이터의 완전성에 의존한다. 출판사 페이지에 먼저 올라왔지만 DOI가 해당 기간에 Crossref에 등록되지 않은 논문은 놓칠 수 있다.
- Crossref `created` 날짜는 실제 온라인 출판일과 다를 수 있다.
- Elsevier/출판사 Abstract는 접근 제한이나 API 응답에 따라 비어 있을 수 있다.
- MyMemory 번역은 품질과 호출 제한이 불안정할 수 있다. DOI별 캐시를 보존해야 한다.
- 국가 정보는 OpenAlex 저자 소속 기관 데이터에 의존하므로 누락될 수 있다.
- 현재 토픽 분류는 키워드 규칙 기반이며, 정밀한 의미 분류 모델이 아니다.
- `weekly_pipeline_watcher.ps1`는 무한 루프형 대안이지만 현재 설치 스크립트와 연결되어 있지 않다.
- Google Drive 동기화는 최종적으로 포기했으며 현재 로컬 저장을 기준으로 한다.
- 저장소 밖의 안정 DB 폴더를 실수로 삭제하지 않도록 별도 백업 정책을 마련하는 것이 좋다.

## 14. 빠른 점검 명령

```powershell
# 예약 작업 확인
Get-ScheduledTask -TaskName "Codex Nuclear Literature Weekly"
Get-ScheduledTaskInfo -TaskName "Codex Nuclear Literature Weekly"

# 최신 상태 확인
Get-Content .\automation-state\latest-run.json -Raw

# 최신 로그 확인
Get-Content .\logs\weekly-pipeline-2026-09-14.log -Tail 100

# SQLite integrity 확인
& "C:\Program Files\Python310\python.exe" -c "import sqlite3; p=r'C:\Users\Idaho_S\Documents\Codex\nuclear-literature-db\data\working.sqlite'; c=sqlite3.connect(p); print(c.execute('pragma integrity_check').fetchone()[0])"
```

## 15. 인수인계 핵심 요약

로컬 수집·DB·HTML·Excel 생성 코드는 이미 작동했고, 2026-09-14 회차까지 정상 결과가 존재한다. 남은 핵심은 **Windows 예약 작업 등록**, **Claude에서 사용할 수 있는 정적 사이트 배포 수단**, **Gmail 인증을 포함한 실제 발송 코드** 세 가지다. 기존 공개 사이트와 Gmail 발송은 Codex 전용 도구에 의존했으므로 Claude에서 그대로 재사용할 수 있다고 가정하면 안 된다.
