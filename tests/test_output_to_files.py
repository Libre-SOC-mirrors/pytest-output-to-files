import pytest
import sys
from pathlib import Path
from pytest_output_to_files import _DEFAULT_LINE_LIMIT


def test_help_message(testdir):
    # type: (pytest.Testdir) -> None
    result = testdir.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'shortening output:',
        '*--shorten-output-dir=DIR*',
        '*shorten test outputs by storing them in files in DIR and*',
        '*returning just the first/last few lines. disable by*',
        '*using --shorten-output-dir=""*',
    ])


def do_stdout_stderr_check(testdir, additional_args, stdout_lines,
                           stderr_lines, enabled):
    # type: (pytest.Testdir, list[str], int, int, bool) -> pytest.RunResult
    testdir.makepyfile(test_print=f"""
        import sys

        def test_print():
            for i in range({stdout_lines}):
                print(f'in stdout {{i}}')
            for i in range({stderr_lines}):
                print(f'in stderr {{i}}', file=sys.stderr)
            assert False
    """)

    full_stdout = ''.join(f'in stdout {i}\n' for i in range(stdout_lines))
    full_stderr = ''.join(f'in stderr {i}\n' for i in range(stderr_lines))

    result = testdir.runpytest('-v', *additional_args)

    test_out_path = Path(testdir.tmpdir)
    test_out_path /= "test-out"
    test_print_path = test_out_path / "test_print_py"
    test_print_path /= "test_print"
    call_stdout_path = test_print_path / "call-stdout.txt"
    call_stderr_path = test_print_path / "call-stderr.txt"

    lines = ['*--- Captured stdout call ---*']
    hr = '-' * 50
    if enabled and stdout_lines >= 2 * _DEFAULT_LINE_LIMIT:
        trimmed_msg = ("Output Trimmed, Full output in: "
                       "test-out/test_print_py/test_print/call-stdout.txt")
        lines.append(trimmed_msg)
        lines.append(hr)
        for i in range(_DEFAULT_LINE_LIMIT):
            lines.append(f'in stdout {i}')
        lines.append(hr)
        lines.append(trimmed_msg)
        lines.append(hr)
        for i in range(stdout_lines - _DEFAULT_LINE_LIMIT, stdout_lines):
            lines.append(f'in stdout {i}')
        lines.append(hr)
        lines.append(trimmed_msg)
    else:
        for i in range(stdout_lines):
            lines.append(f'in stdout {i}')
    lines.append('*--- Captured stderr call ---*')
    if enabled and stderr_lines >= 2 * _DEFAULT_LINE_LIMIT:
        trimmed_msg = ("Output Trimmed, Full output in: "
                       "test-out/test_print_py/test_print/call-stderr.txt")
        lines.append(trimmed_msg)
        lines.append(hr)
        for i in range(_DEFAULT_LINE_LIMIT):
            lines.append(f'in stderr {i}')
        lines.append(hr)
        lines.append(trimmed_msg)
        lines.append(hr)
        for i in range(stderr_lines - _DEFAULT_LINE_LIMIT, stderr_lines):
            lines.append(f'in stderr {i}')
        lines.append(hr)
        lines.append(trimmed_msg)
    else:
        for i in range(stderr_lines):
            lines.append(f'in stderr {i}')
    lines.append("*====*")

    result.stdout.fnmatch_lines(lines, consecutive=True)

    result.stdout.fnmatch_lines([
        'FAILED test_print.py::test_print *',
    ])

    if enabled:
        for empty_file in ("setup-stdout.txt", "setup-stderr.txt",
                           "teardown-stdout.txt", "teardown-stderr.txt"):
            assert (test_print_path / empty_file).read_text("utf-8") == ""
        assert call_stdout_path.read_text("utf-8") == full_stdout
        assert call_stderr_path.read_text("utf-8") == full_stderr
        call_stdout_path.unlink()  # remove big files
        call_stderr_path.unlink()  # remove big files
    else:
        assert not test_out_path.exists()
    assert result.ret != 0

    return result


def test_ini_setting(testdir):
    # type: (pytest.Testdir) -> None
    testdir.makeini("""
        [pytest]
        shorten-output-dir = test-out
    """)

    do_stdout_stderr_check(testdir, [], 1, 1, True)


def test_nothing(testdir):
    # type: (pytest.Testdir) -> None
    do_stdout_stderr_check(testdir, [], 1, 1, False)


def test_arg(testdir):
    # type: (pytest.Testdir) -> None
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], 1, 1, True)


def test_arg_override_ini(testdir):
    # type: (pytest.Testdir) -> None
    testdir.makeini("""
        [pytest]
        shorten-output-dir = test-out
    """)

    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir="], 1, 1, False)


def test_disable_capture(testdir):
    # type: (pytest.Testdir) -> None
    testdir.makeini("""
        [pytest]
        shorten-output-dir = test-out
    """)

    testdir.makepyfile(test_print=f"""
        import sys

        def test_print():
            print(f'in stdout')
            print(f'in stderr', file=sys.stderr)
            assert False
    """)

    result = testdir.runpytest('-v', '-s')

    test_out_path = Path(testdir.tmpdir)
    test_out_path /= "test-out"

    assert not test_out_path.exists()

    result.stdout.fnmatch_lines(['test_print.py::test_print*in stdout'])
    result.stderr.fnmatch_lines(['in stderr'])

    assert result.ret != 0


def test_20k_disabled(testdir):
    # type: (pytest.Testdir) -> None
    do_stdout_stderr_check(testdir, [], 20000, 20000, False)


def test_20k(testdir):
    # type: (pytest.Testdir) -> None
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], 20000, 20000, True)


def test_21k(testdir):
    # type: (pytest.Testdir) -> None
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], 21000, 21000, True)


def test_22k(testdir):
    # type: (pytest.Testdir) -> None
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], 22000, 22000, True)


def test_1x(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_50_percent_more(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT + _DEFAULT_LINE_LIMIT // 2
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_2x_minus_two(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT * 2 - 2
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_2x_minus_one(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT * 2 - 1
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_2x(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT * 2
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_2x_plus_one(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT * 2 + 1
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_2x_plus_two(testdir):
    # type: (pytest.Testdir) -> None
    lines = _DEFAULT_LINE_LIMIT * 2 + 2
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


def test_1M(testdir):
    # type: (pytest.Testdir) -> None
    lines = 1_000_000
    do_stdout_stderr_check(
        testdir, ["--shorten-output-dir=test-out"], lines, lines, True)


if __name__ == "__main__":
    sys.exit(pytest.main())
