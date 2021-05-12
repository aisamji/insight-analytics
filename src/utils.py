from time import sleep
from functools import wraps
import logging
import requests


# setup logger
logger = logging.getLogger()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


# Configure requests for exponential backoff
DEFAULT_TIMEOUT = 10
old_send = requests.Session.send


def new_send(*args, **kwargs):
    if kwargs.get("timeout", None) is None:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    return old_send(*args, **kwargs)


requests.Session.send = new_send


def with_backoff(func):
    return with_backoff_condition('True')(func)


def with_backoff_condition(condition):
    def backoff(func):
        @wraps(func)
        def try_request(*args, **kwargs):
            backoff = 5
            response = None
            while True:
                try:
                    response = func(*args, **kwargs)
                    if eval(condition):
                        break
                except requests.exceptions.ConnectTimeout:
                    pass
                logger.info(f'Retrying request in {backoff} seconds.')
                sleep(backoff)
                backoff *= 2
            return response
        return try_request
    return backoff
