# https://sudact.ru/law/nk-rf-chast1/
import json
import time
import os
import logging
from parsing_laws.utils import (
    extract_statia_links,
    extract_article_text,
    resolve_output_path,
)

START_URLS = [
    "https://sudact.ru/law/nk-rf-chast1/",
    "https://sudact.ru/law/nk-rf-chast2/",
]

LAW_CODE = "НК РФ"
OUTPUT_PATH = resolve_output_path("data/laws_data/nk_rf_statias.json")


def main():
    merged_links = {}

    # Collect all statias across parts
    for url in START_URLS:
        logging.info(f"Scanning part from: {url}")
        part_links = extract_statia_links(
            start_url=url, law_name="статья", base_url="https://sudact.ru"
        )
        for number, href in part_links.items():
            if number in merged_links:
                logging.warning(f"Duplicate article number: {number} from {href}")
            merged_links[number] = href

    logging.info(f"Total unique articles found: {len(merged_links)}")

    results = []
    for number, url in merged_links.items():
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
