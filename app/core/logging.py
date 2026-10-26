import logging
import sys
from app.core.config import get_settings


def configurar_logging() -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger("agregador_resiliente")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formato = logging.Formatter(
        fmt="[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    consola_handler = logging.StreamHandler(sys.stdout)
    consola_handler.setFormatter(formato)

    archivo_handler = logging.FileHandler(
        settings.log_file, mode="a", encoding="utf-8"
    )
    archivo_handler.setFormatter(formato)

    logger.addHandler(consola_handler)
    logger.addHandler(archivo_handler)
    logger.propagate = False
    return logger


logger = configurar_logging()
