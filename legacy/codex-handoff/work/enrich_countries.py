import json
import shutil
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent
PROJECT = Path(r"C:\Users\Idaho_S\Documents\Codex\nuclear-literature-db")
DB = PROJECT / "data" / "working.sqlite"
HEADERS = {"User-Agent": "NuclearLiteratureDigest/2.1 (mailto:hysms@hanyang.ac.kr)"}


def fetch_country_data(doi):
    url = "https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="/()")
    for attempt in range(4):
        response = requests.get(url, params={"select": "doi,authorships"}, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            authorships = response.json().get("authorships", [])
            all_codes, corresponding = [], []
            for authorship in authorships:
                codes = authorship.get("countries", []) or [
                    institution.get("country_code") for institution in authorship.get("institutions", [])
                    if institution.get("country_code")
                ]
                for code in codes:
                    code = (code or "").upper()
                    if code and code not in all_codes:
                        all_codes.append(code)
                    if authorship.get("is_corresponding") and code and code not in corresponding:
                        corresponding.append(code)
            primary = (corresponding or all_codes or [""])[0]
            return doi, all_codes, primary, "OpenAlex authorship institutions"
        if response.status_code == 404:
            return doi, [], "", "OpenAlex: work not found"
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(1.5 * (attempt + 1))
            continue
        response.raise_for_status()
    return doi, [], "", "OpenAlex: temporary failure"


def export_payload(connection):
    connection.row_factory = sqlite3.Row
    return {
        "papers": [dict(row) for row in connection.execute("SELECT * FROM papers ORDER BY doi_registered_date DESC,journal,title_en")],
        "runs": [dict(row) for row in connection.execute("SELECT * FROM collection_runs ORDER BY period_end DESC")],
        "topics": [dict(row) for row in connection.execute("SELECT * FROM topics ORDER BY topic_id")],
        "paper_topics": [dict(row) for row in connection.execute("SELECT * FROM paper_topics ORDER BY doi,is_primary DESC,topic_ko")],
        "journal_summary": [dict(row) for row in connection.execute("SELECT journal,COUNT(*) paper_count FROM papers GROUP BY journal ORDER BY paper_count DESC")],
        "topic_summary": [dict(row) for row in connection.execute("SELECT primary_topic,COUNT(*) paper_count FROM papers GROUP BY primary_topic ORDER BY paper_count DESC")],
        "type_summary": [dict(row) for row in connection.execute("SELECT document_type,COUNT(*) paper_count FROM papers GROUP BY document_type ORDER BY paper_count DESC")],
    }


connection = sqlite3.connect(DB)
columns = {row[1] for row in connection.execute("PRAGMA table_info(papers)")}
with connection:
    if "countries" not in columns:
        connection.execute("ALTER TABLE papers ADD COLUMN countries TEXT NOT NULL DEFAULT ''")
    if "primary_country" not in columns:
        connection.execute("ALTER TABLE papers ADD COLUMN primary_country TEXT NOT NULL DEFAULT ''")
    if "country_source" not in columns:
        connection.execute("ALTER TABLE papers ADD COLUMN country_source TEXT NOT NULL DEFAULT ''")

dois = [row[0] for row in connection.execute("SELECT doi FROM papers WHERE countries='' ORDER BY doi")]
results = []
with ThreadPoolExecutor(max_workers=6) as pool:
    futures = [pool.submit(fetch_country_data, doi) for doi in dois]
    for future in as_completed(futures):
        results.append(future.result())

with connection:
    for doi, countries, primary, source in results:
        connection.execute(
            "UPDATE papers SET countries=?,primary_country=?,country_source=? WHERE doi=?",
            (";".join(countries), primary, source, doi),
        )

payload = export_payload(connection)
integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
coverage = connection.execute("SELECT COUNT(*),SUM(CASE WHEN countries<>'' THEN 1 ELSE 0 END) FROM papers").fetchone()
connection.close()
if integrity != "ok" or foreign:
    raise RuntimeError(f"database validation failed: {integrity}, foreign={len(foreign)}")

(ROOT / "db_export.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
by_doi = {paper["doi"].lower(): paper for paper in payload["papers"]}
for filename in ["articles.json", "articles_previous.json"]:
    path = ROOT / filename
    records = json.loads(path.read_text(encoding="utf-8"))
    for record in records:
        paper = by_doi.get(record.get("doi", "").lower(), {})
        record["countries"] = [value for value in (paper.get("countries") or "").split(";") if value]
        record["primary_country"] = paper.get("primary_country") or ""
        record["country_source"] = paper.get("country_source") or ""
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

shutil.copy2(DB, PROJECT / "backups" / "latest.sqlite")
print(json.dumps({"queried": len(dois), "papers": coverage[0], "with_country": coverage[1], "coverage_percent": round((coverage[1] or 0) / coverage[0] * 100, 1), "integrity": integrity}, ensure_ascii=False))
