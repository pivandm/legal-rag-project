```markdown
# Legal RAG

This repository contains a Legal Retrieval-Augmented Generation (RAG) system designed to support legal document parsing, embedding, retrieval, and conversational querying via bot integration.

## Project Structure

```
.
├── bot/                 # Bot setup and main execution
├── configs_retriever/   # Retrieval configuration files
├── data/                # Data folder (not provided here but can be downloaded from Drive)
├── eval_results/        # Output from evaluation experiments
├── evaluation/          # Scripts for evaluating generation and rertieval
├── ingestion/           # Scripts to load data into Qdrant
├── logs/                # Logs will be here
├── parsing_cases/       # Case document parsing scripts
├── parsing_laws/        # Law document parsing scripts
├── qdrant_data/         # Qdrant-related local files (will be created if running db locally)
├── retrieval/           # Retrieval logic and modules
├── .env                 # Environment variable file (needs to be created)
├── .env.example         # Example environment variable template
├── .gitignore           # Git ignore file
```

## Setup Instructions

### 1. Install Dependencies

Ensure you have Python 3.10.11+ installed.

It is advised to use venv
```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

pip install -r requirements.txt
```

Some models are downloaded automatically by Hugging Face during execution. One model must be manually installed for CPU optimised performance:

- https://huggingface.co/EmbeddedLLM/bge-reranker-v2-m3-onnx-o3-cpu

You can install or cache it locally with:

```bash
huggingface-cli download EmbeddedLLM/bge-reranker-v2-m3-onnx-o3-cpu
```

### 2. Start Qdrant via Docker

Install Docker if not already installed, then run:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 3. Upload Embeddings to Qdrant

Download the precomputed embeddings from the following link:

https://drive.google.com/file/d/1xUBosOdibbwwhXCLKxCmXFdey0wh-cam/view?usp=sharing

Once downloaded, place the files in the appropriate location (data/embeddings) and upload them to Qdrant collections using:

```bash
python ingestion/load_to_qdrant.py <config_name>
```

Replace `<config_name>` with a filename from the `configs_retriever/` directory. The loading function is located in the `ingestion` module.

### 4. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit the `.env` file and insert your API keys:

- `OPENROUTER_API_KEY`
- `HF_TOKEN`
- `BOT_TOKEN`

### 5. Run the Bot

Once everything is set up, start the Legal RAG bot:

```bash
python bot/main.py
```

## Notes

- This project uses Hugging Face models and Qdrant as the vector database.
- All experiments are organized in the `evaluation/` and `eval_results/` directories.
- Ensure that `.env` is properly configured before running the bot.
```
