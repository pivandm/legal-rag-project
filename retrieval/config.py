import yaml
import os
from logger import auto_logger


@auto_logger
def load_config(config_name: str, logger=None):
    config_path = os.path.join("configs_retriever", f"{config_name}.yaml")
    logger.info(f"Loading config: {config_path}")

    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded config with keys: {list(config.keys())}")
    return config
