"""Weekly pipeline entry point.

    python -m pipeline.run_weekly                     # this week's Monday (Asia/Seoul)
    python -m pipeline.run_weekly --run-date 2026-09-21
    python -m pipeline.run_weekly --skip-collect --no-email   # rebuild outputs from the DB only

Missed weeks between the last recorded run and the target Monday are collected automatically
(emails are sent only for the target week).
"""
import argparse
import json
import os
import traceback
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import shutil

from . import build_dashboard, build_database_page, build_email, build_excel, collect, database, send_email, translate
from .common import OUTPUT_DIR, SETTINGS, SITE_DIR, STATE_DIR, Period, raw_path, write_json

KST = ZoneInfo("Asia/Seoul")
STATUS_PATH = STATE_DIR / "latest-run.json"


def log(event, **fields):
    print(json.dumps({"time": datetime.now(KST).isoformat(timespec="seconds"), "event": event, **fields}, ensure_ascii=False, default=str), flush=True)


def weeks_to_collect(con, target, max_backfill):
    last = database.last_run_id(con)
    weeks = []
    if last:
        monday = date.fromisoformat(last) + timedelta(days=7)
        while monday < target.run_date:
            weeks.append(Period(monday))
            monday += timedelta(days=7)
    if len(weeks) > max_backfill:
        raise RuntimeError(f"{len(weeks)} missed weeks since {last}; run with --max-backfill {len(weeks)} to confirm")
    return weeks + [target]


def collect_week(con, period):
    records = collect.collect(period)
    stats = translate.translate_records(records)
    write_json(raw_path(period, "current"), records)
    found, new = database.upsert_run(con, period, records)
    log("collected", run_id=period.run_id, start=period.start, end=period.end, found=found, new=new, translation=stats)
    return found


def build_outputs(con, period):
    current = [database.as_record(r) for r in database.papers_between(con, period.start, period.end)]
    previous = [database.as_record(r) for r in database.papers_between(con, period.previous.start, period.previous.end)]
    payload = database.export_payload(con)
    cumulative = [database.as_record(r) for r in payload["papers"]]

    (SITE_DIR / "archive").mkdir(parents=True, exist_ok=True)
    for path, prefix in [(SITE_DIR / "index.html", "./"), (SITE_DIR / "archive" / f"{period.run_id}.html", "../")]:
        page = build_dashboard.render(period, [dict(r) for r in current], previous, cumulative, len(payload["runs"]), prefix)
        path.write_text(page, encoding="utf-8")
    (SITE_DIR / ".nojekyll").touch()

    email_html = build_email.render(period, current, previous, len(payload["papers"]), len(payload["runs"]))
    email_path = OUTPUT_DIR / f"email-{period.run_id}.html"
    email_path.parent.mkdir(parents=True, exist_ok=True)
    email_path.write_text(email_html, encoding="utf-8")

    excel_path = build_excel.build(payload, OUTPUT_DIR / "nuclear-literature-database.xlsx")
    shutil.copy2(excel_path, SITE_DIR / excel_path.name)
    archives = [path.stem for path in (SITE_DIR / "archive").glob("*.html")]
    (SITE_DIR / "database.html").write_text(build_database_page.render(payload, archives), encoding="utf-8")
    return {"current": len(current), "previous": len(previous), "papers": len(payload["papers"]), "runs": len(payload["runs"]),
            "email_html": email_html, "email_path": email_path, "excel_path": excel_path}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", default=os.environ.get("RUN_DATE") or datetime.now(KST).date().isoformat())
    parser.add_argument("--skip-collect", action="store_true")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--force-email", action="store_true", help="Send even if this week was already sent")
    parser.add_argument("--max-backfill", type=int, default=6)
    args = parser.parse_args()

    period = Period.for_date(date.fromisoformat(args.run_date))
    started = datetime.now(KST)
    status = {"run_date": period.run_id, "period_start": str(period.start), "period_end": str(period.end), "started_at": started.isoformat(timespec="seconds")}
    try:
        con = database.connect()
        if not args.skip_collect:
            for week in weeks_to_collect(con, period, args.max_backfill):
                collect_week(con, week)
            log("enriched", **collect.enrich_recent(con, since=period.start - timedelta(weeks=11)))
        database.sync_titles(con, translate.load_cache())
        integrity = database.validate(con)
        result = build_outputs(con, period)
        database.dump(con)
        con.close()
        if result["current"] == 0:
            raise RuntimeError(f"no papers found for {period.start}~{period.end}; Crossref may be delayed. Not sending an empty digest.")

        email_state = "disabled (--no-email)"
        if not args.no_email:
            if send_email.smtp_configured():
                email_state = send_email.send_digest(period.run_id, result["email_html"], force=args.force_email)
            else:
                email_state = "skipped: SMTP_USER/SMTP_PASSWORD not configured"
        status.update({
            "status": "success", "article_count": result["current"], "previous_count": result["previous"],
            "total_papers": result["papers"], "total_runs": result["runs"], "integrity": integrity,
            "email": email_state, "recipients": SETTINGS["recipients"], "dashboard_url": SETTINGS.get("dashboard_url", ""),
            "email_path": str(result["email_path"].relative_to(OUTPUT_DIR.parent)),
            "excel_path": str(result["excel_path"].relative_to(OUTPUT_DIR.parent)),
            "finished_at": datetime.now(KST).isoformat(timespec="seconds"),
        })
        write_json(STATUS_PATH, status)
        log("done", **{k: v for k, v in status.items() if k != "recipients"})
    except Exception as error:
        status.update({"status": "failed", "error": f"{type(error).__name__}: {error}", "finished_at": datetime.now(KST).isoformat(timespec="seconds")})
        write_json(STATUS_PATH, status)
        traceback.print_exc()
        log("failed", error=status["error"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
