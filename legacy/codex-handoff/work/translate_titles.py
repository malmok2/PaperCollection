import json
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
articles = json.loads((ROOT / "articles.json").read_text(encoding="utf-8"))
cache_path = ROOT / "title_translations_ko.json"
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

session = requests.Session()
for index, article in enumerate(articles, 1):
    doi = article["doi"]
    if cache.get(doi):
        continue
    response = session.get(
        "https://api.mymemory.translated.net/get",
        params={"q": article["title"], "langpair": "en|ko"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    translated = payload.get("responseData", {}).get("translatedText", "").strip()
    cache[doi] = translated or article["title"]
    if index % 10 == 0:
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(0.2)

cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "title_translations_ko.txt").write_text(
    "\n".join(cache.get(article["doi"], article["title"]) for article in articles) + "\n",
    encoding="utf-8",
)
print(json.dumps({"translated": len(cache), "expected": len(articles)}, ensure_ascii=False))
