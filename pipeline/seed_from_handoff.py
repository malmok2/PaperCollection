"""One-time migration: rebuild data/literature.sqlite from the Codex handoff's db_export.json.

    python -m pipeline.seed_from_handoff path/to/db_export.json [path/to/title_translations_ko.json]
"""
import json
import sys
from pathlib import Path

from . import database
from .common import DB_PATH, TRANSLATIONS_PATH, write_json

PAPER_COLUMNS = [
    "doi", "title_en", "title_ko", "journal", "issn", "authors", "doi_registered_date", "published_online", "issue_date",
    "document_type", "primary_topic", "abstract", "abstract_url", "doi_url", "open_access", "first_seen", "last_checked",
    "status", "source", "countries", "primary_country", "country_source",
]


def main():
    export = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} already exists; delete it first to reseed")
    con = database.connect()
    with con:
        for run in export["runs"]:
            con.execute(
                "INSERT INTO collection_runs(run_id,period_start,period_end,executed_at,found_count,new_count,updated_count,error_count,source_note) VALUES(?,?,?,?,?,?,?,?,?)",
                tuple(run[k] for k in ["run_id", "period_start", "period_end", "executed_at", "found_count", "new_count", "updated_count", "error_count", "source_note"]),
            )
        for paper in export["papers"]:
            values = [paper.get(c) if paper.get(c) is not None else "" for c in PAPER_COLUMNS]
            con.execute(f"INSERT INTO papers({','.join(PAPER_COLUMNS)},abstract_source) VALUES({','.join('?' * len(PAPER_COLUMNS))},'')", values)
            database.set_topics(con, paper["doi"], {"title": paper["title_en"], "abstract": paper.get("abstract")})
            for run in export["runs"]:
                if run["period_start"] <= (paper.get("doi_registered_date") or "") <= run["period_end"]:
                    con.execute("INSERT OR IGNORE INTO paper_runs(doi,run_id) VALUES(?,?)", (paper["doi"], run["run_id"]))
    print(json.dumps({"papers": len(export["papers"]), "runs": len(export["runs"]), "integrity": database.validate(con)}))

    cache = {p["doi"]: {"ko": p["title_ko"], "engine": "mymemory"} for p in export["papers"] if p.get("title_ko")}
    write_json(TRANSLATIONS_PATH, dict(sorted(cache.items())))
    database.dump(con)
    con.close()


if __name__ == "__main__":
    main()
