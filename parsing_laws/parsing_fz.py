import json
import time
import os
from parsing_laws.utils import (
    extract_statia_links,
    extract_article_text,
    resolve_output_path,
)
from logger import get_logger

# Dictionary of law name -> URL
LAW_SOURCES = {
    "ФЗ О ПОЖАРНОЙ БЕЗОПАСНОСТИ": "https://sudact.ru/law/federalnyi-zakon-ot-21121994-n-69-fz-o/",
    "ФЗ ОБ ОСАГО": "https://sudact.ru/law/federalnyi-zakon-ot-25042002-n-40-fz-s/",
    "ФЗ ОБ ОБРАЗОВАНИИ": "https://sudact.ru/law/federalnyi-zakon-ot-29122012-n-273-fz-ob/",
    "ФЗ О ГОСУДАРСТВЕННОЙ ГРАЖДАНСКОЙ СЛУЖБЕ": "https://sudact.ru/law/federalnyi-zakon-ot-27072004-n-79-fz-o/",
    "ФЗ О ГОСУДАРСТВЕННОМ ОБОРОННОМ ЗАКАЗЕ": "https://sudact.ru/law/federalnyi-zakon-ot-29122012-n-275-fz-o/",
    "ФЗ О ЗАЩИТЕ ПРАВ ПОТРЕБИТЕЛЕЙ": "https://sudact.ru/law/zakon-rf-ot-07021992-n-2300-1-o/",
    "ФЗ О ПРОТИВОДЕЙСТВИИ КОРРУПЦИИ": "https://sudact.ru/law/federalnyi-zakon-ot-25122008-n-273-fz-o/",
    "ФЗ О РЕКЛАМЕ": "https://sudact.ru/law/federalnyi-zakon-ot-13032006-n-38-fz-o/",
    "ФЗ ОБ ОХРАНЕ ОКРУЖАЮЩЕЙ СРЕДЫ": "https://sudact.ru/law/federalnyi-zakon-ot-10012002-n-7-fz-ob/",
    "ФЗ О ПОЛИЦИИ": "https://sudact.ru/law/federalnyi-zakon-ot-07022011-n-3-fz-o/",
    "ФЗ О БУХГАЛТЕРСКОМ УЧЕТЕ": "https://sudact.ru/law/federalnyi-zakon-ot-06122011-n-402-fz-o/",
    "ФЗ О ЗАЩИТЕ КОНКУРЕНЦИИ": "https://sudact.ru/law/federalnyi-zakon-ot-26072006-n-135-fz-o/",
    "ФЗ О ЛИЦЕНЗИРОВАНИИ ОТДЕЛЬНЫХ ВИДОВ ДЕЯТЕЛЬНОСТИ": "https://sudact.ru/law/federalnyi-zakon-ot-04052011-n-99-fz-o/",
    "ФЗ ОБ ООО": "https://sudact.ru/law/federalnyi-zakon-ot-08021998-n-14-fz-ob/",
    "ФЗ О ЗАКУПКАХ ТОВАРОВ, РАБОТ, УСЛУГ ОТДЕЛЬНЫМИ ВИДАМИ ЮРИДИЧЕСКИХ ЛИЦ": "https://sudact.ru/law/federalnyi-zakon-ot-18072011-n-223-fz-o/",
    "ФЗ О ПРОКУРАТУРЕ": "https://sudact.ru/law/zakon-rf-ot-17011992-n-2202-1-o/",
    "ФЗ О НЕСОСТОЯТЕЛЬНОСТИ (БАНКРОТСТВЕ)": "https://sudact.ru/law/federalnyi-zakon-ot-26102002-n-127-fz-o/",
    "ФЗ О ПЕРСОНАЛЬНЫХ ДАННЫХ": "https://sudact.ru/law/federalnyi-zakon-ot-27072006-n-152-fz-o/",
    "ФЗ О КОНТРАКТНОЙ СИСТЕМЕ В СФЕРЕ ЗАКУПОК ТОВАРОВ, РАБОТ, УСЛУГ ДЛЯ ОБЕСПЕЧЕНИЯ ГОСУДАРСТВЕННЫХ И МУНИЦИПАЛЬНЫХ НУЖД": "https://sudact.ru/law/federalnyi-zakon-ot-05042013-n-44-fz-o/",
    "ФЗ ОБ ИСПОЛНИТЕЛЬНОМ ПРОИЗВОДСТВЕ": "https://sudact.ru/law/federalnyi-zakon-ot-02102007-n-229-fz-ob/",
    "ФЗ О ВОИНСКОЙ ОБЯЗАННОСТИ И ВОЕННОЙ СЛУЖБЕ": "https://sudact.ru/law/federalnyi-zakon-ot-28031998-n-53-fz-o/",
    "ФЗ О БАНКАХ И БАНКОВСКОЙ ДЕЯТЕЛЬНОСТИ": "https://sudact.ru/law/zakon-rsfsr-ot-02121990-n-395-1-s/",
    "ФЗ О СТРАХОВЫХ ПЕНСИЯХ": "https://sudact.ru/law/federalnyi-zakon-ot-28122013-n-400-fz-o/",
}

# Output file path
OUTPUT_PATH = resolve_output_path("data/laws_data/fz.json")


def main():
    combined_results = []

    for law_name, start_url in LAW_SOURCES.items():
        logger.info(f"Parsing law: {law_name} from {start_url}")
        statia_links = extract_statia_links(
            start_url=start_url, law_name="статья", base_url="https://sudact.ru"
        )

        for number, url in statia_links.items():
            logger.info(f"Статья {number} of {law_name} from {url}")
            text = extract_article_text(url)
            if not text:
                continue

            combined_results.append({
                "law_code": law_name,
                "law_number": number,
                "url": url,
                "text": text
            })

            time.sleep(0.3)  # polite crawl

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(combined_results)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    global logger
    logger = get_logger()
    main()
