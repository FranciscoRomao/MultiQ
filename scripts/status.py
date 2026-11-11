"""Status output for the evaluation: short progress lines on the terminal, everything else in a log file."""
import contextlib
import os
import sys
import time

# Original terminal while output is redirected to a log, None otherwise.
_terminal = None


def status(msg):
    out = _terminal or sys.stdout
    out.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    out.flush()


def step(compiler, i, n, what):
    status(f"  {compiler:<10} [{i:>{len(str(n))}}/{n}] {what}")


def warn(compiler, msg):
    status(f"  {compiler:<10} WARNING: {msg}")


@contextlib.contextmanager
def output_to_log(log_path):
    """Redirect stdout and stderr at the file-descriptor level, so compiler, C++ and subprocess output also go to the log."""
    global _terminal
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out, saved_err = os.dup(1), os.dup(2)
    log = open(log_path, "a")
    _terminal = os.fdopen(os.dup(saved_out), "w")
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)
    # Keep Python output in order with subprocess output in the log.
    sys.stdout.reconfigure(line_buffering=True)
    try:
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)
        _terminal.close()
        _terminal = None
        log.close()
