"""Shared paths, settings, and classification rules for the weekly pipeline."""
import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "settings.json"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "literature.sqlite"
DUMP_PATH = DATA_DIR / "literature.sql"  # text form kept in git; the .sqlite is rebuilt from it
TRANSLATIONS_PATH = DATA_DIR / "translations_ko.json"
STATE_DIR = ROOT / "state"
OUTPUT_DIR = ROOT / "outputs"
SITE_DIR = ROOT / "docs"

USER_AGENT = "NuclearLiteratureDigest/3.0 (mailto:{contact})"


def load_settings():
    settings = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # Repository variables override the committed defaults without code changes.
    if os.environ.get("DASHBOARD_URL"):
        settings["dashboard_url"] = os.environ["DASHBOARD_URL"].strip()
    if os.environ.get("DIGEST_RECIPIENTS"):
        settings["recipients"] = [v.strip() for v in os.environ["DIGEST_RECIPIENTS"].split(",") if v.strip()]
    return settings


SETTINGS = load_settings()
HEADERS = {"User-Agent": USER_AGENT.format(contact=SETTINGS["contact_email"])}


@dataclass(frozen=True)
class Period:
    """A weekly window: run on Monday, collect the previous Monday..Sunday."""

    run_date: date

    @classmethod
    def for_date(cls, value: date):
        return cls(value - timedelta(days=value.weekday()))

    @property
    def start(self):
        return self.run_date - timedelta(days=7)

    @property
    def end(self):
        return self.run_date - timedelta(days=1)

    @property
    def previous(self):
        return Period(self.run_date - timedelta(days=7))

    @property
    def run_id(self):
        return self.run_date.isoformat()


def strip_markup(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def paper_text(record):
    title = record.get("title") or record.get("title_en") or ""
    return f"{title} {strip_markup(record.get('abstract', ''))}".lower()


def topics_for(record):
    text = paper_text(record)
    found = [name for name, terms in SETTINGS["topics"].items() if any(term in text for term in terms)]
    return found or [SETTINGS["fallback_topic"]]


def watchlists_for(record):
    text = paper_text(record)
    return [name for name, terms in SETTINGS["watchlists"].items() if any(term in text for term in terms)]


def document_type(title):
    value = (title or "").lower().strip()
    for label, rule in SETTINGS["document_types"].items():
        if value in rule.get("equals", []):
            return label
        if any(value.startswith(prefix) for prefix in rule.get("startswith", [])):
            return label
        if any(term in value for term in rule.get("contains", [])):
            return label
    return SETTINGS["default_document_type"]


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def raw_path(period: Period, kind: str):
    """kind: 'current' (full metadata) for the run's own window."""
    return RAW_DIR / f"{period.run_id}-{kind}.json"
