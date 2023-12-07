import os
from threading import Timer

from windrecorder.exceptions import LockExistsException


class FileLock:
    def __init__(self, path, value="", timeout_s: int | None = 60 * 16):
        try:
            with open(path, "x", encoding="utf-8") as f:
                f.write(value)
        except FileExistsError:
            raise LockExistsException
        self.path = path
        self.timeout_timer = None
        if timeout_s:
            self.timeout_timer = Timer(timeout_s, os.remove, [path])
            self.timeout_timer.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.release()

    def release(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        if self.timeout_timer:
            self.timeout_timer.cancel()
