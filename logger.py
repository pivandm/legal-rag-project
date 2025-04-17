import logging
import os
import sys
import atexit
import time
from datetime import datetime
from pathlib import Path
import functools
import inspect

# Get the script name for file and folder
main_script = Path(sys.argv[0]).stem or "script"
LOG_DIR = os.path.join("logs", main_script)
os.makedirs(LOG_DIR, exist_ok=True)

START_TIME = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILENAME = f"{START_TIME}_{main_script}.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILENAME)

# Global handler store
_LOG_HANDLERS = []


def get_logger(name=None, stack_offset=1):
    if name is None:
        frame = inspect.stack()[stack_offset]
        module = inspect.getmodule(frame.frame)
        name = module.__name__ if module else "__main__"

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        if not _LOG_HANDLERS:
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            )

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            file_handler = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
            file_handler.setFormatter(formatter)

            _LOG_HANDLERS.extend([console_handler, file_handler])

        for handler in _LOG_HANDLERS:
            logger.addHandler(handler)

        logger.propagate = False

    return logger


def auto_logger(func):
    is_async = inspect.iscoroutinefunction(func)
    func_module = inspect.getmodule(func)
    func_logger_name = func_module.__name__ if func_module else "__main__"

    if is_async:

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(name=func_logger_name)
            kwargs["logger"] = logger
            logger.debug(f"Calling async: {func.__name__}()")
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                logger.debug(
                    f"Finished async: {func.__name__}() in {time.time() - start:.3f}s"
                )
                return result
            except Exception:
                logger.exception(f"Exception in async: {func.__name__}()")
                raise

        return wrapper

    else:

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(name=func_logger_name)
            kwargs["logger"] = logger
            logger.debug(f"Calling: {func.__name__}()")
            start = time.time()
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"Finished: {func.__name__}() in {time.time() - start:.3f}s"
                )
                return result
            except Exception:
                logger.exception(f"Exception in: {func.__name__}()")
                raise

        return wrapper


# Optional: shutdown hook
def _shutdown_logger():
    for handler in _LOG_HANDLERS:
        try:
            handler.close()
        except:
            pass


atexit.register(_shutdown_logger)
