import os
from threading import Timer

from windrecorder.exceptions import LockExistsException


class FileLock:
    """
    1. 创建 `FileLock` 类的实例来管理文件锁：
    ````python
    lock = FileLock(path, value="", timeout_s: int | None = 60 * 16)
    ```
    - `path`：锁存放的文件路径。
    - `value`：文件中要写入的内容（可选，默认为空）。
    - `timeout_s`：超时后释放锁的时间（以秒为单位）（可选，默认为 16 分钟，即 60 * 16 秒）。

    2. 进入文件锁的上下文管理器：
    ````python
    with lock:
        # 在此处执行需要保护的代码
    ```
    在 `with` 语句块中，您可以执行需要在文件锁保护下运行的代码。当退出 `with` 块时，文件锁将自动释放。

    3. 手动释放文件锁：
    ````python
    lock.release()
    ```
    如果您希望在 `with` 语句块之外手动释放文件锁，可以调用 `release()` 方法。
    注意事项：
    - 如果文件锁已存在（即文件已存在），将引发 `LockExistsException` 异常。
    - 文件锁在创建时会将指定的值写入文件中。
    - 如果指定了超时时间 (`timeout_s`)，则在超过该时间后，文件锁将自动释放并删除锁定的文件。
    """

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
