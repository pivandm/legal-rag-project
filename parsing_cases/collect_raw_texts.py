import requests
import json
import os
import time
import random
import urllib3
from bs4 import BeautifulSoup
from logger import get_logger, auto_logger
from parsing_cases.utils import resolve_output_path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger("case_text_collector")

INPUT_PATH = resolve_output_path("data\cases_data\case_links_deduped.json")
OUTPUT_PATH = resolve_output_path("data/cases_data/case_texts.jsonl")
FAILED_PATH = resolve_output_path("data/cases_data/case_texts_failed.json")

USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.224 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2_1; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0 Edg/124.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_7_8) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    # YandexBrowser (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 YaBrowser/24.1.3.956 Yowser/2.5 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) YaBrowser/23.9.2.914 Yowser/2.5 Safari/537.36",
    # Opera (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/95.0.4635.84",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 OPR/94.0.4606.76 Safari/537.36",
    # Additional desktop variants
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Debian; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36",
]


session = requests.Session()


@auto_logger
def get_soup(url, retries=3, backoff=1.5, logger=None):
    for attempt in range(retries):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            res = session.get(url, headers=headers, timeout=10, verify=False)
            if res.status_code == 429 or 500 <= res.status_code < 600:
                logger.warning(f"Retry {attempt+1}: {url} => {res.status_code}")
                time.sleep(backoff * (attempt + 1))
                continue
            res.raise_for_status()
            return BeautifulSoup(res.text, "lxml")
        except Exception as e:
            logger.warning(f"Request failed ({url}) => {e}")
            time.sleep(backoff * (attempt + 1))
    return None


@auto_logger
def extract_raw_text(soup, logger=None):
    td = soup.select_one("td.h-col1.h-col1-inner3")
    if not td:
        logger.debug("No target <td> found in parsed HTML.")
    return str(td) if td else None


@auto_logger
def load_completed_urls(logger=None):
    if not os.path.exists(OUTPUT_PATH):
        return set()
    completed = set()
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                completed.add(obj["case_url"])
            except Exception as e:
                logger.debug(f"Skipping corrupt line in output: {e}")
                continue
    logger.info(f"Loaded {len(completed)} completed case URLs.")
    return completed


@auto_logger
def main(logger=None):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(INPUT_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    completed_urls = load_completed_urls(logger=logger)
    failed_cases = []

    total = len(cases)
    logger.info(f"Total cases: {total}")
    logger.info(f"Already collected: {len(completed_urls)}")

    with open(OUTPUT_PATH, "a", encoding="utf-8") as fout:
        for i, case in enumerate(cases, start=1):
            url = case["case_url"]
            if url in completed_urls:
                continue

            logger.info(f"Fetching [{i}/{total}]: {url}")
            soup = get_soup(url, logger=logger)
            if not soup:
                logger.warning(f"Failed to fetch soup: {url}")
                failed_cases.append(case)
                continue

            raw_text = extract_raw_text(soup, logger=logger)
            if not raw_text:
                logger.warning(f"No raw text found at {url}")
                failed_cases.append(case)
                continue

            case["raw_text"] = raw_text
            fout.write(json.dumps(case, ensure_ascii=False) + "\n")
            fout.flush()

            completed_urls.add(url)
            time.sleep(random.uniform(0.3, 0.7))

    if failed_cases:
        with open(FAILED_PATH, "w", encoding="utf-8") as f:
            json.dump(failed_cases, f, ensure_ascii=False, indent=2)
        logger.warning(f"Saved {len(failed_cases)} failed cases to: {FAILED_PATH}")

    logger.info(f"Finished. Collected {len(completed_urls)} cases.")


if __name__ == "__main__":
    main()