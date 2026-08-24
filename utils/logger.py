import logging
import sys
import os

os.makedirs("logs", exist_ok=True)

def setup_logger():
    logger = logging.getLogger("ucircle_qa")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter('%(asctime)s %(levelname)s  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    from logging.handlers import RotatingFileHandler
    
    file_handler = RotatingFileHandler(
        "logs/session.log", 
        maxBytes=5*1024*1024, # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger

logger = setup_logger()
