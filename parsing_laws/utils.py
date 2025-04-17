import requests
from bs4 import BeautifulSoup
import urllib3
import logging
import os
import re
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except requests.HTTPError as e:
        logging.error(f"HTTP error {r.status_code} while accessing {url}")
    except Exception as e:
        logging.error(f"Failed to load {url} => {e}")
    return None


def extract_statia_links(start_url, law_name="статья", base_url="https://sudact.ru"):
    logging.info(f"Extracting article links from {start_url}")
    soup = get_soup(start_url)
    if not soup:
        return {}

    statia_links = {}

    for a in soup.select("a[href*='/statia-']"):
        href = a.get("href")
        text = a.get_text(strip=True)
        # Matches "статья 5.63.1" or "Статья 330.1" etc.
        match = re.search(
            rf"{law_name}\s+(\d+(?:\.\d+)*)(?=\s|\.|$)", text, re.IGNORECASE
        )
        if match and href:
            number = match.group(1)
            full_url = urljoin(base_url, href)
            statia_links[number] = full_url

    logging.info(f"Found {len(statia_links)} article links")

    def smart_key(k):
        return [int(p) for p in k.split(".")]

    return dict(sorted(statia_links.items(), key=lambda x: smart_key(x[0])))


def extract_article_text(url):
    soup = get_soup(url)
    if not soup:
        return None

    body = soup.select_one("#law_text_body")
    if not body:
        logging.error(f"No law_text_body found at {url}")
        return None

    paragraphs = [
        p.get_text(strip=True) for p in body.find_all("p") if p.get_text(strip=True)
    ]
    pre_blocks = [
        pre.get_text(strip=True)
        for pre in body.find_all("pre")
        if pre.get_text(strip=True)
    ]
    content = paragraphs + pre_blocks

    if not content:
        logging.warning(f"Empty content at {url}")
        return None

    return "\n\n".join(content)


def resolve_output_path(relative_path_from_project_root):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(
        os.path.join(script_dir, "..", relative_path_from_project_root)
    )
