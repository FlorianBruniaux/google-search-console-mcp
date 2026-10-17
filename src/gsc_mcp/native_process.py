"""Bound native-host streams and regular-file writes on Linux and macOS.

The launcher runs in a fresh interpreter before exec, never a threaded
parent's preexec_fn. This is a resource limit, not a hostile-code sandbox.
"""
from contextlib import ExitStack
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time


MAX_NATIVE_OUTPUT_BYTES = 2_000_000
MAX_NATIVE_STATE_BYTES = 16_000_000


def _kill_group(child):
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_bounded(command, *, input_bytes, cwd, output_path, timeout,
                limit=MAX_NATIVE_OUTPUT_BYTES, regular_file_limit=None, stderr_path=None):
    """Return bounded stdout; independently limit streams and regular-file writes.

    stderr is discarded unless an exclusive private capture path is supplied.
    A larger session-file allowance does not increase accepted output bytes.
    It is a per-file resource limit, not an aggregate disk quota.

    Only the direct child can be reaped here. Its ordinary descendants inherit
    its process group and file ceiling; explicitly detached groups are outside
    this cleanup contract. No unbounded communicate() or disk log is used.
    """
    if sys.platform not in {'darwin', 'linux'}:
        raise RuntimeError('Native host unavailable: unsupported platform for output limits')
    file_limit = limit if regular_file_limit is None else regular_file_limit
    if type(limit) is not int or limit < 1 or type(file_limit) is not int or file_limit < 1:
        raise ValueError('Native byte ceilings must be positive integers')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Native timeout must be positive and finite')
    output_path = Path(output_path)
    deadline = time.monotonic() + timeout
    launcher = [sys.executable, '-I', str(Path(__file__).resolve()), str(file_limit), *command]
    captured = bytearray()
    counts = {'stdout': 0, 'stderr': 0}
    # A bounded source file avoids blocking on stdin while the host fills pipes.
    with ExitStack() as resources, tempfile.TemporaryFile(dir=cwd) as source, selectors.DefaultSelector() as selector:
        diagnostic = None
        if stderr_path is not None:
            fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            diagnostic = resources.enter_context(os.fdopen(fd, 'wb'))
        source.write(input_bytes)
        source.seek(0)
        try:
            child = subprocess.Popen(launcher, stdin=source, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=cwd, start_new_session=True,
                env={**os.environ, 'GSC_NO_BROWSER': '1'})
        except OSError as exc:
            raise RuntimeError(f'Native host unavailable: {type(exc).__name__}') from None
        group_stopped = False
        try:
            for name, stream in (('stdout', child.stdout), ('stderr', child.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while True:
                if output_path.exists() and output_path.stat().st_size >= limit:
                    raise ValueError('Native output byte budget exceeded')
                returncode = child.poll()
                if returncode is not None and not group_stopped:
                    # Descendants must not outlive a completed native invocation,
                    # including those keeping the stdout/stderr pipes open.
                    _kill_group(child)
                    group_stopped = True
                if returncode is not None and not selector.get_map():
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError('Native host unavailable: TimeoutExpired')
                for key, _ in selector.select(min(remaining, 0.05)):
                    chunk = os.read(key.fd, min(65536, limit + 1 - counts[key.data]))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    counts[key.data] += len(chunk)
                    if counts[key.data] > limit:
                        raise ValueError('Native output byte budget exceeded')
                    if key.data == 'stdout':
                        captured.extend(chunk)
                    elif diagnostic is not None:
                        diagnostic.write(chunk)
            if returncode == -signal.SIGXFSZ:
                raise ValueError('Native regular-file byte budget exceeded')
            if returncode:
                raise RuntimeError(f'Native host unavailable: exit {returncode}')
            return bytes(captured)
        finally:
            if not group_stopped:
                _kill_group(child)
            child.wait()
            child.stdout.close()
            child.stderr.close()


def _exec_limited():
    import resource
    limit = int(sys.argv[1])
    for inherited in resource.getrlimit(resource.RLIMIT_FSIZE):
        if inherited != resource.RLIM_INFINITY:
            limit = min(limit, inherited)
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
    os.execvpe(sys.argv[2], sys.argv[2:], os.environ)


if __name__ == '__main__':
    try:
        _exec_limited()
    except (ImportError, OSError, ValueError):
        # Never include host arguments, filesystem paths or source text in errors.
        sys.exit(125)
