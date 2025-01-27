import logging
from logging.handlers import RotatingFileHandler
from config import Config

def setup_logger():
    logger = logging.getLogger('SecurityMonitor')

    if logger.handlers:
        logger.handlers = []

    try:
        logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = RotatingFileHandler(
            Config.LOG_FILE, maxBytes=1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    except AttributeError as e:
        print(f"Logger setup failed: Invalid log level '{Config.LOG_LEVEL}' - {e}")
    except PermissionError as e:
        print(f"Logger setup failed: Permission error - {e}")
    except Exception as e:
        print(f"Logger setup failed: {e}")
    return None
