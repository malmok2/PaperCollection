import html
import json
import os
from collections import Counter
from datetime import date, timedelta
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
RUN_DATE = os.environ.get("NUCLEAR_RUN_DATE", date.today().isoformat())
PERIOD_START = os.environ.get("NUCLEAR_PERIOD_START", (date.fromisoformat(RUN_DATE) - timedelta(days=7)).isoformat())
PERIOD_END = os.environ.get("NUCLEAR_PERIOD_END", (date.fromisoformat(RUN_DATE) - timedelta(days=1)).isoformat())
PREVIOUS_START = os.environ.get("NUCLEAR_PREVIOUS_START", (date.fromisoformat(PERIOD_START) - timedelta(days=7)).isoformat())
PREVIOUS_END = os.environ.get("NUCLEAR_PREVIOUS_END", (date.fromisoformat(PERIOD_END) - timedelta(days=7)).isoformat())
OUTPUT = BASE / "outputs" / f"nuclear-literature-email-{RUN_DATE}.html"

records = json.loads((BASE / "work" / "articles.json").read_text(encoding="utf-8"))
previous = json.loads((BASE / "work" / "articles_previous.json").read_text(encoding="utf-8"))
database = json.loads((BASE / "work" / "db_export.json").read_text(encoding="utf-8"))
translations = (BASE / "work" / "title_translations_ko.txt").read_text(encoding="utf-8").splitlines()
db_by_doi = {paper["doi"]: paper for paper in database["papers"]}


def esc(value):
    return html.escape(str(value or ""), quote=True)


for record, title_ko in zip(records, translations):
    record["title_ko"] = title_ko
    db_record = db_by_doi.get(record["doi"], {})
    record["topic"] = db_record.get("primary_topic") or "기타 원자력"
    record["abstract_url"] = record.get("publisher_url") or record.get("doi_url")

current_topics = Counter(record["topic"] for record in records)
previous_topics = Counter((db_by_doi.get(record["doi"], {}).get("primary_topic") or "기타 원자력") for record in previous)
journals = Counter(record["journal"] for record in records)

topic_rows = "".join(
    f'''<tr>
      <td>{esc(topic)}</td><td class="num muted">{previous_topics[topic]}</td><td class="num strong">{count}</td>
      <td class="num strong" style="color:{'#087f5b' if count-previous_topics[topic] > 0 else '#c92a2a' if count-previous_topics[topic] < 0 else '#627d98'}">{count-previous_topics[topic]:+d}</td>
    </tr>'''
    for topic, count in current_topics.most_common()
)

journal_rows = "".join(
    f'''<tr><td>{esc(journal)}</td><td class="num strong">{count}</td></tr>'''
    for journal, count in journals.most_common()
)

paper_rows = []
for index, record in enumerate(records, 1):
    authors = ", ".join(record.get("authors", [])[:5])
    if len(record.get("authors", [])) > 5:
        authors += " et al."
    paper_rows.append(f'''<tr>
      <td class="paper-no">{index:03d}</td><td class="paper-body">
        <a href="{esc(record['doi_url'])}" class="paper-title">{esc(record['title'])}</a>
        <div class="title-ko">{esc(record['title_ko'])}</div><div class="authors">{esc(authors)}</div>
        <div class="meta">{esc(record['journal'])} · {esc(record['topic'])} · DOI 등록 {esc(record['registered_date'])} · <a href="{esc(record['abstract_url'])}">Abstract/출판사</a></div>
      </td>
    </tr>''')

document = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{{margin:0;background:#f5f8fb;color:#243b53;font-family:Arial,'Noto Sans KR',sans-serif;line-height:1.55}}table{{width:100%;border-collapse:collapse;font-size:13px}}td{{padding:7px 8px;border-bottom:1px solid #e6edf3}}a{{color:#075985}}.num{{text-align:right}}.muted,.authors{{color:#627d98}}.strong,.paper-title{{font-weight:700}}.paper-no,.paper-body{{padding:12px 8px;border-bottom:1px solid #d9e2ec;vertical-align:top}}.paper-no{{color:#0b6bcb;font-weight:700}}.paper-title{{text-decoration:none}}.title-ko{{margin-top:4px;color:#102a43}}.authors{{margin-top:6px;font-size:12px}}.meta{{margin-top:5px;color:#52677b;font-size:12px}}
</style></head>
<body style="margin:0;background:#f5f8fb;color:#243b53;font-family:Arial,'Noto Sans KR',sans-serif;line-height:1.55">
<div style="max-width:760px;margin:0 auto;padding:22px 12px">
  <div style="background:#102a43;color:#ffffff;padding:24px;border-radius:12px">
    <h1 style="margin:0 0 8px;font-size:25px">원자력공학 최근 논문 다이제스트</h1>
    <div style="color:#d9edff">{PERIOD_START} ~ {PERIOD_END} · 최근 1주 DOI 신규 등록 기준</div>
    <div style="margin-top:16px"><a href="https://nuclear-literature-dashboard.ssrmin.chatgpt.site" style="display:inline-block;background:#ffffff;color:#075985;text-decoration:none;font-weight:700;padding:10px 16px;border-radius:7px">대화형 대시보드 열기</a></div>
  </div>
  <table role="presentation" style="width:100%;border-collapse:separate;border-spacing:8px;margin:12px 0">
    <tr>
      <td style="width:33%;background:#ffffff;border:1px solid #d9e2ec;padding:13px;text-align:center"><strong style="display:block;font-size:24px;color:#102a43">{len(database['papers'])}</strong>누적 논문</td>
      <td style="width:33%;background:#ffffff;border:1px solid #d9e2ec;padding:13px;text-align:center"><strong style="display:block;font-size:24px;color:#102a43">{len(records)}</strong>이번 신규 논문</td>
      <td style="width:33%;background:#ffffff;border:1px solid #d9e2ec;padding:13px;text-align:center"><strong style="display:block;font-size:24px;color:#102a43">{len(database['runs'])}</strong>수집 기간</td>
    </tr>
  </table>
  <div style="background:#ffffff;border:1px solid #d9e2ec;padding:16px;margin:12px 0">
    <h2 style="margin:0 0 9px;font-size:18px;color:#102a43">주간 연구 토픽 변화</h2>
    <p style="margin:0 0 8px;color:#627d98;font-size:12px">{PREVIOUS_START}~{PREVIOUS_END} 대비 {PERIOD_START}~{PERIOD_END}</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr><th style="padding:7px 8px;text-align:left;background:#eaf4ff">토픽</th><th style="padding:7px 8px;text-align:right;background:#eaf4ff">직전</th><th style="padding:7px 8px;text-align:right;background:#eaf4ff">현재</th><th style="padding:7px 8px;text-align:right;background:#eaf4ff">변화</th></tr></thead><tbody>{topic_rows}</tbody></table>
  </div>
  <div style="background:#ffffff;border:1px solid #d9e2ec;padding:16px;margin:12px 0">
    <h2 style="margin:0 0 9px;font-size:18px;color:#102a43">저널별 신규 논문</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px">{journal_rows}</table>
  </div>
  <div style="background:#ffffff;border:1px solid #d9e2ec;padding:16px;margin:12px 0">
    <h2 style="margin:0 0 4px;font-size:18px;color:#102a43">최신 논문 {len(records)}편</h2>
    <p style="margin:0 0 8px;color:#627d98;font-size:12px">논문 제목을 누르면 DOI 페이지로, Abstract/출판사를 누르면 공개된 출판사 페이지로 이동합니다.</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">{''.join(paper_rows)}</table>
  </div>
  <p style="color:#627d98;font-size:11px;text-align:center">수집 기준: Crossref DOI created date. 온라인 공개일·권호일과 다를 수 있습니다.</p>
</div></body></html>'''

OUTPUT.write_text(document, encoding="utf-8")
print(json.dumps({"output": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "papers": len(records)}, ensure_ascii=False))
