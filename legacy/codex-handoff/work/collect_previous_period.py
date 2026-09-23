import argparse
import json
from pathlib import Path

import requests


JOURNALS = {
    "Nuclear Engineering and Design": "0029-5493",
    "Annals of Nuclear Energy": "0306-4549",
    "Nuclear Engineering and Technology": "1738-5733",
    "Progress in Nuclear Energy": "0149-1970",
    "Nuclear Technology": "0029-5450",
}
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "articles_previous.json"))
    args = parser.parse_args()
    records = []
    for journal, issn in JOURNALS.items():
        response = requests.get(
            f"https://api.crossref.org/journals/{issn}/works",
            params={
                "filter": f"from-created-date:{args.start},until-created-date:{args.end}",
                "select": "DOI,title,created,type",
                "rows": 1000,
            },
            headers={"User-Agent": "NuclearLiteratureDigest/2.1 (mailto:hysms@hanyang.ac.kr)"},
            timeout=60,
        )
        response.raise_for_status()
        for item in response.json()["message"]["items"]:
            created = item.get("created", {}).get("date-time", "")[:10]
            if args.start <= created <= args.end:
                records.append({
                    "journal": journal,
                    "title": item.get("title", [""])[0],
                    "doi": item.get("DOI", ""),
                    "registered_date": created,
                    "type": item.get("type", ""),
                })
    output = Path(args.output)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"start": args.start, "end": args.end, "count": len(records), "by_journal": {j: sum(r["journal"] == j for r in records) for j in JOURNALS}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
