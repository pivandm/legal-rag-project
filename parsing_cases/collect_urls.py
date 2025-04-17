import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import dateparser
import urllib3
from datetime import datetime
from urllib.parse import urljoin
from parsing_cases.utils import resolve_output_path
from logger import get_logger, auto_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://sudact.ru"
MAX_PAGES = 30
OUTPUT_PATH = resolve_output_path("data/cases_data/case_links.json")

START_URLS = {
    "https://sudact.ru/practice/sudebnaya-praktika-po-ugolovnym-delam/": "УК РФ",
    "https://sudact.ru/practice/sudebnaya-praktika-po-administrativnym-delam/": "КоАП РФ",
    "https://sudact.ru/practice/sudebnaya-praktika-po-grazhdanskomu-kodeksu/": "ГК РФ",
}


@auto_logger
def get_soup(url, logger=None):
    try:
        res = requests.get(
            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False
        )
        res.raise_for_status()
        return BeautifulSoup(res.text, "lxml")
    except Exception as e:
        logger.error(f"Failed to load {url} => {e}")
        return None


@auto_logger
def parse_main_page(start_url, case_code, logger=None):
    soup = get_soup(start_url)
    if not soup:
        return []

    results = []
    for li in soup.select("li.wos"):
        a = li.find("a", href=True)
        div = li.find("div")

        if not a or not div:
            continue

        case_topic = a.get_text(strip=True)
        case_norm = div.get_text(strip=True)
        topic_url = urljoin(BASE_URL, a["href"])

        results.append(
            {
                "case_code": case_code,
                "case_topic": case_topic,
                "case_norm": case_norm,
                "topic_url": topic_url,
            }
        )

    logger.info(f"Found {len(results)} topics under {case_code}")
    return results


@auto_logger
def extract_case_links(topic_info, logger=None):
    topic_url = topic_info["topic_url"]
    collected = []

    for page in range(1, MAX_PAGES + 1):
        page_url = f"{topic_url}?page={page}"
        logger.info(f"Scanning page {page}: {page_url}")
        soup = get_soup(page_url)
        if not soup:
            break

        found = 0
        for a in soup.select("a[href^='/regular/doc/']"):
            full_text = a.get_text(strip=True)
            href = a.get("href")
            full_url = urljoin(BASE_URL, href)

            case_type_match = re.match(r"^(.*?) №", full_text)
            date_match = re.search(r"от (.+?) по делу", full_text)
            case_no_match = re.search(
                r"№\s*(.+?)\s+от\s+\d{1,2}\s+\S+\s+\d{4}\s+г\.", full_text
            )

            if not (case_type_match and date_match and case_no_match):
                continue

            raw_date = date_match.group(1).strip()
            parsed_date = dateparser.parse(raw_date, languages=["ru"])
            if not parsed_date:
                logger.warning(f"Date parse failed on: {raw_date}")
                continue
            case_date = parsed_date.strftime("%d.%m.%Y")

            collected.append(
                {
                    "case_code": topic_info["case_code"],
                    "case_topic": topic_info["case_topic"],
                    "case_norm": topic_info["case_norm"],
                    "case_type": case_type_match.group(1).strip(),
                    "case_date": case_date,
                    "case_no": case_no_match.group(1).strip(),
                    "case_url": full_url,
                }
            )
            found += 1

        if found == 0:
            logger.info("No cases found on this page — stopping.")
            break

        time.sleep(0.3)

    return collected


def main():
    logger = get_logger()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    all_cases = []

    for start_url, code in START_URLS.items():
        logger.info(f"Starting code section: {code}")
        topics = parse_main_page(start_url, code, logger=logger)

        for topic in topics:
            logger.info(
                f"Processing topic: {topic['case_topic']} ({topic['case_norm']})"
            )
            topic_cases = extract_case_links(topic, logger=logger)
            all_cases.extend(topic_cases)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(all_cases)} case entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
