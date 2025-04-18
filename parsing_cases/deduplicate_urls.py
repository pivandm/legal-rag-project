import json

with open("data/cases_data/case_links.json", encoding="utf-8") as f:
    cases = json.load(f)

seen = set()
unique = []
for c in cases:
    if c["case_url"] not in seen:
        seen.add(c["case_url"])
        unique.append(c)

with open("data/cases_data/case_links_deduped.json", "w", encoding="utf-8") as f:
    json.dump(unique, f, ensure_ascii=False, indent=2)

print(f"Deduplicated: {len(cases)} → {len(unique)}")
