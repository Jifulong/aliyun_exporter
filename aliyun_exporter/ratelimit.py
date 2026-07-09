import threading
import time
from collections import deque

'''
Minimal drop-in replacement for the abandoned `ratelimiter` PyPI package,
which calls `asyncio.coroutine` and no longer imports on Python 3.11+.
Same semantics: a context manager that blocks callers so that no more than
`max_calls` occur within any rolling `period` seconds.
'''
class RateLimiter(object):
    def __init__(self, max_calls, period=1.0):
        if max_calls <= 0:
            raise ValueError('max_calls must be greater than 0')
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = threading.Lock()

    def __enter__(self):
        with self.lock:
            self._pop_expired()
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (time.time() - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self._pop_expired()
            self.calls.append(time.time())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def _pop_expired(self):
        threshold = time.time() - self.period
        while self.calls and self.calls[0] <= threshold:
            self.calls.popleft()
