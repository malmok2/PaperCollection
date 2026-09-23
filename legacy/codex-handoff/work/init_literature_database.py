import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(r"C:\Users\Idaho_S\Documents\Codex\nuclear-literature-db")
RUN_DATE = "2026-08-30"

TOPIC_RULES = {
    "열수력·유체": ["flow", "thermal", "heat", "boiling", "condensation", "coolant", "hydraulic", "fluid", "turbulence", "pressure drop", "void fraction", "pump"],
    "원자로물리·해석": ["neutron", "reactor physics", "core analysis", "criticality", "monte carlo", "geant4", "cross section", "burnup", "kinetics"],
    "안전·사고·리스크": ["safety", "accident", "risk", "loca", "tsunami", "reliability", "severe", "emergency", "hazard"],
    "핵연료·재료": ["fuel", "cladding", "material", "irradiation", "steel", "zircon", "alloy", "corrosion", "defect", "composite"],
    "AI·디지털": ["machine learning", "deep learning", "neural", "artificial intelligence", "ai-driven", "reinforcement learning", "physics-informed", "digital twin", "surrogate", "reduced-order", "reduced order", "cnn", "lstm"],
    "방사선·계측": ["radiation", "detector", "dosim", "shield", "source localization", "spectr", "instrument", "measurement", "magnet"],
    "핵연료주기·폐기물": ["waste", "spent fuel", "fuel cycle", "pyroprocessing", "decommission", "disposal", "incineration", "storage"],
    "설계·운전·경제": ["design", "operation", "maintenance", "economic", "cost", "control room", "optimization", "management", "policy", "sociotechnical"],
}
JOURNALS = {
    "Nuclear Engineering and Design": "0029-5493",
    "Annals of Nuclear Energy": "0306-4549",
    "Nuclear Engineering and Technology": "1738-5733",
    "Progress in Nuclear Energy": "0149-1970",
    "Nuclear Technology": "0029-5450",
}


def areas_for(title):
    lower = title.lower()
    matches = [area for area, terms in TOPIC_RULES.items() if any(term in lower for term in terms)]
    return matches or ["기타 원자력"]


def document_type(title):
    lower = title.lower().strip()
    if "corrigendum" in lower:
        return "정오표"
    if lower == "editorial board" or lower.startswith("introduction:"):
        return "편집물"
    if any(term in lower for term in ["review", "recent progress", "perspective", "retrospective"]):
        return "리뷰·관점"
    return "연구논문"


for name in ["data", "backups", "exports", "reports", "config", "raw", "logs"]:
    (PROJECT_ROOT / name).mkdir(parents=True, exist_ok=True)

current = json.loads((SOURCE_ROOT / "articles.json").read_text(encoding="utf-8"))
previous = json.loads((SOURCE_ROOT / "articles_previous.json").read_text(encoding="utf-8"))
translations = (SOURCE_ROOT / "title_translations_ko.txt").read_text(encoding="utf-8").splitlines()
translations_by_doi = {record["doi"]: title for record, title in zip(current, translations)}

db_path = PROJECT_ROOT / "data" / "working.sqlite"
connection = sqlite3.connect(db_path)
connection.execute("PRAGMA foreign_keys=ON")
connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS papers (
      doi TEXT PRIMARY KEY,
      title_en TEXT NOT NULL,
      title_ko TEXT,
      journal TEXT NOT NULL,
      issn TEXT,
      authors TEXT,
      doi_registered_date TEXT,
      published_online TEXT,
      issue_date TEXT,
      document_type TEXT NOT NULL,
      primary_topic TEXT NOT NULL,
      abstract TEXT,
      abstract_url TEXT,
      doi_url TEXT NOT NULL,
      open_access INTEGER NOT NULL DEFAULT 0,
      first_seen TEXT NOT NULL,
      last_checked TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      source TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS collection_runs (
      run_id TEXT PRIMARY KEY,
      period_start TEXT NOT NULL,
      period_end TEXT NOT NULL,
      executed_at TEXT NOT NULL,
      found_count INTEGER NOT NULL,
      new_count INTEGER NOT NULL,
      updated_count INTEGER NOT NULL,
      error_count INTEGER NOT NULL,
      source_note TEXT
    );
    CREATE TABLE IF NOT EXISTS paper_runs (
      doi TEXT NOT NULL REFERENCES papers(doi),
      run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
      PRIMARY KEY (doi, run_id)
    );
    CREATE TABLE IF NOT EXISTS topics (
      topic_id INTEGER PRIMARY KEY,
      topic_ko TEXT UNIQUE NOT NULL,
      keywords TEXT NOT NULL,
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS paper_topics (
      doi TEXT NOT NULL REFERENCES papers(doi),
      topic_ko TEXT NOT NULL REFERENCES topics(topic_ko),
      is_primary INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (doi, topic_ko)
    );
    CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal);
    CREATE INDEX IF NOT EXISTS idx_papers_registered ON papers(doi_registered_date);
    CREATE INDEX IF NOT EXISTS idx_papers_topic ON papers(primary_topic);
    """
)

with connection:
    for index, (topic, keywords) in enumerate(list(TOPIC_RULES.items()) + [("기타 원자력", [])], 1):
        connection.execute(
            "INSERT INTO topics(topic_id, topic_ko, keywords, active) VALUES(?,?,?,1) ON CONFLICT(topic_ko) DO UPDATE SET keywords=excluded.keywords, active=1",
            (index, topic, "; ".join(keywords)),
        )

    periods = [
        ("2026-08-16", "2026-08-03", "2026-08-16", previous),
        ("2026-08-30", "2026-08-17", "2026-08-30", current),
    ]
    for run_id, start, end, records in periods:
        connection.execute(
            """INSERT INTO collection_runs(run_id,period_start,period_end,executed_at,found_count,new_count,updated_count,error_count,source_note)
               VALUES(?,?,?,?,0,0,0,0,?)
               ON CONFLICT(run_id) DO UPDATE SET period_start=excluded.period_start,period_end=excluded.period_end,executed_at=excluded.executed_at""",
            (run_id, start, end, datetime.now().isoformat(timespec="seconds"), "Crossref DOI created date; five target journals"),
        )
        before = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        for record in records:
            doi = record["doi"]
            areas = areas_for(record["title"])
            authors = "; ".join(record.get("authors", [])) if isinstance(record.get("authors"), list) else record.get("authors", "")
            issn = record.get("issn") or JOURNALS.get(record["journal"], "")
            abstract_url = record.get("publisher_url") or record.get("doi_url") or f"https://doi.org/{doi}"
            connection.execute(
                """
                INSERT INTO papers(doi,title_en,title_ko,journal,issn,authors,doi_registered_date,published_online,issue_date,document_type,primary_topic,abstract,abstract_url,doi_url,open_access,first_seen,last_checked,status,source)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(doi) DO UPDATE SET
                  title_en=excluded.title_en, title_ko=COALESCE(excluded.title_ko,papers.title_ko), journal=excluded.journal,
                  issn=excluded.issn, authors=CASE WHEN excluded.authors<>'' THEN excluded.authors ELSE papers.authors END,
                  doi_registered_date=excluded.doi_registered_date, published_online=COALESCE(NULLIF(excluded.published_online,''),papers.published_online),
                  issue_date=COALESCE(NULLIF(excluded.issue_date,''),papers.issue_date), document_type=excluded.document_type,
                  primary_topic=excluded.primary_topic, abstract=COALESCE(NULLIF(excluded.abstract,''),papers.abstract),
                  abstract_url=excluded.abstract_url, doi_url=excluded.doi_url, open_access=excluded.open_access,
                  last_checked=excluded.last_checked, status='active', source=excluded.source
                """,
                (
                    doi, record["title"], translations_by_doi.get(doi), record["journal"], issn, authors,
                    record.get("registered_date", ""), record.get("published_online", ""), record.get("issued", ""),
                    document_type(record["title"]), areas[0], record.get("abstract", ""), abstract_url,
                    record.get("doi_url") or f"https://doi.org/{doi}", int(bool(record.get("open_access"))),
                    end, RUN_DATE, "active", "Crossref + publisher metadata",
                ),
            )
            connection.execute("DELETE FROM paper_topics WHERE doi=?", (doi,))
            for area_index, area in enumerate(areas):
                connection.execute("INSERT INTO paper_topics(doi,topic_ko,is_primary) VALUES(?,?,?)", (doi, area, int(area_index == 0)))
            connection.execute("INSERT OR IGNORE INTO paper_runs(doi,run_id) VALUES(?,?)", (doi, run_id))
        after = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        connection.execute(
            "UPDATE collection_runs SET found_count=?,new_count=?,updated_count=?,error_count=0,source_note=? WHERE run_id=?",
            (len(records), after - before, len(records) - (after - before), "Crossref DOI created date; five target journals", run_id),
        )

integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
counts = {
    "papers": connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0],
    "runs": connection.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0],
    "paper_topics": connection.execute("SELECT COUNT(*) FROM paper_topics").fetchone()[0],
}
connection.commit()
connection.close()
if integrity != "ok":
    raise RuntimeError(f"SQLite integrity check failed: {integrity}")

shutil.copy2(db_path, PROJECT_ROOT / "backups" / f"{RUN_DATE}.sqlite")
shutil.copy2(db_path, PROJECT_ROOT / "backups" / "latest.sqlite")
shutil.copy2(SOURCE_ROOT / "articles.json", PROJECT_ROOT / "raw" / f"{RUN_DATE}-crossref.json")
shutil.copy2(SOURCE_ROOT / "articles_previous.json", PROJECT_ROOT / "raw" / "2026-08-16-crossref.json")
report_source = SOURCE_ROOT.parent / "outputs" / "nuclear-literature-digest-2026-08-30.html"
shutil.copy2(report_source, PROJECT_ROOT / "reports" / f"{RUN_DATE}-digest.html")
(PROJECT_ROOT / "config" / "journals.json").write_text(json.dumps(JOURNALS, ensure_ascii=False, indent=2), encoding="utf-8")
(PROJECT_ROOT / "config" / "topics.json").write_text(json.dumps(TOPIC_RULES, ensure_ascii=False, indent=2), encoding="utf-8")
(PROJECT_ROOT / "logs" / "collection-history.log").write_text(
    f"{datetime.now().isoformat(timespec='seconds')} initialized papers={counts['papers']} runs={counts['runs']} integrity={integrity}\n",
    encoding="utf-8",
)

# Export a compact JSON payload for the workbook builder.
connection = sqlite3.connect(db_path)
connection.row_factory = sqlite3.Row
payload = {
    "papers": [dict(row) for row in connection.execute("SELECT * FROM papers ORDER BY doi_registered_date DESC, journal, title_en")],
    "runs": [dict(row) for row in connection.execute("SELECT * FROM collection_runs ORDER BY period_end DESC")],
    "topics": [dict(row) for row in connection.execute("SELECT * FROM topics ORDER BY topic_id")],
    "paper_topics": [dict(row) for row in connection.execute("SELECT * FROM paper_topics ORDER BY doi, is_primary DESC, topic_ko")],
    "journal_summary": [dict(row) for row in connection.execute("SELECT journal, COUNT(*) AS paper_count FROM papers GROUP BY journal ORDER BY paper_count DESC")],
    "topic_summary": [dict(row) for row in connection.execute("SELECT primary_topic, COUNT(*) AS paper_count FROM papers GROUP BY primary_topic ORDER BY paper_count DESC")],
    "type_summary": [dict(row) for row in connection.execute("SELECT document_type, COUNT(*) AS paper_count FROM papers GROUP BY document_type ORDER BY paper_count DESC")],
}
connection.close()
(SOURCE_ROOT / "db_export.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"root": str(PROJECT_ROOT), "integrity": integrity, **counts}, ensure_ascii=False))
