import logging

def setup_logger(logger):
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    fi = logging.FileHandler("ext-mount/logs/logs.txt")
    fi.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(fi)
    logger.addHandler(ch)