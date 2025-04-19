import json
from bs4 import BeautifulSoup
from logger import get_logger
from parsing_cases.utils import resolve_output_path

logger = get_logger("splitter")

INPUT_PATH = resolve_output_path("data/cases_data/case_texts.jsonl")
OUTPUT_PATH = resolve_output_path("data/cases_data/case_texts_split.jsonl")
FAILED_PATH = resolve_output_path("data/cases_data/failed_split.json")

PLOT_MARKERS = {"установил", "у с т а н о в и л"}
OPERATIVE_MARKERS = {
    "постановил",
    "приговорил",
    "решил",
    "п о с т а н о в и л",
    "п р и г о в о р и л",
    "р е ш и л",
    "постановила",
    "приговорила",
    "решила",
    "п о с т а н о в и л а",
    "п р и г о в о р и л а",
    "р е ш и л а",
}


def normalize(text):
    return text.lower().replace(":", "").replace(" ", "").strip()


def is_marker(text, marker_set):
    return normalize(text) in marker_set


def extract_parts_from_html(raw_html):
    soup = BeautifulSoup(raw_html, "lxml")

    # Remove ads and non-content
    for tag in soup(["script", "style"]):
        tag.decompose()
    for ad in soup.select("[id^=adfox_]"):
        ad.decompose()
    for ad_div in soup.find_all("div", class_="adv_inside_text"):
        ad_div.decompose() 

    # Flatten all text elements for sequential scan
    segments = []
    for tag in soup.find_all(string=True):
        clean = tag.strip()
        if clean:
            segments.append(clean)

    # Find first PLOT marker and OPERATIVE marker (as indices)
    plot_idx = None
    op_idx = None
    for i, seg in enumerate(segments):
        if plot_idx is None and is_marker(seg, PLOT_MARKERS):
            plot_idx = i
        elif op_idx is None and is_marker(seg, OPERATIVE_MARKERS):
            op_idx = i

    # Decide how to split
    if plot_idx is not None and op_idx is not None:
        plot_text = "\n".join(segments[plot_idx + 1 : op_idx]).strip()
        op_text = "\n".join(segments[op_idx + 1 :]).strip()
        return plot_text, op_text

    elif plot_idx is not None:
        plot_text = "\n".join(segments[plot_idx + 1 :]).strip()
        return plot_text, None

    elif op_idx is not None:
        op_text = "\n".join(segments[op_idx + 1 :]).strip()
        return None, op_text

    return None, None


def main():
    total, ok_both, only_plot, only_op, neither = 0, 0, 0, 0, 0
    failed_entries = []

    with open(INPUT_PATH, encoding="utf-8") as fin, open(
        OUTPUT_PATH, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            total += 1
            try:
                entry = json.loads(line)
                raw = entry.pop("raw_text", "")

                plot, op = extract_parts_from_html(raw)
                entry["plot"] = plot or ""
                entry["operative"] = op or ""

                if plot and op:
                    ok_both += 1
                elif plot:
                    only_plot += 1
                    failed_entries.append({**entry, "missing": "operative"})
                elif op:
                    only_op += 1
                    failed_entries.append({**entry, "missing": "plot"})
                else:
                    neither += 1
                    failed_entries.append({**entry, "missing": "both"})

                fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

            except Exception as e:
                logger.error(f"Failed to parse line {total}: {e}")

    logger.info(f"Processed {total} cases")
    logger.info(f"Both parts found: {ok_both}")
    logger.info(f"Only plot found: {only_plot}")
    logger.info(f"Only operative found: {only_op}")
    logger.info(f"Neither found: {neither}")

    if failed_entries:
        with open(FAILED_PATH, "w", encoding="utf-8") as f:
            json.dump(failed_entries, f, ensure_ascii=False, indent=2)
        logger.info(
            f"Saved {len(failed_entries)} partial/missing cases to {FAILED_PATH}"
        )


if __name__ == "__main__":
    main()
