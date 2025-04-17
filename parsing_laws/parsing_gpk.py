import json
import time
import os
import logging
from parsing_laws.utils import (
    extract_statia_links,
    extract_article_text,
    resolve_output_path,
)

START_URL = "https://sudact.ru/law/gpk-rf/"
LAW_CODE = "ГПК РФ"
OUTPUT_PATH = resolve_output_path("data/laws_data/gpk_statias.json")


def main():
    statia_links = extract_statia_links(
        start_url=START_URL, law_name="статья", base_url="https://sudact.ru"
    )

    results = []
    for number, url in statia_links.items():
        logging.info(f"Parsing Статья {number} from {url}")
        text = extract_article_text(url)
        if not text:
            continue

        results.append(
            {"law_code": LAW_CODE, "law_number": number, "url": url, "text": text}
        )

        time.sleep(0.3)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logging.info(f"Saved {len(results)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
