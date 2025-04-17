from retrieval import load_config
from logger import get_logger

if __name__ == "__main__":
    logger = get_logger()
    logger.info("Starting script...")
    config = load_config("laws_jina_1024")
    print(type(config["truncate_dim"]))
    logger.info("Script finished.")