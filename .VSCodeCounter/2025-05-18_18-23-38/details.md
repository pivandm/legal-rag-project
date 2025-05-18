# Details

Date : 2025-05-18 18:23:38

Directory c:\\vscode-projects\\legal-rag-project

Total : 51 files,  4855 codes, 64 comments, 462 blanks, all 5381 lines

[Summary](results.md) / Details / [Diff Summary](diff.md) / [Diff Details](diff-details.md)

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [README.md](/README.md) | Markdown | 8 | 0 | 1 | 9 |
| [bot/\_\_init\_\_.py](/bot/__init__.py) | Python | 0 | 0 | 1 | 1 |
| [bot/config.yaml](/bot/config.yaml) | YAML | 5 | 5 | 3 | 13 |
| [bot/load\_config.py](/bot/load_config.py) | Python | 20 | 0 | 8 | 28 |
| [bot/main.py](/bot/main.py) | Python | 162 | 8 | 40 | 210 |
| [bot/startup.py](/bot/startup.py) | Python | 8 | 0 | 3 | 11 |
| [bot/utils.py](/bot/utils.py) | Python | 31 | 7 | 13 | 51 |
| [configs\_retriever/cases\_bge.yaml](/configs_retriever/cases_bge.yaml) | YAML | 10 | 0 | 1 | 11 |
| [configs\_retriever/laws\_bge.yaml](/configs_retriever/laws_bge.yaml) | YAML | 10 | 0 | 1 | 11 |
| [configs\_retriever/laws\_gte.yaml](/configs_retriever/laws_gte.yaml) | YAML | 10 | 0 | 1 | 11 |
| [configs\_retriever/laws\_jina.yaml](/configs_retriever/laws_jina.yaml) | YAML | 12 | 0 | 1 | 13 |
| [configs\_retriever/laws\_qwen.yaml](/configs_retriever/laws_qwen.yaml) | YAML | 11 | 0 | 1 | 12 |
| [construct\_eval\_excel.py](/construct_eval_excel.py) | Python | 10 | 3 | 4 | 17 |
| [eval\_results/models\_comparison\_at10.csv](/eval_results/models_comparison_at10.csv) | CSV | 5 | 0 | 1 | 6 |
| [eval\_results/models\_comparison\_at15.csv](/eval_results/models_comparison_at15.csv) | CSV | 5 | 0 | 1 | 6 |
| [eval\_results/models\_comparison\_at5.csv](/eval_results/models_comparison_at5.csv) | CSV | 5 | 0 | 1 | 6 |
| [eval\_results/reranked\_modes\_comparison\_at5.csv](/eval_results/reranked_modes_comparison_at5.csv) | CSV | 4 | 0 | 1 | 5 |
| [eval\_results/retrieval\_modes\_comparison\_at10.csv](/eval_results/retrieval_modes_comparison_at10.csv) | CSV | 4 | 0 | 1 | 5 |
| [eval\_results/retrieval\_modes\_comparison\_at5.csv](/eval_results/retrieval_modes_comparison_at5.csv) | CSV | 4 | 0 | 1 | 5 |
| [evaluation/\_\_init\_\_.py](/evaluation/__init__.py) | Python | 0 | 0 | 1 | 1 |
| [evaluation/eval\_dset\_laws.json](/evaluation/eval_dset_laws.json) | JSON | 1,288 | 0 | 2 | 1,290 |
| [evaluation/get\_responses.py](/evaluation/get_responses.py) | Python | 160 | 2 | 38 | 200 |
| [evaluation/laws\_retriever\_gridsearch.ipynb](/evaluation/laws_retriever_gridsearch.ipynb) | JSON | 971 | 0 | 1 | 972 |
| [generation\_eval\_dset.json](/generation_eval_dset.json) | JSON | 202 | 0 | 1 | 203 |
| [generation\_eval\_results.json](/generation_eval_results.json) | JSON | 302 | 0 | 0 | 302 |
| [generation\_eval\_results\_old.json](/generation_eval_results_old.json) | JSON | 302 | 0 | 0 | 302 |
| [ingestion/\_\_init\_\_.py](/ingestion/__init__.py) | Python | 0 | 0 | 1 | 1 |
| [ingestion/load\_to\_qdrant.py](/ingestion/load_to_qdrant.py) | Python | 97 | 8 | 21 | 126 |
| [ingestion/upsert\_fz.py](/ingestion/upsert_fz.py) | Python | 53 | 6 | 13 | 72 |
| [logger.py](/logger.py) | Python | 82 | 3 | 27 | 112 |
| [parsing\_cases/\_\_init\_\_.py](/parsing_cases/__init__.py) | Python | 0 | 0 | 1 | 1 |
| [parsing\_cases/collect\_raw\_texts.py](/parsing_cases/collect_raw_texts.py) | Python | 119 | 10 | 26 | 155 |
| [parsing\_cases/collect\_urls.py](/parsing_cases/collect_urls.py) | Python | 119 | 0 | 33 | 152 |
| [parsing\_cases/deduplicate\_urls.py](/parsing_cases/deduplicate_urls.py) | Python | 12 | 0 | 5 | 17 |
| [parsing\_cases/split\_clean.py](/parsing_cases/split_clean.py) | Python | 99 | 4 | 28 | 131 |
| [parsing\_cases/utils.py](/parsing_cases/utils.py) | Python | 6 | 0 | 3 | 9 |
| [parsing\_laws/\_\_init\_\_.py](/parsing_laws/__init__.py) | Python | 0 | 1 | 1 | 2 |
| [parsing\_laws/parsing\_apk.py](/parsing_laws/parsing_apk.py) | Python | 32 | 0 | 11 | 43 |
| [parsing\_laws/parsing\_fz.py](/parsing_laws/parsing_fz.py) | Python | 62 | 2 | 13 | 77 |
| [parsing\_laws/parsing\_gk.py](/parsing_laws/parsing_gk.py) | Python | 45 | 1 | 14 | 60 |
| [parsing\_laws/parsing\_gpk.py](/parsing_laws/parsing_gpk.py) | Python | 32 | 0 | 11 | 43 |
| [parsing\_laws/parsing\_kas.py](/parsing_laws/parsing_kas.py) | Python | 32 | 0 | 11 | 43 |
| [parsing\_laws/parsing\_koap.py](/parsing_laws/parsing_koap.py) | Python | 32 | 0 | 11 | 43 |
| [parsing\_laws/parsing\_nk\_rf.py](/parsing_laws/parsing_nk_rf.py) | Python | 43 | 2 | 14 | 59 |
| [parsing\_laws/parsing\_uk.py](/parsing_laws/parsing_uk.py) | Python | 32 | 0 | 11 | 43 |
| [parsing\_laws/parsing\_upk.py](/parsing_laws/parsing_upk.py) | Python | 32 | 0 | 11 | 43 |
| [parsing\_laws/utils.py](/parsing_laws/utils.py) | Python | 68 | 1 | 22 | 91 |
| [retrieval/\_\_init\_\_.py](/retrieval/__init__.py) | Python | 12 | 0 | 0 | 12 |
| [retrieval/config.py](/retrieval/config.py) | Python | 14 | 0 | 6 | 20 |
| [retrieval/reranker.py](/retrieval/reranker.py) | Python | 22 | 0 | 3 | 25 |
| [retrieval/tools.py](/retrieval/tools.py) | Python | 261 | 1 | 38 | 300 |

[Summary](results.md) / Details / [Diff Summary](diff.md) / [Diff Details](diff-details.md)