import html
import json
import os
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / "work" / "articles.json"
RUN_DATE = os.environ.get("NUCLEAR_RUN_DATE", date.today().isoformat())
PERIOD_START = os.environ.get("NUCLEAR_PERIOD_START", (date.fromisoformat(RUN_DATE) - timedelta(days=7)).isoformat())
PERIOD_END = os.environ.get("NUCLEAR_PERIOD_END", (date.fromisoformat(RUN_DATE) - timedelta(days=1)).isoformat())
PREVIOUS_START = os.environ.get("NUCLEAR_PREVIOUS_START", (date.fromisoformat(PERIOD_START) - timedelta(days=7)).isoformat())
PREVIOUS_END = os.environ.get("NUCLEAR_PREVIOUS_END", (date.fromisoformat(PERIOD_END) - timedelta(days=7)).isoformat())
OUTPUT = BASE / "outputs" / f"nuclear-literature-digest-{RUN_DATE}.html"
DB_EXPORT = BASE / "work" / "db_export.json"

RESEARCH_AREAS = {
    "열수력·유체": ["flow", "thermal", "heat", "boiling", "condensation", "coolant", "hydraulic", "fluid", "turbulence", "pressure drop", "void fraction", "pump"],
    "원자로물리·해석": ["neutron", "reactor physics", "core analysis", "criticality", "monte carlo", "geant4", "cross section", "burnup", "kinetics"],
    "안전·사고·리스크": ["safety", "accident", "risk", "loca", "tsunami", "reliability", "severe", "emergency", "hazard"],
    "핵연료·재료": ["fuel", "cladding", "material", "irradiation", "steel", "zircon", "alloy", "corrosion", "defect", "composite"],
    "AI·디지털": ["machine learning", "deep learning", "neural", "artificial intelligence", "ai-driven", "reinforcement learning", "physics-informed", "digital twin", "surrogate", "reduced-order", "reduced order", "cnn", "lstm"],
    "방사선·계측": ["radiation", "detector", "dosim", "shield", "source localization", "spectr", "instrument", "measurement", "magnet"],
    "핵연료주기·폐기물": ["waste", "spent fuel", "fuel cycle", "pyroprocessing", "decommission", "disposal", "incineration", "storage"],
    "설계·운전·경제": ["design", "operation", "maintenance", "economic", "cost", "control room", "optimization", "management", "policy", "sociotechnical"],
}

WATCHLISTS = {
    "열수력": ["thermal", "hydraulic", "heat transfer", "coolant", "fluid", "flow"],
    "다상유동·비등": ["multiphase", "two-phase", "two phase", "boiling", "bubble", "void fraction", "critical heat flux", "chf", "condensation"],
    "유동가시화": ["flow visualization", "visualization", "tomography", "particle image", "piv", "x-ray", "high-speed imaging", "image-based"],
    "안전·사고해석": ["safety", "accident", "loca", "severe accident", "risk", "emergency", "hazard"],
    "원자로물리": ["neutron", "reactor physics", "core analysis", "criticality", "monte carlo", "cross section", "burnup", "kinetics"],
    "핵연료·재료": ["fuel", "cladding", "material", "irradiation", "steel", "zircon", "alloy", "corrosion"],
    "Machine Learning": ["machine learning", "deep learning", "neural", "artificial intelligence", "reinforcement learning", "cnn", "lstm", "ai-driven"],
    "Digital Twin·PINN": ["digital twin", "physics-informed", "pinn", "surrogate", "reduced-order", "reduced order"],
}

COUNTRY_NAMES = {
    "AE":"아랍에미리트","AU":"호주","BD":"방글라데시","BE":"벨기에","BR":"브라질","CA":"캐나다","CN":"중국","CZ":"체코",
    "DE":"독일","EG":"이집트","ES":"스페인","FR":"프랑스","GB":"영국","GH":"가나","GR":"그리스","HK":"홍콩","HU":"헝가리",
    "ID":"인도네시아","IN":"인도","IQ":"이라크","IR":"이란","IT":"이탈리아","JO":"요르단","JP":"일본","KR":"대한민국","LB":"레바논",
    "LT":"리투아니아","MA":"모로코","MN":"몽골","MX":"멕시코","MY":"말레이시아","NL":"네덜란드","PE":"페루","PK":"파키스탄",
    "PL":"폴란드","PT":"포르투갈","RO":"루마니아","RS":"세르비아","RU":"러시아","SA":"사우디아라비아","SD":"수단","SE":"스웨덴",
    "SG":"싱가포르","SI":"슬로베니아","TR":"튀르키예","TW":"대만","UA":"우크라이나","US":"미국","VN":"베트남","YE":"예멘",
    "ZA":"남아프리카공화국","ZM":"잠비아",
}

def country_codes(record):
    values = record.get("countries") or []
    if isinstance(values, str):
        values = values.split(";")
    return [value for value in values if value]

def country_label(code):
    return f"{COUNTRY_NAMES.get(code, code)} ({code})"


def topic_tags(title):
    lowered = title.lower()
    matches = [topic for topic, terms in RESEARCH_AREAS.items() if any(term in lowered for term in terms)]
    return matches or ["기타 원자력"]


def document_type(title):
    lowered = title.lower()
    if "corrigendum" in lowered:
        return "정오표"
    if title.strip().lower() == "editorial board" or lowered.startswith("introduction:"):
        return "편집물"
    if any(term in lowered for term in ["review", "recent progress", "perspective", "retrospective"]):
        return "리뷰·관점"
    return "연구논문"


def provisional_intro(title, tags):
    lowered = title.lower()
    if "machine learning" in lowered or "artificial intelligence" in lowered or "ai-driven" in lowered or "reinforcement learning" in lowered:
        return "AI·기계학습을 이용해 원자력 계통의 예측, 진단 또는 최적화 문제를 다룬 연구입니다."
    if "cfd" in lowered or "computational fluid" in lowered or "eulerian" in lowered:
        return "전산유체역학 모델을 이용해 원자로 내부 유동과 열전달 현상을 해석한 연구입니다."
    if "boiling" in lowered or "critical heat flux" in lowered or "chf" in lowered:
        return "비등 열전달 또는 임계열유속과 관련된 모델·실험·안전여유를 검토한 연구입니다."
    if "condensation" in lowered:
        return "응축 열전달과 비응축성 기체 등 원전 안전계통의 주요 열수력 현상을 다룬 연구입니다."
    if "smr" in lowered or "microreactor" in lowered:
        return "SMR 또는 마이크로리액터의 설계·성능·안전 특성을 평가한 연구입니다."
    if "accident" in lowered or "loca" in lowered or "corium" in lowered:
        return "사고 조건에서의 원전 거동과 안전성 평가 또는 완화 전략을 다룬 연구입니다."
    if tags:
        return f"{', '.join(tags)} 관점에서 원자력 시스템의 성능 또는 해석 방법을 다룬 연구입니다."
    return "제목상 원자력 시스템의 설계, 해석, 운전 또는 기반 기술을 다룬 연구입니다."


records = json.loads(SOURCE.read_text(encoding="utf-8"))
previous_records = json.loads((BASE / "work" / "articles_previous.json").read_text(encoding="utf-8"))
database = json.loads(DB_EXPORT.read_text(encoding="utf-8"))
cumulative_records = database["papers"]
translations = (BASE / "work" / "title_translations_ko.txt").read_text(encoding="utf-8").splitlines()
if len(translations) != len(records):
    raise ValueError(f"Korean title count mismatch: {len(translations)} translations for {len(records)} records")
for record, translated_title in zip(records, translations):
    record["title_ko"] = translated_title

# The one abstract that was explicitly retrieved and verified in the authenticated publisher page.
verified_doi = "10.1016/j.nucengdes.2026.115177"
verified_summary = (
    "BWR 전길이 핵연료집합체의 비등유동을 Eulerian two-fluid CFD와 20개 기포 크기군 PBM으로 해석했다. "
    "SIRIUS-3D X선 단층촬영 자료와 비교해 공극률 분포를 재현했으며, 중간 높이에서 lift-force 계수 조정의 영향을 확인했다."
)

for record in records:
    tags = topic_tags(record["title"])
    record["areas"] = tags
    record["primary_area"] = tags[0]
    record["document_type"] = document_type(record["title"])
    if record["doi"] == verified_doi:
        record["summary"] = verified_summary
        record["summary_basis"] = "출판사 Abstract 확인"
        record["areas"] = ["열수력·유체"]
        record["primary_area"] = "열수력·유체"
    else:
        record["summary"] = ""
        record["summary_basis"] = "제목·서지정보 확인"

by_journal = Counter(record["journal"] for record in records)
area_counts = Counter(record["primary_area"] for record in records)
date_counts = Counter(record["registered_date"] for record in records)
previous_area_counts = Counter(topic_tags(record["title"])[0] for record in previous_records)
type_counts = Counter(record["document_type"] for record in records)
country_counts = Counter(code for record in records for code in country_codes(record))
cumulative_country_counts = Counter(code for record in cumulative_records for code in country_codes(record))
country_coverage = sum(bool(country_codes(record)) for record in records)

# Title-based semantic map: TF-IDF (unigrams+bigrams) projected to two dimensions.
vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
title_matrix = vectorizer.fit_transform(record["title"] for record in records)
topic_xy = TruncatedSVD(n_components=2, random_state=42).fit_transform(title_matrix)
for record, (x_value, y_value) in zip(records, topic_xy):
    record["topic_x"] = float(x_value)
    record["topic_y"] = float(y_value)

kmeans = KMeans(n_clusters=7, random_state=42, n_init=20).fit(title_matrix)
terms = vectorizer.get_feature_names_out()
cluster_names = {}
for cluster_id in range(7):
    member_indices = [i for i, label in enumerate(kmeans.labels_) if label == cluster_id]
    dominant_area = Counter(records[i]["primary_area"] for i in member_indices).most_common(1)[0][0]
    center_terms = [terms[i] for i in kmeans.cluster_centers_[cluster_id].argsort()[::-1] if len(terms[i]) > 3][:1]
    cluster_names[cluster_id] = f"{dominant_area} · {center_terms[0]}"
    for i in member_indices:
        records[i]["cluster"] = cluster_id

keyword_stop = list(TfidfVectorizer(stop_words="english").get_stop_words()) + [
    "nuclear", "reactor", "study", "analysis", "model", "modeling", "development", "assessment", "using", "based", "system", "systems",
    "characteristics", "approach", "condition", "conditions", "case", "effect", "effects", "performance", "method", "methods", "experimental",
    "numerical", "evaluation", "investigation", "results", "application", "new", "integrated", "energy", "implications"
]
keyword_vectorizer = CountVectorizer(stop_words=keyword_stop, ngram_range=(1, 1), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9-]{2,}\b")
keyword_matrix = keyword_vectorizer.fit_transform(record["title"].lower() for record in records)
keyword_totals = keyword_matrix.sum(axis=0).A1
keyword_names = keyword_vectorizer.get_feature_names_out()
top_keywords = sorted(zip(keyword_names, keyword_totals), key=lambda item: (-item[1], item[0]))[:18]


def paper_text(record):
    return " ".join([
        record.get("title", record.get("title_en", "")) or "",
        record.get("abstract", "") or "",
    ]).lower()


def count_keywords(items):
    texts = [paper_text(item) for item in items]
    vectorizer = CountVectorizer(stop_words=keyword_stop, ngram_range=(1, 2), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9-]{2,}\b")
    matrix = vectorizer.fit_transform(texts)
    totals = matrix.sum(axis=0).A1
    return Counter({word: int(value) for word, value in zip(vectorizer.get_feature_names_out(), totals)})


current_keyword_counts = count_keywords(records)
previous_keyword_counts = count_keywords(previous_records)
keyword_candidates = []
for word, current_count in current_keyword_counts.items():
    if current_count < 2 or word in {"nuclear energy", "nuclear engineering", "reactor system"}:
        continue
    previous_count = previous_keyword_counts[word]
    current_rate = current_count / len(records) * 100
    previous_rate = previous_count / len(previous_records) * 100
    delta_rate = current_rate - previous_rate
    if delta_rate > 0:
        keyword_candidates.append((word, current_count, previous_count, current_rate, previous_rate, delta_rate))
emerging_keywords = sorted(keyword_candidates, key=lambda item: (-item[5], -item[1], item[0]))[:14]

cumulative_area_counts = Counter(record.get("primary_topic") or "기타 원자력" for record in cumulative_records)


def watch_matches(record, terms):
    text = paper_text(record)
    return any(term in text for term in terms)


watch_stats = []
for watch_name, watch_terms in WATCHLISTS.items():
    current_matches = [record for record in records if watch_matches(record, watch_terms)]
    previous_matches = [record for record in previous_records if watch_matches(record, watch_terms)]
    cumulative_matches = [record for record in cumulative_records if watch_matches(record, watch_terms)]
    representative = next(iter(current_matches), None)
    if representative is None and cumulative_matches:
        representative = max(cumulative_matches, key=lambda item: item.get("doi_registered_date", ""))
    watch_stats.append({
        "name": watch_name,
        "current": len(current_matches),
        "previous": len(previous_matches),
        "cumulative": len(cumulative_matches),
        "delta": len(current_matches) - len(previous_matches),
        "representative": representative,
    })


def esc(value):
    return html.escape(str(value or ""), quote=True)


cards = []
for number, record in enumerate(records, 1):
    tags_html = "".join(f'<span class="tag">{esc(tag)}</span>' for tag in record["areas"])
    author_text = ", ".join(record["authors"][:8])
    if len(record["authors"]) > 8:
        author_text += " et al."
    date_text = record.get("published_online") or record.get("issued") or record.get("cover_date") or "미확인"
    summary_html = f'<p class="summary">{esc(record["summary"])}</p>' if record["summary"] else ""
    abstract_link_label = "Abstract 확인" if record["publisher_url"] else "DOI 확인"
    watch_names = "|".join(name for name, terms in WATCHLISTS.items() if watch_matches(record, terms))
    countries = country_codes(record)
    country_text = ", ".join(country_label(code) for code in countries) if countries else "소속 국가 미확인"
    cards.append(f"""
      <article class="paper" data-journal="{esc(record['journal'])}" data-topic="{esc(record['primary_area'])}" data-title="{esc(paper_text(record))}" data-watch="{esc(watch_names)}" data-country="{esc('|'.join(countries))}" data-type="{esc(record['document_type'])}">
        <div class="paper-top"><span class="num">{number:03d}</span><span class="journal">{esc(record['journal'])}</span><span class="date">DOI 등록 {esc(record['registered_date'])}</span></div>
        <h2><a href="{esc(record['doi_url'])}" target="_blank" rel="noopener noreferrer">{esc(record['title'])}</a></h2>
        <h3 class="title-ko">{esc(record['title_ko'])}</h3>
        <p class="authors">{esc(author_text)}</p>
        <div class="tags"><span class="type-tag">{esc(record['document_type'])}</span>{tags_html}</div>
        {summary_html}
        <p class="basis">저자 소속 국가: {esc(country_text)} · {esc(record['summary_basis'])} · 온라인/권호일 {esc(date_text)} · <a class="abstract-link" href="{esc(record['publisher_url'] or record['doi_url'])}" target="_blank" rel="noopener noreferrer">{abstract_link_label}</a> · <a href="{esc(record['doi_url'])}" target="_blank" rel="noopener noreferrer">DOI</a></p>
      </article>""")

journal_rows = f'<button type="button" class="journal-filter active" data-journal="all" aria-pressed="true">전체 <strong>{len(records)}</strong></button>' + "".join(
    f'<button type="button" class="journal-filter" data-journal="{esc(name)}" aria-pressed="false"><span>{esc(name)}</span> <strong>{count}</strong></button>'
    for name, count in by_journal.items()
)
type_rows = "".join(f'<span class="type-summary"><strong>{esc(name)}</strong> {count}</span>' for name, count in type_counts.items())
max_area = max(area_counts.values())
area_order = [name for name, _ in area_counts.most_common()]
area_bars = "".join(
    f'<div class="bar-row"><span>{esc(name)}</span><div class="bar-track"><div class="bar-fill" style="width:{count/max_area*100:.1f}%"></div></div><strong>{count}</strong></div>'
    for name, count in area_counts.most_common()
)
country_max = max(country_counts.values(), default=1)
country_bars = "".join(
    f'<button type="button" class="bar-row country-trigger" data-country="{esc(code)}"><span>{esc(country_label(code))}</span><div class="bar-track"><div class="bar-fill country-fill" style="width:{count/country_max*100:.1f}%"></div></div><strong>{count}</strong></button>'
    for code, count in country_counts.most_common(15)
)

top_country_codes = [code for code, _ in country_counts.most_common(10)]
country_matrix_rows = []
for journal in by_journal:
    cells = []
    for code in top_country_codes:
        count = sum(r["journal"] == journal and code in country_codes(r) for r in records)
        cells.append(f'<td style="--cell-opacity:{0.08 + min(count/5, 0.75):.2f}"><button type="button" class="matrix-cell journal-country-trigger" data-journal="{esc(journal)}" data-country="{esc(code)}"><strong>{count}</strong></button></td>')
    country_matrix_rows.append(f'<tr><th>{esc(journal)}</th>{"".join(cells)}</tr>')
country_matrix_header = "".join(f'<th>{esc(country_label(code))}</th>' for code in top_country_codes)
country_matrix_html = f'<div class="matrix-wrap"><table class="matrix"><thead><tr><th>저널</th>{country_matrix_header}</tr></thead><tbody>{"".join(country_matrix_rows)}</tbody></table></div><p class="chart-note">저자 소속기관 기준입니다. 국제공동연구는 참여 국가마다 1편으로 집계되어 국가별 합계가 전체 논문 수보다 클 수 있습니다.</p>'
trend_rows = "".join(
    f'''<button type="button" class="trend-row topic-trigger" data-topic="{esc(area)}">
      <span class="trend-name">{esc(area)}</span>
      <span class="trend-period"><i style="width:{previous_area_counts[area]/len(previous_records)*100:.1f}%"></i><b>{previous_area_counts[area]}</b><small>{previous_area_counts[area]/len(previous_records)*100:.1f}%</small></span>
      <span class="trend-period current"><i style="width:{area_counts[area]/len(records)*100:.1f}%"></i><b>{area_counts[area]}</b><small>{area_counts[area]/len(records)*100:.1f}%</small></span>
      <span class="trend-delta {"up" if area_counts[area]/len(records)-previous_area_counts[area]/len(previous_records) > 0 else "down"}">{(area_counts[area]/len(records)-previous_area_counts[area]/len(previous_records))*100:+.1f}%p</span>
    </button>'''
    for area in area_order
)
keyword_max = max(count for _, count in top_keywords)
keyword_bars = "".join(
    f'<div class="keyword-item"><span>{esc(word)}</span><div class="keyword-track"><div class="keyword-fill" style="width:{count/keyword_max*100:.1f}%"></div></div><strong>{int(count)}</strong></div>'
    for word, count in top_keywords
)
emerging_keyword_html = "".join(
    f'''<button type="button" class="surge-keyword keyword-trigger" data-keyword="{esc(word)}">
      <span class="surge-word">{esc(word)}</span>
      <span class="surge-count">{current_count}편</span>
      <span class="surge-delta">+{delta_rate:.1f}편/100편</span>
      <span class="surge-context">직전 {previous_count} → 현재 {current_count}{" · 신규" if previous_count == 0 else ""}</span>
    </button>'''
    for word, current_count, previous_count, current_rate, previous_rate, delta_rate in emerging_keywords
)
watchlist_html = "".join(
    f'''<button type="button" class="watch-card watch-trigger" data-watch="{esc(item['name'])}">
      <span class="watch-name">{esc(item['name'])}</span>
      <span class="watch-total">누적 <strong>{item['cumulative']}</strong>편</span>
      <span class="watch-change"><b>{item['previous']}</b> → <b>{item['current']}</b><em class="{'up' if item['delta'] > 0 else 'down' if item['delta'] < 0 else 'flat'}">{item['delta']:+d}</em></span>
      <span class="watch-paper">{esc((item['representative'] or {}).get('title_ko') or (item['representative'] or {}).get('title') or (item['representative'] or {}).get('title_en') or '관련 논문 없음')}</span>
    </button>'''
    for item in watch_stats
)
start_day = date.fromisoformat(PERIOD_START)
end_day = date.fromisoformat(PERIOD_END)
all_dates = [(start_day + timedelta(days=offset)).isoformat() for offset in range((end_day-start_day).days + 1)]
max_date = max(date_counts.values())
timeline_bars = "".join(
    f'<div class="day"><div class="day-value">{date_counts[date]}</div><div class="day-track"><div class="day-fill" style="height:{(date_counts[date]/max_date*100) if max_date else 0:.1f}%"></div></div><span>{date[-2:]}</span></div>'
    for date in all_dates
)
matrix_rows = []
for journal in by_journal:
    cells = []
    for area in area_order:
        current_count = sum(r["journal"] == journal and r["primary_area"] == area for r in records)
        cumulative_count = sum(r["journal"] == journal and (r.get("primary_topic") or "기타 원자력") == area for r in cumulative_records)
        journal_total = sum(r["journal"] == journal for r in cumulative_records)
        opacity = 0.08 + (cumulative_count / max(journal_total, 1)) * 1.5
        cells.append(f'<td style="--cell-opacity:{min(opacity,0.85):.2f}"><button type="button" class="matrix-cell matrix-trigger" data-journal="{esc(journal)}" data-topic="{esc(area)}" aria-label="{esc(journal)}, {esc(area)}, 현재 {current_count}편, 누적 {cumulative_count}편"><strong>{current_count}</strong><small>{cumulative_count}</small></button></td>')
    matrix_rows.append(f'<tr><th>{esc(journal)}</th>{"".join(cells)}</tr>')
matrix_header = "".join(f'<th>{esc(area)}</th>' for area in area_order)
matrix_html = f'<div class="matrix-wrap"><table class="matrix"><thead><tr><th>저널</th>{matrix_header}</tr></thead><tbody>{"".join(matrix_rows)}</tbody></table></div><p class="chart-note">각 셀은 <strong>현재 기간</strong> / 누적 순서입니다. 셀을 누르면 해당 조합의 최신 논문만 표시합니다.</p>'

area_colors = {
    "열수력·유체": "#0b6bcb", "원자로물리·해석": "#7048e8", "안전·사고·리스크": "#d9480f",
    "핵연료·재료": "#087f5b", "AI·디지털": "#c2255c", "방사선·계측": "#e67700",
    "핵연료주기·폐기물": "#5f3dc4", "설계·운전·경제": "#2b8a3e", "기타 원자력": "#7b8794",
}
x_values = [record["topic_x"] for record in records]
y_values = [record["topic_y"] for record in records]
x_min, x_max = min(x_values), max(x_values)
y_min, y_max = min(y_values), max(y_values)

def map_value(value, low, high, out_low, out_high):
    return out_low + (value - low) / max(high - low, 1e-9) * (out_high - out_low)

scatter_points = []
for index, record in enumerate(records, 1):
    cx = map_value(record["topic_x"], x_min, x_max, 62, 798)
    cy = map_value(record["topic_y"], y_min, y_max, 448, 28)
    color = area_colors[record["primary_area"]]
    tooltip = f"{index:03d} · {record['title_ko']} · {record['primary_area']}"
    point_watches = "|".join(name for name, terms in WATCHLISTS.items() if watch_matches(record, terms))
    scatter_points.append(
        f'<a href="{esc(record["doi_url"])}" target="_blank" rel="noopener noreferrer"><circle data-journal="{esc(record["journal"])}" data-topic="{esc(record["primary_area"])}" data-title="{esc(paper_text(record))}" data-watch="{esc(point_watches)}" data-country="{esc("|".join(country_codes(record)))}" cx="{cx:.1f}" cy="{cy:.1f}" r="5.2" fill="{color}" fill-opacity="0.76" stroke="#ffffff" stroke-width="1"><title>{esc(tooltip)}</title></circle></a>'
    )
cluster_labels = []
for cluster_id, cluster_name in cluster_names.items():
    members = [record for record in records if record["cluster"] == cluster_id]
    label_x = sum(map_value(record["topic_x"], x_min, x_max, 62, 798) for record in members) / len(members)
    label_y = sum(map_value(record["topic_y"], y_min, y_max, 448, 28) for record in members) / len(members)
    cluster_labels.append(f'<text class="cluster-label" x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle">{esc(cluster_name)}</text>')
scatter_legend = "".join(
    f'<span><i style="background:{area_colors[area]}"></i>{esc(area)} {area_counts[area]}</span>'
    for area in area_order
)
scatter_html = f'''<div class="scatter-legend">{scatter_legend}</div>
<svg class="topic-scatter" viewBox="0 0 840 500" role="img" aria-labelledby="topic-map-title topic-map-desc">
  <title id="topic-map-title">제목 기반 연구 토픽 산점도</title>
  <desc id="topic-map-desc">영문 제목의 TF-IDF 유사도를 SVD로 2차원에 투영한 지도입니다. 가까운 점일수록 제목에서 사용하는 연구 용어가 유사합니다.</desc>
  <rect x="54" y="18" width="754" height="440" fill="#f8fafc" stroke="#d9e2ec"/>
  <line x1="54" y1="458" x2="808" y2="458" stroke="#9fb3c8"/><line x1="54" y1="18" x2="54" y2="458" stroke="#9fb3c8"/>
  <text x="431" y="490" text-anchor="middle">토픽 성분 1</text><text x="16" y="238" text-anchor="middle" transform="rotate(-90 16 238)">토픽 성분 2</text>
  {''.join(scatter_points)}
  {''.join(cluster_labels)}
</svg>
<p class="chart-note">점 하나는 논문 한 편입니다. 가까울수록 제목에 등장하는 용어가 유사하며, 점을 가리키면 한글 제목을 확인하고 클릭하면 DOI로 이동합니다.</p>'''

document = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>원자력공학 최근 논문 다이제스트 · {RUN_DATE}</title>
  <style>
    :root {{ --navy:#102a43; --blue:#0b6bcb; --sky:#eaf4ff; --line:#d9e2ec; --ink:#243b53; --muted:#627d98; --high:#087f5b; --mid:#b35c00; }}
    * {{ box-sizing:border-box }} body {{ margin:0;background:#f5f8fb;color:var(--ink);font-family:Arial,'Noto Sans KR',sans-serif;line-height:1.55 }}
    .wrap {{ max-width:920px;margin:auto;padding:32px 18px 80px }}
    header {{ background:linear-gradient(135deg,#102a43,#1668a9);color:white;border-radius:18px;padding:34px;box-shadow:0 12px 34px #102a4326 }}
    header h1 {{ margin:0 0 10px;font-size:30px;line-height:1.25 }} header p {{ margin:5px 0;color:#d9edff }}
    .notice {{ margin:18px 0;padding:16px 18px;border-left:5px solid #d9480f;background:#fff4e6;border-radius:8px;color:#7c2d12 }}
    .metrics {{ display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0 }}
    .metric {{ background:white;border:1px solid var(--line);border-radius:12px;padding:16px;text-align:center }} .metric strong {{ display:block;font-size:25px;color:var(--navy) }}
    .panel {{ background:white;border:1px solid var(--line);border-radius:12px;padding:18px;margin:15px 0 }} .panel h2 {{ margin:0 0 10px;font-size:18px }}
    .journal-filters {{ display:flex;flex-wrap:wrap;gap:8px }} .journal-filter {{ border:1px solid var(--line);background:#f8fafc;color:var(--ink);border-radius:999px;padding:8px 12px;cursor:pointer;font:inherit;font-size:13px }} .journal-filter:hover {{ border-color:var(--blue) }} .journal-filter.active {{ background:var(--blue);border-color:var(--blue);color:white }} .journal-filter strong {{ margin-left:4px }}
    .tag,.type-tag,.type-summary {{ display:inline-block;margin:3px;padding:3px 8px;border-radius:999px;background:var(--sky);color:#075985;font-size:12px }} .type-tag,.type-summary {{ background:#edf2f7;color:#52677b }}
    .bar-row {{ width:100%;display:grid;grid-template-columns:150px 1fr 32px;gap:10px;align-items:center;margin:9px 0;padding:0;border:0;background:transparent;color:inherit;font:inherit;text-align:left }} .bar-track {{ height:14px;background:#edf2f7;border-radius:4px;overflow:hidden }} .bar-fill {{ height:100%;background:#0b6bcb }} .country-fill {{ background:#087f5b }} button.bar-row {{ cursor:pointer }} button.bar-row:hover {{ background:#f8fbff }}
    .trend-head {{ display:grid;grid-template-columns:150px 1fr 1fr 58px;gap:10px;color:var(--muted);font-size:11px;padding:0 8px 6px }} .trend-grid {{ display:grid;gap:2px }} .trend-row {{ width:100%;display:grid;grid-template-columns:150px 1fr 1fr 58px;gap:10px;align-items:center;padding:8px;border:0;border-bottom:1px solid #edf2f7;background:transparent;color:var(--ink);font:inherit;text-align:left;cursor:pointer }} .trend-row:hover {{ background:#f8fbff }} .trend-period {{ position:relative;display:grid;grid-template-columns:1fr 30px 40px;gap:5px;align-items:center;font-size:11px }} .trend-period::before {{ content:"";position:absolute;left:0;right:75px;height:9px;background:#edf2f7 }} .trend-period i {{ height:9px;background:#9fb3c8;z-index:1 }} .trend-period.current i {{ background:var(--blue) }} .trend-period b,.trend-period small {{ z-index:1;text-align:right }} .trend-delta {{ text-align:right;font-weight:700;font-size:12px }} .trend-delta.up {{ color:#087f5b }} .trend-delta.down {{ color:#c92a2a }}
    .keyword-grid {{ display:grid;grid-template-columns:1fr 1fr;gap:0 20px }} .keyword-item {{ display:grid;grid-template-columns:115px 1fr 25px;gap:8px;align-items:center;padding:5px 0;font-size:12px }} .keyword-track {{ height:9px;background:#edf2f7 }} .keyword-fill {{ height:100%;background:#7048e8 }}
    .surge-grid {{ display:grid;grid-template-columns:repeat(2,1fr);gap:7px 16px }} .surge-keyword {{ display:grid;grid-template-columns:1fr auto auto;gap:8px;width:100%;padding:9px 7px;border:0;border-bottom:1px solid #edf2f7;background:transparent;color:var(--ink);font:inherit;text-align:left;cursor:pointer }} .surge-keyword:hover {{ background:#f8fbff }} .surge-word {{ font-weight:700 }} .surge-count {{ color:var(--navy);font-size:12px }} .surge-delta {{ color:#087f5b;font-size:12px;font-weight:700 }} .surge-context {{ grid-column:1/-1;color:var(--muted);font-size:11px }}
    .watch-grid {{ display:grid;grid-template-columns:repeat(2,1fr);gap:10px }} .watch-card {{ display:grid;grid-template-columns:1fr auto;gap:5px 10px;padding:13px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--ink);font:inherit;text-align:left;cursor:pointer }} .watch-card:hover {{ border-color:var(--blue);background:#f8fbff }} .watch-name {{ font-weight:700;color:var(--navy) }} .watch-total {{ font-size:12px;color:var(--muted) }} .watch-change {{ font-size:12px }} .watch-change em {{ margin-left:8px;font-style:normal;font-weight:700 }} .watch-change em.up {{ color:#087f5b }} .watch-change em.down {{ color:#c92a2a }} .watch-change em.flat {{ color:var(--muted) }} .watch-paper {{ grid-column:1/-1;color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis }}
    .timeline {{ display:flex;gap:8px;height:170px;align-items:flex-end }} .day {{ flex:1;min-width:20px;text-align:center;font-size:11px;color:var(--muted) }} .day-track {{ height:120px;background:#edf2f7;display:flex;align-items:flex-end;margin:3px 0 }} .day-fill {{ width:100%;background:#087f5b }} .day-value {{ color:var(--ink);font-weight:700 }}
    .matrix-wrap {{ overflow-x:auto }} .matrix {{ border-collapse:collapse;width:100%;font-size:11px }} .matrix th,.matrix td {{ padding:0;border:1px solid var(--line);text-align:center }} .matrix thead th {{ padding:7px;writing-mode:vertical-rl;min-width:42px;height:125px }} .matrix tbody th {{ padding:7px;text-align:left;min-width:180px }} .matrix td {{ background:rgba(11,107,203,var(--cell-opacity)) }} .matrix-cell {{ width:100%;min-height:42px;border:0;background:transparent;color:var(--navy);cursor:pointer;font:inherit }} .matrix-cell:hover {{ outline:2px solid var(--navy);outline-offset:-2px }} .matrix-cell strong,.matrix-cell small {{ display:block }} .matrix-cell small {{ opacity:.7 }}
    .topic-scatter {{ display:block;width:100%;height:auto }} .topic-scatter text {{ fill:var(--muted);font-size:12px }} .topic-scatter circle {{ cursor:pointer;transition:opacity .18s,r .18s }} .topic-scatter circle:hover {{ r:8;fill-opacity:1 }} .topic-scatter .cluster-label {{ fill:var(--navy);font-size:11px;font-weight:700;paint-order:stroke;stroke:#ffffff;stroke-width:4px;stroke-linejoin:round;pointer-events:none }}
    .paper[hidden] {{ display:none }} .topic-scatter circle.is-dimmed {{ opacity:.10 }} .topic-scatter circle.is-selected {{ opacity:1;stroke:#102a43;stroke-width:1.7 }}
    .filter-status {{ display:flex;align-items:center;justify-content:space-between;gap:12px;margin:16px 0;padding:12px 14px;background:#eaf4ff;border-left:4px solid var(--blue);border-radius:7px }} .filter-status button {{ border:1px solid var(--line);background:white;border-radius:7px;padding:6px 10px;cursor:pointer }} .filter-status[hidden] {{ display:none }}
    .scatter-legend {{ display:flex;flex-wrap:wrap;gap:8px 14px;margin-bottom:8px;font-size:12px }} .scatter-legend span {{ display:inline-flex;align-items:center;gap:5px }} .scatter-legend i {{ width:10px;height:10px;border-radius:50%;display:inline-block }} .chart-note {{ color:var(--muted);font-size:12px;margin:6px 0 0 }}
    .paper {{ background:white;border:1px solid var(--line);border-left:5px solid #0b6bcb;border-radius:12px;padding:19px;margin:14px 0 }}
    .paper-top {{ display:flex;gap:9px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--muted) }} .num {{ font-weight:700;color:var(--blue) }} .journal {{ background:#edf2f7;padding:2px 7px;border-radius:5px }} .date {{ margin-left:auto }}
    .paper h2 {{ font-size:18px;line-height:1.4;margin:10px 0 4px }} .title-ko {{ margin:0 0 8px;font-size:16px;font-weight:500;color:var(--navy);line-height:1.45 }} a {{ color:#075985;text-decoration:none }} a:hover {{ text-decoration:underline }}
    .authors,.basis {{ color:var(--muted);font-size:12px }} .summary {{ margin:12px 0 8px }}
    footer {{ margin-top:32px;color:var(--muted);font-size:12px;text-align:center }}
    @media(max-width:650px) {{ .metrics {{ grid-template-columns:1fr }} header {{ padding:24px }} .date {{ margin-left:0 }} .bar-row {{ grid-template-columns:115px 1fr 28px }} .timeline {{ gap:3px }} .journal-filter {{ width:100%;text-align:left }} .keyword-grid,.surge-grid,.watch-grid {{ grid-template-columns:1fr }} .trend-head {{ display:none }} .trend-row {{ grid-template-columns:1fr }} .trend-period {{ grid-template-columns:1fr 30px 40px }} .trend-delta {{ text-align:left }} }}
    @media print {{ body {{ background:white }} .wrap {{ max-width:none;padding:0 }} header,.paper,.panel,.metric {{ box-shadow:none;break-inside:avoid }} }}
  </style>
</head>
<body><div class="wrap">
  <header>
    <h1>원자력공학 최근 논문 다이제스트</h1>
    <p>대상 기간: {PERIOD_START} ~ {PERIOD_END} · DOI 신규 등록 기준</p>
    <p>5개 원자력공학 종합 저널 · 연구 영역 및 출판 동향</p>
  </header>
  <div class="notice"><strong>수록 기준:</strong> 데이터베이스에는 최근 2회 수집분 {len(cumulative_records)}편이 DOI 기준으로 중복 없이 저장되어 있습니다. 아래 동향 지표는 누적 자료를 사용하며, 논문 목록은 최신 기간 {len(records)}편을 보여줍니다.</div>
  <section class="metrics"><div class="metric"><strong>{len(cumulative_records)}</strong>누적 논문</div><div class="metric"><strong id="visible-count">{len(records)}</strong>최신 기간 표시 논문</div><div class="metric"><strong>{len(database['runs'])}</strong>누적 수집 기간</div></section>
  <section class="panel"><h2>저널 필터</h2><div class="journal-filters" aria-label="저널별 논문 필터">{journal_rows}</div></section>
  <div id="filter-status" class="filter-status" aria-live="polite" hidden><span id="filter-label"></span><button type="button" id="reset-filter">필터 초기화</button></div>
  <section class="panel"><h2>문서 유형</h2><div>{type_rows}</div></section>
  <section class="panel"><h2>연구 영역 분포</h2>{area_bars}</section>
  <section class="panel"><h2>국가별 논문 분포</h2>{country_bars}<p class="chart-note">이번 주 {len(records)}편 중 소속 국가를 확인한 논문은 {country_coverage}편입니다. 막대를 누르면 해당 국가의 논문만 표시합니다.</p></section>
  <section class="panel"><h2>저널 × 국가 히트맵</h2>{country_matrix_html}</section>
  <section class="panel"><h2>제목 기반 연구 토픽 지도</h2>{scatter_html}</section>
  <section class="panel"><h2>주간 연구 토픽 추세</h2><div class="trend-head"><span>토픽</span><span>{PREVIOUS_START[5:]}–{PREVIOUS_END[5:]} · {len(previous_records)}편</span><span>{PERIOD_START[5:]}–{PERIOD_END[5:]} · {len(records)}편</span><span>비중 변화</span></div><div class="trend-grid">{trend_rows}</div><p class="chart-note">주별 전체 논문 수가 다르므로 건수와 함께 점유율 변화를 표시합니다. 행을 누르면 최신 논문을 필터링합니다.</p></section>
  <section class="panel"><h2>급상승 연구 키워드</h2><div class="surge-grid">{emerging_keyword_html}</div><p class="chart-note">제목·공개 초록에서 기간별 100편당 출현 빈도가 증가한 단어와 구문입니다. 키워드를 누르면 최신 관련 논문만 표시합니다.</p></section>
  <section class="panel"><h2>연구실 관심 분야 추적기</h2><div class="watch-grid">{watchlist_html}</div><p class="chart-note">누적 건수와 직전 주→현재 주 변화를 함께 표시합니다. 항목을 누르면 관련 최신 논문으로 이동합니다.</p></section>
  <section class="panel"><h2>상위 연구 키워드</h2><div class="keyword-grid">{keyword_bars}</div></section>
  <section class="panel"><h2>최근 1주 DOI 등록 추이</h2><div class="timeline" role="img" aria-label="{PERIOD_START}부터 {PERIOD_END}까지 일별 DOI 등록 논문 수">{timeline_bars}</div></section>
  <section class="panel"><h2>저널 × 연구 토픽 히트맵</h2>{matrix_html}</section>
  <main id="papers">{''.join(cards)}</main>
  <footer>수집 기준: Crossref DOI created date. 권호일·온라인 공개일과 다를 수 있으므로 각 카드에 별도 표기했습니다.</footer>
</div>
<script>
(() => {{
  const buttons = [...document.querySelectorAll('.journal-filter')];
  const papers = [...document.querySelectorAll('.paper')];
  const points = [...document.querySelectorAll('.topic-scatter circle[data-journal]')];
  const visibleCount = document.getElementById('visible-count');
  const status = document.getElementById('filter-status');
  const statusLabel = document.getElementById('filter-label');
  const state = {{ journal: 'all', topic: '', keyword: '', watch: '', country: '' }};
  function matches(item) {{
    return (state.journal === 'all' || item.dataset.journal === state.journal)
      && (!state.topic || item.dataset.topic === state.topic)
      && (!state.keyword || (item.dataset.title || '').includes(state.keyword))
      && (!state.watch || (item.dataset.watch || '').split('|').includes(state.watch))
      && (!state.country || (item.dataset.country || '').split('|').includes(state.country));
  }}
  function applyFilters(scrollToPapers = false) {{
    let count = 0;
    papers.forEach(paper => {{
      const show = matches(paper);
      paper.hidden = !show;
      if (show) count += 1;
    }});
    points.forEach(point => {{
      const selected = matches(point);
      const filtering = state.journal !== 'all' || state.topic || state.keyword || state.watch || state.country;
      point.classList.toggle('is-dimmed', filtering && !selected);
      point.classList.toggle('is-selected', filtering && selected);
    }});
    buttons.forEach(button => {{
      const selected = button.dataset.journal === state.journal;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    }});
    visibleCount.textContent = count;
    const labels = [];
    if (state.journal !== 'all') labels.push(state.journal);
    if (state.topic) labels.push(state.topic);
    if (state.keyword) labels.push(`키워드: ${{state.keyword}}`);
    if (state.watch) labels.push(`관심 분야: ${{state.watch}}`);
    if (state.country) labels.push(`국가: ${{state.country}}`);
    status.hidden = labels.length === 0;
    statusLabel.textContent = labels.length ? `${{labels.join(' · ')}} — ${{count}}편 표시` : '';
    if (scrollToPapers) document.getElementById('papers').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}
  function resetSecondaryFilters() {{ state.topic = ''; state.keyword = ''; state.watch = ''; state.country = ''; }}
  buttons.forEach(button => button.addEventListener('click', () => {{ state.journal = button.dataset.journal; applyFilters(); }}));
  document.querySelectorAll('.topic-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.topic = button.dataset.topic; applyFilters(true); }}));
  document.querySelectorAll('.keyword-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.keyword = button.dataset.keyword.toLowerCase(); applyFilters(true); }}));
  document.querySelectorAll('.watch-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.watch = button.dataset.watch; applyFilters(true); }}));
  document.querySelectorAll('.country-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.country = button.dataset.country; applyFilters(true); }}));
  document.querySelectorAll('.journal-country-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.journal = button.dataset.journal; state.country = button.dataset.country; applyFilters(true); }}));
  document.querySelectorAll('.matrix-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.journal = button.dataset.journal; state.topic = button.dataset.topic; applyFilters(true); }}));
  document.getElementById('reset-filter').addEventListener('click', () => {{ state.journal = 'all'; resetSecondaryFilters(); applyFilters(); }});
}})();
</script>
</body></html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(document, encoding="utf-8")
print(json.dumps({"output": str(OUTPUT), "records": len(records), "areas": area_counts}, ensure_ascii=False, default=dict))
