"""Cumulative database page (docs/database.html): every stored paper, searchable and filterable.

Static single file: paper data is embedded as JSON and filtered in the browser (no external libraries).
"""
import html
import json
from collections import Counter, defaultdict
from datetime import date, timedelta

from .common import SETTINGS

NAV_CSS = (
    ".sitenav{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}"
    ".sitenav a{padding:7px 13px;border:1px solid #d9e2ec;border-radius:999px;background:#fff;color:#075985;"
    "font-size:13px;font-weight:700;text-decoration:none}.sitenav a.on{background:#0b6bcb;border-color:#0b6bcb;color:#fff}"
)


def nav_html(active, prefix="./"):
    items = [("index", "이번 주 동향", "index.html"), ("database", "누적 데이터베이스", "database.html"),
             ("excel", "Excel 내려받기", "nuclear-literature-database.xlsx")]
    links = "".join(
        f'<a href="{prefix}{href}"{" class=on" if key == active else ""}>{label}</a>' for key, label, href in items
    )
    return f'<nav class="sitenav">{links}</nav>'


def week_of(value):
    day = date.fromisoformat(value[:10])
    return (day - timedelta(days=day.weekday())).isoformat()


def render(payload, archive_ids):
    papers = payload["papers"]
    topics_by_doi = defaultdict(list)
    for link in payload["paper_topics"]:
        topics_by_doi[link["doi"]].append(link["topic_ko"])
    rows = []
    for p in papers:
        registered = p.get("doi_registered_date") or ""
        rows.append({
            "d": p["doi"], "t": p["title_en"], "k": p.get("title_ko") or "", "j": p["journal"],
            "a": p.get("authors") or "", "r": registered, "w": week_of(registered) if registered else "",
            "p": p["primary_topic"], "tp": topics_by_doi.get(p["doi"], [p["primary_topic"]]),
            "c": [c for c in (p.get("countries") or "").split(";") if c], "o": int(bool(p.get("open_access"))),
            "y": p["document_type"], "ab": p.get("abstract") or "",
        })

    weeks = sorted({r["w"] for r in rows if r["w"]})
    topic_order = list(SETTINGS["topics"]) + [SETTINGS["fallback_topic"]]
    journals = [j for j, _ in Counter(r["j"] for r in rows).most_common()]
    countries = [c for c, _ in Counter(c for r in rows for c in r["c"]).most_common()]
    first, last = (min(r["r"] for r in rows), max(r["r"] for r in rows)) if rows else ("", "")
    meta = {
        "weeks": weeks, "topics": topic_order, "journals": journals, "countries": countries,
        "countryNames": SETTINGS["country_names"], "archives": sorted(archive_ids, reverse=True),
    }
    data_json = json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    esc = lambda v: html.escape(str(v), quote=True)
    oa = sum(r["o"] for r in rows)
    with_abstract = sum(bool(r["ab"]) for r in rows)
    with_country = sum(bool(r["c"]) for r in rows)

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>원자력 문헌 누적 DB</title>
<style>
:root{{--navy:#102a43;--blue:#0b6bcb;--sky:#eaf4ff;--line:#d9e2ec;--ink:#243b53;--muted:#627d98;--bg:#f5f8fb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Arial,'Noto Sans KR',sans-serif;line-height:1.55}}
.wrap{{max-width:1080px;margin:auto;padding:28px 16px 80px}}
header{{background:linear-gradient(135deg,#102a43,#1668a9);color:#fff;border-radius:18px;padding:30px;margin-bottom:16px}}
header h1{{margin:0 0 8px;font-size:28px}}header p{{margin:4px 0;color:#d9edff}}
{NAV_CSS}
.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:0 0 14px}}
.metric{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px;text-align:center;font-size:12px;color:var(--muted)}}
.metric strong{{display:block;font-size:22px;color:var(--navy)}}
.panel{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}}
.panel h2{{margin:0 0 4px;font-size:18px;color:var(--navy)}}.hint{{margin:0 0 12px;color:var(--muted);font-size:12px}}
.bars{{display:flex;align-items:flex-end;gap:6px;height:190px;padding-top:18px;border-bottom:1px solid var(--line)}}
.bar{{flex:1;min-width:14px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;cursor:pointer;border:0;background:none;padding:0;font:inherit}}
.bar i{{display:block;width:100%;max-width:38px;background:var(--blue);border-radius:4px 4px 0 0;min-height:2px}}
.bar b{{font-size:11px;color:var(--ink);margin-bottom:3px}}.bar:hover i,.bar.on i{{background:var(--navy)}}
.xlabels{{display:flex;gap:6px}}.xlabels span{{flex:1;min-width:14px;text-align:center;font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden}}
.heat-wrap{{overflow-x:auto}}table.heat{{border-collapse:separate;border-spacing:2px;font-size:12px;width:100%}}
.heat th{{font-weight:400;color:var(--muted);font-size:11px;padding:2px 4px;white-space:nowrap}}.heat th.row{{text-align:left;color:var(--ink);font-size:12px}}
.heat td{{text-align:center;padding:6px 2px;border-radius:4px;cursor:pointer;min-width:34px}}.heat td.z{{color:#b6c2cf}}.heat td:hover{{outline:2px solid var(--navy)}}
.filters{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:8px;margin-bottom:8px}}
.filters input,.filters select{{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:13px;background:#fff;color:var(--ink)}}
.filters2{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;color:var(--muted)}}
.filters2 input[type=date]{{padding:7px 8px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:13px}}
button.act{{padding:8px 13px;border:1px solid var(--line);border-radius:8px;background:#fff;color:#075985;font:inherit;font-size:13px;font-weight:700;cursor:pointer}}
button.act:hover{{background:var(--sky)}}
.status{{margin:12px 0;padding:10px 14px;background:var(--sky);border-left:4px solid var(--blue);border-radius:7px;font-size:13px}}
.paper{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:10px;padding:14px 16px;margin:10px 0}}
.top{{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;color:var(--muted)}}.top .jr{{background:#edf2f7;padding:1px 8px;border-radius:999px}}
.paper h3{{margin:6px 0 2px;font-size:15px;line-height:1.4}}.paper h3 a{{color:#075985;text-decoration:none}}.paper h3 a:hover{{text-decoration:underline}}
.ko{{color:var(--navy);font-size:14px}}.au{{color:var(--muted);font-size:12px;margin-top:4px}}
.tag{{display:inline-block;margin:4px 4px 0 0;padding:2px 8px;border-radius:999px;background:var(--sky);color:#075985;font-size:11px}}
details{{margin-top:6px;font-size:13px}}summary{{cursor:pointer;color:var(--blue);font-size:12px}}
.pager{{display:flex;justify-content:center;align-items:center;gap:10px;margin:16px 0;font-size:13px}}
.archive{{display:flex;flex-wrap:wrap;gap:8px}}.archive a{{padding:6px 11px;border:1px solid var(--line);border-radius:8px;color:#075985;text-decoration:none;font-size:13px;background:#fff}}
footer{{margin-top:28px;color:var(--muted);font-size:12px;text-align:center}}
@media(max-width:760px){{.metrics{{grid-template-columns:repeat(3,1fr)}}.filters{{grid-template-columns:1fr 1fr}}.filters input{{grid-column:1/-1}}header{{padding:22px}}}}
</style></head>
<body><div class="wrap">
{nav_html("database")}
<header><h1>원자력공학 문헌 누적 데이터베이스</h1>
<p>{len(journals)}개 저널 · DOI 등록일 {esc(first)} ~ {esc(last)} · DOI 기준 중복 제거</p>
<p>검색·필터 결과는 CSV로, 전체 DB는 Excel로 내려받을 수 있습니다.</p></header>

<section class="metrics">
<div class="metric"><strong>{len(rows)}</strong>누적 논문</div>
<div class="metric"><strong>{len(payload["runs"])}</strong>수집 회차</div>
<div class="metric"><strong>{len(weeks)}</strong>주간(등록일 기준)</div>
<div class="metric"><strong>{with_abstract}</strong>초록 보유</div>
<div class="metric"><strong>{oa}</strong>Open Access</div>
<div class="metric"><strong>{round(with_country / max(len(rows), 1) * 100)}%</strong>국가정보 보유</div>
</section>

<section class="panel"><h2>주간 신규 논문 수</h2>
<p class="hint">DOI 등록일이 속한 주(월요일 기준). 막대를 누르면 그 주 논문만 아래 목록에 표시합니다.</p>
<div class="bars" id="bars"></div><div class="xlabels" id="xlabels"></div></section>

<section class="panel"><h2>주간 토픽 분포</h2>
<p class="hint">칸의 숫자는 논문 수이며, 색이 진할수록 그 주 전체 대비 비중이 큽니다. 칸을 누르면 해당 토픽·주간으로 필터합니다.</p>
<div class="heat-wrap"><table class="heat" id="heat"></table></div></section>

<section class="panel"><h2>논문 검색</h2>
<div class="filters">
<input id="q" type="search" placeholder="제목(영/한), 저자, 초록, DOI 검색">
<select id="fj"><option value="">전체 저널</option></select>
<select id="ft"><option value="">전체 토픽</option></select>
<select id="fc"><option value="">전체 국가</option></select>
<select id="fy"><option value="">전체 문서유형</option></select>
</div>
<div class="filters2">DOI 등록일 <input type="date" id="d1"> ~ <input type="date" id="d2">
<label><input type="checkbox" id="fo"> Open Access만</label>
<label><input type="checkbox" id="fa"> 초록 있는 논문만</label>
<select id="sort" class="act"><option value="new">최신순</option><option value="old">오래된순</option><option value="journal">저널순</option></select>
<button class="act" id="reset" type="button">필터 초기화</button>
<button class="act" id="csv" type="button">검색 결과 CSV</button></div>
<div class="status" id="status"></div>
<div id="list"></div>
<div class="pager"><button class="act" id="prev" type="button">이전</button><span id="page"></span><button class="act" id="next" type="button">다음</button></div>
</section>

<section class="panel"><h2>회차별 대시보드</h2><p class="hint">매주 발행된 동향 대시보드 원본입니다.</p><div class="archive" id="archive"></div></section>

<footer>수집 기준: Crossref DOI created date · 국가·OA·초록: OpenAlex · 토픽: 제목+초록 키워드 규칙 · 매주 월요일 자동 갱신</footer>
</div>
<script id="data" type="application/json">{data_json}</script>
<script>
(() => {{
const D = JSON.parse(document.getElementById('data').textContent), R = D.rows, M = D.meta;
const $ = id => document.getElementById(id), PER = 50;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const cname = c => (M.countryNames[c] || c) + ' (' + c + ')';
const endOf = w => {{ const d = new Date(w + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 6); return d.toISOString().slice(0, 10); }};
let page = 0, weekSel = '';
R.forEach(r => r.s = (r.t + ' ' + r.k + ' ' + r.a + ' ' + r.ab + ' ' + r.d).toLowerCase());

const fill = (id, vals, label) => $(id).insertAdjacentHTML('beforeend', vals.map(v => `<option value="${{esc(v)}}">${{esc(label ? label(v) : v)}}</option>`).join(''));
fill('fj', M.journals); fill('ft', M.topics); fill('fc', M.countries, cname);
fill('fy', [...new Set(R.map(r => r.y))]);
$('archive').innerHTML = M.archives.map(a => `<a href="./archive/${{a}}.html">${{a}}</a>`).join('') || '<span class="hint">아직 없음</span>';

// Weekly bars (single series: no legend; value label on top, native tooltip on hover)
const wc = {{}}; R.forEach(r => wc[r.w] = (wc[r.w] || 0) + 1);
const wmax = Math.max(1, ...M.weeks.map(w => wc[w] || 0));
$('bars').innerHTML = M.weeks.map(w => `<button class="bar" data-w="${{w}}" title="${{w}} ~ ${{endOf(w)}}: ${{wc[w] || 0}}편"><b>${{wc[w] || 0}}</b><i style="height:${{(wc[w] || 0) / wmax * 150}}px"></i></button>`).join('');
$('xlabels').innerHTML = M.weeks.map(w => `<span>${{w.slice(5)}}</span>`).join('');
$('bars').addEventListener('click', e => {{ const b = e.target.closest('.bar'); if (!b) return; setWeek(weekSel === b.dataset.w ? '' : b.dataset.w); }});

// Topic x week heatmap: one hue, lightness by within-week share; counts printed in every cell
const tw = {{}}; R.forEach(r => r.tp.forEach(t => {{ const k = t + '|' + r.w; tw[k] = (tw[k] || 0) + 1; }}));
const shade = f => `rgba(11,107,203,${{(0.08 + 0.85 * f).toFixed(2)}})`;
$('heat').innerHTML = '<tr><th></th>' + M.weeks.map(w => `<th>${{w.slice(5)}}</th>`).join('') + '<th>합계</th></tr>' +
  M.topics.map(t => {{
    let total = 0;
    const cells = M.weeks.map(w => {{
      const n = tw[t + '|' + w] || 0, f = n / Math.max(1, wc[w] || 0); total += n;
      return n ? `<td data-t="${{esc(t)}}" data-w="${{w}}" style="background:${{shade(Math.min(1, f / 0.5))}};color:${{f > 0.3 ? '#fff' : '#102a43'}}" title="${{esc(t)}} · ${{w}}주: ${{n}}편 (${{Math.round(f * 100)}}%)">${{n}}</td>` : `<td class="z" data-t="${{esc(t)}}" data-w="${{w}}">·</td>`;
    }}).join('');
    return `<tr><th class="row">${{esc(t)}}</th>${{cells}}<th>${{total}}</th></tr>`;
  }}).join('');
$('heat').addEventListener('click', e => {{ const c = e.target.closest('td'); if (!c) return; $('ft').value = c.dataset.t; setWeek(c.dataset.w); }});
const note = document.createElement('p'); note.className = 'hint'; note.textContent = '한 논문이 여러 토픽에 해당하면 각 토픽에 모두 집계됩니다.'; $('heat').after(note);

function setWeek(w) {{ weekSel = w; $('d1').value = w; $('d2').value = w ? endOf(w) : ''; page = 0; draw(); $('list').scrollIntoView({{behavior: 'smooth', block: 'start'}}); }}

function filtered() {{
  const q = $('q').value.trim().toLowerCase().split(/\\s+/).filter(Boolean);
  const j = $('fj').value, t = $('ft').value, c = $('fc').value, y = $('fy').value, d1 = $('d1').value, d2 = $('d2').value;
  const out = R.filter(r => (!j || r.j === j) && (!t || r.tp.includes(t)) && (!c || r.c.includes(c)) && (!y || r.y === y)
    && (!d1 || r.r >= d1) && (!d2 || r.r <= d2) && (!$('fo').checked || r.o) && (!$('fa').checked || r.ab)
    && q.every(x => r.s.includes(x)));
  const s = $('sort').value;
  out.sort((a, b) => s === 'old' ? a.r.localeCompare(b.r) : s === 'journal' ? a.j.localeCompare(b.j) || b.r.localeCompare(a.r) : b.r.localeCompare(a.r));
  return out;
}}

function draw() {{
  const rows = filtered(), pages = Math.max(1, Math.ceil(rows.length / PER));
  page = Math.min(page, pages - 1);
  document.querySelectorAll('.bar').forEach(b => b.classList.toggle('on', b.dataset.w === weekSel));
  $('status').textContent = `${{rows.length}}편 / 전체 ${{R.length}}편`;
  $('page').textContent = `${{page + 1}} / ${{pages}}`;
  $('prev').disabled = page === 0; $('next').disabled = page >= pages - 1;
  $('list').innerHTML = rows.slice(page * PER, page * PER + PER).map(r => {{
    const au = r.a.split('; ').filter(Boolean), auText = au.slice(0, 6).join(', ') + (au.length > 6 ? ' et al.' : '');
    return `<article class="paper"><div class="top"><span>${{r.r}}</span><span class="jr">${{esc(r.j)}}</span><span>${{esc(r.y)}}</span>${{r.o ? '<span>Open Access</span>' : ''}}</div>
<h3><a href="https://doi.org/${{esc(r.d)}}" target="_blank" rel="noopener">${{esc(r.t)}}</a></h3><div class="ko">${{esc(r.k)}}</div>
<div class="au">${{esc(auText)}}${{r.c.length ? ' · ' + r.c.map(cname).join(', ') : ''}}</div>
<div>${{r.tp.map(t => `<span class="tag">${{esc(t)}}</span>`).join('')}}</div>
${{r.ab ? `<details><summary>초록 보기</summary><p>${{esc(r.ab)}}</p></details>` : ''}}</article>`;
  }}).join('') || '<p class="hint">조건에 맞는 논문이 없습니다.</p>';
}}

['q', 'fj', 'ft', 'fc', 'fy', 'd1', 'd2', 'fo', 'fa', 'sort'].forEach(id => $(id).addEventListener('input', () => {{ page = 0; if (id === 'd1' || id === 'd2') weekSel = ''; draw(); }}));
$('prev').onclick = () => {{ page--; draw(); $('list').scrollIntoView(); }};
$('next').onclick = () => {{ page++; draw(); $('list').scrollIntoView(); }};
$('reset').onclick = () => {{ ['q', 'fj', 'ft', 'fc', 'fy', 'd1', 'd2'].forEach(id => $(id).value = ''); $('fo').checked = $('fa').checked = false; weekSel = ''; page = 0; draw(); }};
$('csv').onclick = () => {{
  const cols = [['doi', 'd'], ['title_en', 't'], ['title_ko', 'k'], ['journal', 'j'], ['authors', 'a'], ['doi_registered', 'r'], ['primary_topic', 'p'], ['countries', 'c'], ['open_access', 'o'], ['abstract', 'ab']];
  const cell = v => '"' + String(Array.isArray(v) ? v.join(';') : v ?? '').replace(/"/g, '""') + '"';
  const text = '\\ufeff' + [cols.map(c => c[0]).join(','), ...filtered().map(r => cols.map(c => cell(r[c[1]])).join(','))].join('\\r\\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {{type: 'text/csv;charset=utf-8'}}));
  a.download = 'nuclear-literature-filtered.csv'; a.click(); URL.revokeObjectURL(a.href);
}};
draw();
}})();
</script></body></html>"""
