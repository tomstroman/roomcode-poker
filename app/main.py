import logging
import time

from fastapi import FastAPI

from app.api import router

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s.%(msecs)03dZ [%(filename)s:%(lineno)d] "
        "%(levelname)s - %(message)s"
    ),
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger()
logger.info("Starting up")
fastapi_app = FastAPI()
fastapi_app.include_router(router)
