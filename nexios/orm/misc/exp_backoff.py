import time


def exponential_backoff(retry_delay: float, attempt: int) -> float:
    return time.sleep(retry_delay * (2 ** (attempt - 1))) # type: ignore