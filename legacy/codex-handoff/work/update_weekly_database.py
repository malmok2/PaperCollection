import argparse
import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = Path(r"C:\Users\Idaho_S\Documents\Codex\nuclear-literature-db")
TOPICS = {
    "열수력·유체": ["flow", "thermal", "heat", "boiling", "condensation", "coolant", "hydraulic", "fluid", "turbulence", "pressure drop", "void fraction", "pump"],
    "원자로물리·해석": ["neutron", "reactor physics", "core analysis", "criticality", "monte carlo", "geant4", "cross section", "burnup", "kinetics"],
    "안전·사고·리스크": ["safety", "accident", "risk", "loca", "tsunami", "reliability", "severe", "emergency", "hazard"],
    "핵연료·재료": ["fuel", "cladding", "material", "irradiation", "steel", "zircon", "alloy", "corrosion", "defect", "composite"],
    "AI·디지털": ["machine learning", "deep learning", "neural", "artificial intelligence", "ai-driven", "reinforcement learning", "physics-informed", "digital twin", "surrogate", "reduced-order", "reduced order", "cnn", "lstm"],
    "방사선·계측": ["radiation", "detector", "dosim", "shield", "source localization", "spectr", "instrument", "measurement", "magnet"],
    "핵연료주기·폐기물": ["waste", "spent fuel", "fuel cycle", "pyroprocessing", "decommission", "disposal", "incineration", "storage"],
    "설계·운전·경제": ["design", "operation", "maintenance", "economic", "cost", "control room", "optimization", "management", "policy", "sociotechnical"],
}

def strip_markup(value):
    return re.sub(r"<[^>]+>", " ", value or "").strip()

def areas_for(record):
    text = f"{record.get('title','')} {strip_markup(record.get('abstract',''))}".lower()
    found = [name for name, terms in TOPICS.items() if any(term in text for term in terms)]
    return found or ["기타 원자력"]

def document_type(title):
    value = title.lower().strip()
    if "corrigendum" in value: return "정오표"
    if value == "editorial board" or value.startswith("introduction:"): return "편집물"
    if any(x in value for x in ["review", "recent progress", "perspective", "retrospective"]): return "리뷰·관점"
    return "연구논문"

def export_payload(con):
    con.row_factory = sqlite3.Row
    return {
        "papers": [dict(r) for r in con.execute("SELECT * FROM papers ORDER BY doi_registered_date DESC,journal,title_en")],
        "runs": [dict(r) for r in con.execute("SELECT * FROM collection_runs ORDER BY period_end DESC")],
        "topics": [dict(r) for r in con.execute("SELECT * FROM topics ORDER BY topic_id")],
        "paper_topics": [dict(r) for r in con.execute("SELECT * FROM paper_topics ORDER BY doi,is_primary DESC,topic_ko")],
        "journal_summary": [dict(r) for r in con.execute("SELECT journal,COUNT(*) paper_count FROM papers GROUP BY journal ORDER BY paper_count DESC")],
        "topic_summary": [dict(r) for r in con.execute("SELECT primary_topic,COUNT(*) paper_count FROM papers GROUP BY primary_topic ORDER BY paper_count DESC")],
        "type_summary": [dict(r) for r in con.execute("SELECT document_type,COUNT(*) paper_count FROM papers GROUP BY document_type ORDER BY paper_count DESC")],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True); p.add_argument("--end", required=True); p.add_argument("--run-date", required=True)
    args = p.parse_args()
    records = json.loads((ROOT / "articles.json").read_text(encoding="utf-8"))
    translations = (ROOT / "title_translations_ko.txt").read_text(encoding="utf-8").splitlines()
    if len(records) != len(translations): raise RuntimeError("translation count mismatch")
    translations = {r["doi"].lower(): t for r, t in zip(records, translations)}
    db = PROJECT / "data" / "working.sqlite"
    con = sqlite3.connect(db); con.execute("PRAGMA foreign_keys=ON")
    columns = {row[1] for row in con.execute("PRAGMA table_info(papers)")}
    with con:
        if "countries" not in columns: con.execute("ALTER TABLE papers ADD COLUMN countries TEXT NOT NULL DEFAULT ''")
        if "primary_country" not in columns: con.execute("ALTER TABLE papers ADD COLUMN primary_country TEXT NOT NULL DEFAULT ''")
        if "country_source" not in columns: con.execute("ALTER TABLE papers ADD COLUMN country_source TEXT NOT NULL DEFAULT ''")
    run_id = args.run_date
    before = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    with con:
        for i, (topic, terms) in enumerate(list(TOPICS.items()) + [("기타 원자력", [])], 1):
            con.execute("INSERT INTO topics(topic_id,topic_ko,keywords,active) VALUES(?,?,?,1) ON CONFLICT(topic_ko) DO UPDATE SET keywords=excluded.keywords,active=1", (i, topic, "; ".join(terms)))
        con.execute("INSERT INTO collection_runs(run_id,period_start,period_end,executed_at,found_count,new_count,updated_count,error_count,source_note) VALUES(?,?,?,?,0,0,0,0,?) ON CONFLICT(run_id) DO UPDATE SET period_start=excluded.period_start,period_end=excluded.period_end,executed_at=excluded.executed_at", (run_id,args.start,args.end,datetime.now().isoformat(timespec="seconds"),"Crossref DOI created date; five target journals; weekly window"))
        for r in records:
            doi = r["doi"].lower(); areas = areas_for(r); authors = "; ".join(r.get("authors", []))
            abstract_url = r.get("publisher_url") or r.get("doi_url") or f"https://doi.org/{doi}"
            con.execute("""INSERT INTO papers(doi,title_en,title_ko,journal,issn,authors,doi_registered_date,published_online,issue_date,document_type,primary_topic,abstract,abstract_url,doi_url,open_access,first_seen,last_checked,status,source,countries,primary_country,country_source)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(doi) DO UPDATE SET title_en=excluded.title_en,title_ko=excluded.title_ko,journal=excluded.journal,issn=excluded.issn,authors=CASE WHEN excluded.authors<>'' THEN excluded.authors ELSE papers.authors END,doi_registered_date=excluded.doi_registered_date,published_online=COALESCE(NULLIF(excluded.published_online,''),papers.published_online),issue_date=COALESCE(NULLIF(excluded.issue_date,''),papers.issue_date),document_type=excluded.document_type,primary_topic=excluded.primary_topic,abstract=COALESCE(NULLIF(excluded.abstract,''),papers.abstract),abstract_url=excluded.abstract_url,doi_url=excluded.doi_url,open_access=excluded.open_access,last_checked=excluded.last_checked,status='active',source=excluded.source,countries=COALESCE(NULLIF(excluded.countries,''),papers.countries),primary_country=COALESCE(NULLIF(excluded.primary_country,''),papers.primary_country),country_source=COALESCE(NULLIF(excluded.country_source,''),papers.country_source)""",
            (doi,r["title"],translations[doi],r["journal"],r.get("issn",""),authors,r.get("registered_date",""),r.get("published_online",""),r.get("issued",""),document_type(r["title"]),areas[0],strip_markup(r.get("abstract","")),abstract_url,r.get("doi_url") or f"https://doi.org/{doi}",int(bool(r.get("open_access"))),args.end,args.run_date,"active","Crossref + publisher metadata",";".join(r.get("countries",[])),r.get("primary_country",""),r.get("country_source","")))
            con.execute("DELETE FROM paper_topics WHERE doi=?", (doi,))
            for j, area in enumerate(areas): con.execute("INSERT INTO paper_topics(doi,topic_ko,is_primary) VALUES(?,?,?)", (doi,area,int(j==0)))
            con.execute("INSERT OR IGNORE INTO paper_runs(doi,run_id) VALUES(?,?)", (doi,run_id))
        after = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        con.execute("UPDATE collection_runs SET found_count=?,new_count=?,updated_count=?,error_count=0 WHERE run_id=?", (len(records),after-before,len(records)-(after-before),run_id))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    foreign = con.execute("PRAGMA foreign_key_check").fetchall()
    duplicates = con.execute("SELECT COUNT(*) FROM (SELECT doi FROM papers GROUP BY doi HAVING COUNT(*)>1)").fetchone()[0]
    payload = export_payload(con); con.close()
    if integrity != "ok" or foreign or duplicates: raise RuntimeError(f"database validation failed: {integrity}, foreign={len(foreign)}, duplicates={duplicates}")
    shutil.copy2(db, PROJECT / "backups" / f"{args.run_date}.sqlite"); shutil.copy2(db, PROJECT / "backups" / "latest.sqlite")
    shutil.copy2(ROOT / "articles.json", PROJECT / "raw" / f"{args.run_date}-crossref.json")
    (ROOT / "db_export.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    with (PROJECT / "logs" / "collection-history.log").open("a",encoding="utf-8") as f: f.write(f"{datetime.now().isoformat(timespec='seconds')} run={run_id} papers={len(payload['papers'])} found={len(records)} new={after-before} integrity={integrity}\n")
    print(json.dumps({"run_id":run_id,"found":len(records),"new":after-before,"papers":len(payload["papers"]),"runs":len(payload["runs"]),"integrity":integrity,"foreign_key_issues":len(foreign),"doi_duplicates":duplicates},ensure_ascii=False))

if __name__ == "__main__": main()
