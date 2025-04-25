This is a repo of Legal RAG
to run it you have to install dependancies
docker Qdrant
all the python packages and models
then upload files drom data/embeddings to qdrant collections
with load_to_qdrant.py config_name
then create .env with all your API keys (openrouter, hf-token, bot-token)
run bot with main.py
