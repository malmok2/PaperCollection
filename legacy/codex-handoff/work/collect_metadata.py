import argparse
import json
import time
from pathlib import Path

import requests
from urllib.parse import quote


JOURNALS = {
    "Nuclear Engineering and Design": "0029-5493",
    "Annals of Nuclear Energy": "0306-4549",
    "Nuclear Engineering and Technology": "1738-5733",
    "Progress in Nuclear Energy": "0149-1970",
    "Nuclear Technology": "0029-5450",
}


def date_parts(value):
    parts = value.get("date-parts", [[]])[0] if value else []
    return "-".join(f"{part:02d}" if index else str(part) for index, part in enumerate(parts))


def author_name(author):
    return " ".join(filter(None, [author.get("given", ""), author.get("family", "")])).strip()


def elsevier_metadata(doi):
    url = "https://api.elsevier.com/content/article/doi/" + requests.utils.quote(doi, safe="")
    response = requests.get(url, headers={"Accept": "application/json"}, timeout=30)
    if response.status_code != 200:
        return {}
    return response.json().get("full-text-retrieval-response", {}).get("coredata", {})


def openalex_countries(doi):
    url = "https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="/()")
    response = requests.get(
        url,
        params={"select": "doi,authorships"},
        headers={"User-Agent": "NuclearLiteratureDigest/2.1 (mailto:hysms@hanyang.ac.kr)"},
        timeout=30,
    )
    if response.status_code != 200:
        return [], ""
    authorships = response.json().get("authorships", [])
    countries, corresponding = [], []
    for authorship in authorships:
        codes = authorship.get("countries", []) or [
            institution.get("country_code") for institution in authorship.get("institutions", [])
            if institution.get("country_code")
        ]
        for code in codes:
            code = (code or "").upper()
            if code and code not in countries:
                countries.append(code)
            if authorship.get("is_corresponding") and code and code not in corresponding:
                corresponding.append(code)
    return countries, (corresponding or countries or [""])[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "articles.json"))
    args = parser.parse_args()
    records = []
    for journal, issn in JOURNALS.items():
        cursor = "*"
        while cursor:
            response = requests.get(
            f"https://api.crossref.org/journals/{issn}/works",
            params={
                "filter": f"from-created-date:{args.start},until-created-date:{args.end}",
                "select": "DOI,title,author,created,published-online,published-print,issued,type,abstract,URL",
                "rows": 1000,
                "cursor": cursor,
            },
            headers={"User-Agent": "NuclearLiteratureDigest/2.0 (mailto:hysms@hanyang.ac.kr)"},
            timeout=60,
            )
            response.raise_for_status()
            message = response.json()["message"]
            items = message.get("items", [])
            for item in items:
                registered = item.get("created", {}).get("date-time", "")[:10]
                if not args.start <= registered <= args.end:
                    continue
                doi = item.get("DOI", "")
                record = {
                    "journal": journal,
                    "issn": issn,
                    "title": item.get("title", [""])[0],
                    "authors": [author_name(author) for author in item.get("author", [])],
                    "doi": doi,
                    "doi_url": "https://doi.org/" + doi,
                    "registered_date": registered,
                    "published_online": date_parts(item.get("published-online")),
                    "published_print": date_parts(item.get("published-print")),
                    "issued": date_parts(item.get("issued")),
                    "publisher_url": "",
                    "pii": "",
                    "abstract": item.get("abstract", ""),
                    "keywords": [],
                    "source_status": "metadata-only",
                }
                if doi.startswith("10.1016/"):
                    core = elsevier_metadata(doi)
                    record["pii"] = core.get("pii", "")
                    links = core.get("link", [])
                    science_direct = next((link.get("@href", "") for link in links if link.get("@rel") == "scidir"), "")
                    record["publisher_url"] = science_direct or record["doi_url"]
                    record["cover_date"] = core.get("prism:coverDate", "")
                    record["open_access"] = core.get("openaccess") == "1"
                else:
                    record["publisher_url"] = record["doi_url"]
                    record["cover_date"] = ""
                    record["open_access"] = False
                record["countries"], record["primary_country"] = openalex_countries(doi)
                record["country_source"] = "OpenAlex authorship institutions" if record["countries"] else "OpenAlex: country unavailable"
                records.append(record)
                time.sleep(0.03)
            next_cursor = message.get("next-cursor")
            if not items or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

    unique = {record["doi"].lower(): record for record in records if record.get("doi")}
    records = sorted(unique.values(), key=lambda record: (record["registered_date"], record["journal"], record["title"]), reverse=True)
    output = Path(args.output)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"start": args.start, "end": args.end, "count": len(records), "by_journal": {journal: sum(r["journal"] == journal for r in records) for journal in JOURNALS}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
