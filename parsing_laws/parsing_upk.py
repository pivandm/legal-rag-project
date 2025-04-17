import json
import time
import os
import logging
from parsing_laws.utils import (
    extract_statia_links,
    extract_article_text,
    resolve_output_path,
)

START_URL = "https://sudact.ru/law/upk-rf/"
LAW_CODE = "УПК РФ"
OUTPUT_PATH = resolve_output_path("data/laws_data/upk_rf_statias.json")


def main():
    statia_links = extract_statia_links(
        START_URL, law_name="статья", base_url="https://sudact.ru"
    )

    results = []
    for num, url in statia_links.items():
        logging.info(f"Parsing Статья {num} from {url}")
        text = extract_article_text(url)
        if not text:
            continue

        results.append(
            {"law_code": LAW_CODE, "law_number": num, "url": url, "text": text}
        )

        time.sleep(0.3)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logging.info(f"Saved {len(results)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
