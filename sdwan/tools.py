import errno
import functools
import subprocess
import threading
import logging
import inspect
import json
import sys
import time
import os
from typing import TextIO, Union
from datetime import datetime, timezone, timedelta


class CallState(threading.local):
    def __init__(self):
        self.frames = []
        self.depth = 0
        self.current_func = None


call_state = CallState()
_logger_cache = {}  # cache loggers per class
log_root = ""


def set_log_root(path):
    global log_root
    log_root = path


class ThreadRegistry:
    def __init__(self):
        self.lock = threading.Lock()
        self.registry = {}
        self.counter = 0

    def get_thread_index(self):
        tid = threading.get_ident()

        if tid in self.registry:
            return self.registry[tid]["index"]

        with self.lock:
            if tid not in self.registry:
                self.registry[tid] = {
                    "index": self.counter,
                    "name": threading.current_thread().name,
                }
                self.counter += 1

            return self.registry[tid]["index"]

    def dump_threads(self):
        return {v: k for k, v in self.registry.items()}


thread_registry = ThreadRegistry()


def _mkpath(path):
    try:
        os.makedirs(path)
    except OSError as ex:
        if ex.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def _get_logger_for_class(cls):
    name = cls.__name__

    if name in _logger_cache:
        return _logger_cache[name]

    logger = logging.getLogger(f"call_tree.{name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # avoid duplicate logs

    if not logger.handlers:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        if log_root:
            fh = logging.FileHandler(f"{log_root}/{name}_{ts}.html", encoding="utf-8")
        else:
            fd = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            _mkpath(fd)
            fh = logging.FileHandler(
                f"/home/tester/vtest/tests/logs/{fd}/{name}_{ts}.html",
                encoding="utf-8",
            )
        formatter = logging.Formatter("%(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info('<meta charset="UTF-8"><pre>')
        logger.info(f" [{ts}] - [{name}]")

    _logger_cache[name] = logger
    return logger


def log_methods_tree(cls):

    def format_prefix(frames):
        prefix = ""
        for frame in frames[:-1]:
            prefix += "    " if frame["is_last"] else "│   "
        if frames:
            prefix += "└── " if frames[-1]["is_last"] else "├── "
        return prefix

    def try_parse_json(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    def format_value(val, max_args=10, max_len=80):
        val = try_parse_json(val)

        if isinstance(val, dict):
            lst = []
            for i, (k, v) in enumerate(val.items()):
                if i >= max_args:
                    lst.append("...")
                    break
                lst.append(f"{k}={format_value(v, max_args)}")
            items = ", ".join(lst)
            return f"{{{items}}}"

        s = repr(val)
        return s if len(s) <= max_len else s[:max_len] + "..."

    def build_arg_string(func, args, kwargs, max_args=10):
        if func.__name__ in [
            "check_key",
            "dump_cloud_init",
            "update_sdwan_init_machine_password",
            "cloud_init_is_hw",
        ]:
            max_args = 2
        sig = inspect.signature(func)

        try:
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
        except Exception:
            return f"args={args}, kwargs={kwargs}"

        parts = []
        for name, val in bound.arguments.items():
            if name == "self":
                continue

            val = try_parse_json(val)

            if isinstance(val, dict):
                for i, (k, v) in enumerate(val.items()):
                    if i >= max_args:
                        parts.append("...")
                        break
                    parts.append(f"{k}={format_value(v, max_args)}")
            else:
                parts.append(f"{name}={format_value(val, max_args)}")

        return ", ".join(parts)

    for attr_name, attr_value in cls.__dict__.items():

        if not callable(attr_value):
            continue

        if attr_name.startswith("__") and attr_name.endswith("__"):
            continue

        def make_wrapper(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                frames = call_state.frames

                if frames:
                    frames[-1]["is_last"] = False

                frame = {"is_last": True}
                frames.append(frame)
                call_state.depth += 1
                prefix = format_prefix(frames)

                arg_str = build_arg_string(func, args, kwargs)

                logger = _get_logger_for_class(cls)
                ts = datetime.now(timezone.utc).strftime("%H:%M:%S,%f")[:-3]
                thread_id = thread_registry.get_thread_index()
                thread_str = "MAIN" if thread_id == 0 else f"{thread_id:04}"
                logger.info(
                    f"{ts} [{thread_str}] [{call_state.depth:02d}] {prefix}{cls.__name__}.{func.__name__}({arg_str})"
                )

                call_state.current_func = func.__name__

                try:
                    return func(*args, **kwargs)
                finally:
                    frames.pop()
                    call_state.depth -= 1

            return wrapper

        setattr(cls, attr_name, make_wrapper(attr_value))

    return cls


class TimestampedLogger:
    def __init__(self, stream: TextIO):
        self._stream = stream
        self._buffer = ""  # holds partial line

    def write(self, data: Union[str, bytes]) -> int:
        if not data:
            return 0

        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="ignore")

        data = data.replace("\r", "\n").replace("\n\n", "\n").replace("\n\n", "\n")
        self._buffer += data
        total_written = 0

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            written = self._stream.write(f"\n[{ts}]  {line}")
            total_written += written if written else 0

        self._stream.flush()
        return total_written

    def flush(self) -> None:
        # flush remaining partial line (optional behavior)
        if self._buffer:
            # ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            # self._stream.write(f"[{ts}]  {self._buffer}\n")
            self._stream.write(f"{self._buffer}")
            self._buffer = ""
        self._stream.flush()

    def fileno(self):
        if hasattr(self._stream, "fileno"):
            return self._stream.fileno()
        raise OSError("Underlying stream does not support fileno()")

    def close(self) -> None:
        self.flush()
        if self._stream not in (sys.stdout, sys.stderr):
            self._stream.close()

    @property
    def closed(self) -> bool:
        return getattr(self._stream, "closed", False)


def notify_user_by_webex(
    status,
    suite_name,
    webex_id,
    start_time,
    db_build_id,
    tb_hostname,
    test_stats,
    db_test_suite_result,
):
    if not webex_id:
        print(f"No webex_id set in preference!")
        return

    if not isinstance(webex_id, str):
        print(f"Invalid webex_id format: {webex_id}")
        return

    run_time = int(time.time() - start_time)
    print(f"notify_user_by_webex to: {webex_id}, status: {status}, suite: {suite_name}")
    txt = f"db_build_id: {db_build_id}|Host Name: {tb_hostname}|"
    if status == "start":
        txt += f"Start to run: {suite_name}"
    elif status == "stop":
        stats = test_stats.replace("\n", "|")
        txt += f"Suite Name: {suite_name}|{stats}"
        txt += f"|Suite Result: {db_test_suite_result}"
        txt += f"|Suite Duration: {str(timedelta(seconds=run_time))}"
    elif status in ["scheduled", "passed", "failed to pass"]:
        txt += f"{str.capitalize(status)}: {suite_name}"
    else:
        txt += f"{suite_name}: {status}"

    # --------------------------------------------------------------------
    # workaround for:
    # 1, compatibility issue with pygithub
    # 2, HTTPS_PROXY
    # --------------------------------------------------------------------
    # subprocess.run("notify_bot", check=True)
    # subprocess.run(["./myscript.sh", "arg1", "arg2", "--flag"], check=True)
    result = subprocess.run(
        ["/home/tester/bin/notify_bot", webex_id, txt],
        capture_output=True,  # gets stdout + stderr
        text=True,  # get strings instead of bytes
        check=True,  # raise exception if exit code ≠ 0
    )

    print("Output: " + result.stdout)
    print("Errors:" + result.stderr)
    print(f"Exit code: {result.returncode}")

    # api = WebexTeamsAPI(
    #     access_token="ZmNmM2M2MzktNTEzMy00N2VhLTgzOWMtNDE0N2E3NmRjYmE5Y2I5OTVmNDgtMGE5_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f"
    # )
    # if person.count('@'):
    #     api.messages.create(toPersonEmail=person, text=txt)
    # else:
    #     api.messages.create(
    #         # roomId="c582edc0-3443-11ef-a59e-497ab6833a4a", text=txt
    #         roomId="306d3220-eadd-11f0-8ed5-e7669d71f2e3", text=txt
    #     )
