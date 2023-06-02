import pytest
import os
from typing import TextIO, Generator, Any
import io
import sys
import errno
from pathlib import Path


if os.name != 'posix':
    raise ValueError(
        f"{sys.platform} is not supported by pytest-output-to-files")


class __Capture:
    def __init__(self, target, line_limit=5000, chunk_size=1 << 16):
        # type: (TextIO, int, int) -> None
        self.__target = target
        self.__old_target_fd = os.dup(target.fileno())
        self.__file_path = None  # type: None | Path
        self.__file = None  # type: None | io.FileIO
        self.__line_limit = line_limit
        self.__buf = memoryview(bytearray(chunk_size))
        self.__active = False

    def resume(self):
        assert self.__file is not None, \
            "resume called without calling start and pause"
        assert not self.active, "resume called without calling pause"
        self.__target.flush()
        os.dup2(self.__file.fileno(), self.__target.fileno())
        self.__active = True

    @property
    def active(self):
        # type: () -> bool
        return self.__active

    @property
    def started(self):
        # type: () -> bool
        return self.__file is not None

    def pause(self):
        assert self.started, "pause called without calling start"
        assert self.active, "pause called without calling resume"
        self.__target.flush()
        os.dup2(self.__old_target_fd, self.__target.fileno())
        self.__active = False

    def start(self, file_path):
        # type: (Path) -> None
        assert not self.started, "start called without calling stop"
        self.__file_path = file_path
        self.__file = file_path.open("wb+", buffering=0)
        self.resume()

    def __read_chunk_at(self, pos, required_len):
        # type: (int, int) -> memoryview
        assert self.__file is not None, "can't be called without file"
        self.__file.seek(pos)
        filled = 0
        while filled < len(self.__buf):
            amount = self.__file.readinto(self.__buf[filled:])
            if amount is None:
                raise BlockingIOError(errno.EAGAIN)
            if amount == 0:
                break
            filled += amount
        if filled < required_len:
            raise ValueError(f"failed to read full {required_len:#x} byte "
                             f"chunk starting at offset {pos:#x}")
        return self.__buf[:filled]

    def __read_lines_at(self, line_limit, pos, backwards):
        # type: (int, int, bool) -> tuple[bytes, bool]
        chunks = []  # type: list[bytes]
        lines = 0
        hit_eof = False
        while lines < line_limit:
            required_len = 0
            if backwards:
                if pos <= 0:
                    hit_eof = True
                    break
                required_len = min(pos, len(self.__buf))
                pos -= required_len
            chunk = bytes(self.__read_chunk_at(pos, required_len))
            if chunk == b"":
                hit_eof = True
                break
            chunks.append(chunk)
            if not backwards:
                pos += len(chunk)
            lines += chunk.count(b"\n")
        extra_lines = lines - line_limit
        if backwards:
            retval = b"".join(reversed(chunks))
            if extra_lines > 0:
                retval = self.__remove_lines_at_start(retval, extra_lines)
            return retval, hit_eof
        retval = b"".join(chunks)
        if extra_lines > 0:
            retval = self.__remove_lines_at_end(retval, extra_lines)
        return retval, hit_eof

    def __remove_lines_at_end(self, b, count):
        # type: (bytes, int) -> bytes
        trim_end = len(b)
        for _ in range(count):
            trim_end = b.rindex(b"\n", None, trim_end)
        return b[:trim_end]

    def __lines_from_start(self, b, count):
        # type: (bytes, int) -> int
        trim_start = 0
        for _ in range(count):
            trim_start = b.index(b"\n", trim_start) + 1
        return trim_start

    def __remove_lines_at_start(self, b, count):
        # type: (bytes, int) -> bytes
        return b[self.__lines_from_start(b, count):]

    def __read_output_str(self):
        # type: () -> str
        assert self.__file is not None, "can't be called without file"
        start_lines, start_hit_eof = self.__read_lines_at(
            line_limit=self.__line_limit * 2, pos=0, backwards=False)
        if start_hit_eof:
            return start_lines.decode("utf-8", errors="replace")
        p = self.__lines_from_start(start_lines, self.__line_limit)
        start_lines = start_lines[:p]
        file_length = self.__file.seek(0, os.SEEK_END)
        end_lines, _ = self.__read_lines_at(
            line_limit=self.__line_limit, pos=file_length, backwards=True)
        hr = '-' * 50
        trimmed_msg = f"Output Trimmed, Full output in: {self.__file_path}"
        retval = [
            trimmed_msg,
            hr,
            start_lines.decode("utf-8", errors="replace"),
            hr,
            trimmed_msg,
            hr,
            end_lines.decode("utf-8", errors="replace"),
            hr,
            trimmed_msg,
        ]
        return "\n".join(retval)

    def abort(self):
        if self.__file is None:
            return
        if self.active:
            self.pause()
        self.__file.close()
        self.__file_path, self.__file = None, None

    def stop(self):
        assert self.__file is not None, "stop called without calling start"
        if self.active:
            self.pause()
        try:
            print(self.__read_output_str(), file=self.__target)
        finally:
            self.abort()
        return


class __OutputToFilesPlugin:
    def __init__(self, output_dir):
        # type: (str) -> None
        self.output_dir = Path(output_dir)
        self.__captures = {
            "stdout.txt": __Capture(sys.stdout),
            "stderr.txt": __Capture(sys.stderr),
        }

    def __repr__(self):
        # type: () -> str
        return f"<OutputToFilesPlugin output_dir={str(self.output_dir)!r}>"

    def __start(self, item):
        # type: (pytest.Item) -> None
        path = self.output_dir
        for part in item.nodeid.split('::'):
            path /= part.replace(".", "_")
        path.mkdir(0o775, parents=True, exist_ok=True)
        for name, capture in self.__captures.items():
            capture.start(path / name)

    @pytest.hookimpl(tryfirst=True)
    def pytest_keyboard_interrupt(self, excinfo):
        for capture in self.__captures.values():
            capture.abort()

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(self, excinfo):
        for capture in self.__captures.values():
            capture.abort()

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_setup(self, item):
        # type: (pytest.Item) -> Generator[Any, Any, Any]
        self.__start(item)
        yield
        for capture in self.__captures.values():
            capture.pause()

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_call(self, item):
        # type: (pytest.Item) -> Generator[Any, Any, Any]
        for capture in self.__captures.values():
            capture.resume()
        yield
        for capture in self.__captures.values():
            capture.pause()

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_teardown(self, item):
        # type: (pytest.Item) -> Generator[Any, Any, Any]
        for capture in self.__captures.values():
            capture.resume()
        yield
        for capture in self.__captures.values():
            capture.stop()


def pytest_addoption(parser):
    # type: (pytest.Parser) -> None
    group = parser.getgroup("output_to_files", "shortening output")
    group.addoption(
        '--shorten-output-dir',
        action='store',
        metavar="DIR",
        default="",
        help=('shorten test outputs by storing them in files in DIR and '
              'returning just the first/last few lines'))

    parser.addini(
        'shorten-output-dir',
        default="",
        help=('shorten test outputs by storing them in files in DIR and '
              'returning just the first/last few lines'))


def pytest_configure(config):
    # type: (pytest.Config) -> None
    output_dir = config.getoption('--shorten-output-dir')
    if output_dir == "":
        output_dir = config.getini('shorten-output-dir')
    if output_dir != "":
        assert isinstance(output_dir, str), "invalid shorten-output-dir"
        config.pluginmanager.register(__OutputToFilesPlugin(output_dir))
