#!/usr/bin/python3
"""Helpers shared by the privileged writer scripts.

ImageWriter.py and ISOCopier.py both talk to MainWindow through a progress
protocol on stdout, so every diagnostic has to go to stderr, both run external
commands without a shell, and both end a cancelled run the same way.

The stop flag lives here as well: a signal handler only records the request,
and the writers decide where it is safe to act on it. The same flag is raised
when the GUI closes the pipe it holds on stdin, which is how a cancel arrives
now that no polkit action for kill is shipped any more.
"""

import os
import pwd
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time

_stop_signal = 0


class CancelledError(Exception):
    """The user asked to stop, the run has to unwind and clean up."""


def request_stop(number=signal.SIGTERM):
    """Record a stop request. Safe to call from a signal handler."""
    global _stop_signal
    _stop_signal = number


def stop_requested():
    """True once a stop signal has been received."""
    return _stop_signal != 0


def log(message: str) -> None:
    """Write a diagnostic line. stdout belongs to the progress protocol."""
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()


def fail(message: str) -> None:
    """Report an error and exit with 1, which MainWindow shows as a failure."""
    log(f"Error: {message}")
    sys.exit(1)


def caller_uid():
    """Return the uid of the user that invoked pkexec, or None.

    pkexec exports PKEXEC_UID, so a script started through it can tell who
    asked for the work even though it runs as root. None means the script was
    started as root some other way, and then there is nobody to drop to.
    """
    value = os.environ.get("PKEXEC_UID", "")
    if not value.isdigit():
        return None

    uid = int(value)
    if uid == 0:
        return None

    return uid


def open_as_caller(path, flags):
    """Open a path with the credentials of the user that invoked pkexec.

    Both writers run as root, so without this they would happily open any file
    on the machine and copy it onto a USB disk the caller owns. A write is only
    ever meant to be started for a file the caller could have read themselves,
    and the kernel is the only thing that can decide that reliably, so the
    effective credentials are dropped around the open instead of the path being
    inspected.

    The real uid stays 0 and the saved uid is set to 0, which is what makes the
    restore below possible. Supplementary groups are set too, otherwise a file
    the caller reaches through a group would be rejected.
    """
    uid = caller_uid()
    if uid is None or os.geteuid() != 0:
        return os.open(path, flags)

    try:
        entry = pwd.getpwuid(uid)
        groups = os.getgrouplist(entry.pw_name, entry.pw_gid)
    except KeyError:
        raise PermissionError(f"Unknown calling user id {uid}.")

    saved_groups = os.getgroups()
    try:
        os.setgroups(groups)
        os.setresgid(-1, entry.pw_gid, 0)
        os.setresuid(-1, uid, 0)

        return os.open(path, flags)
    finally:
        os.setresuid(-1, 0, 0)
        os.setresgid(-1, 0, 0)
        os.setgroups(saved_groups)


def watch_stdin_for_cancel(on_cancel=None):
    """Raise the stop flag when the GUI closes the pipe it holds on stdin.

    The GUI runs as the user and cannot signal a process that runs as root.
    Shipping a polkit action for kill would solve that, but such an action lets
    any caller kill any process as root once the prompt is answered, so the
    cancel travels through a pipe instead: the GUI closes its end, the read
    below returns end of file and the writer stops itself at a point where the
    disk is in a consistent state.

    Only a pipe is watched. Started from a terminal stdin is a tty and the read
    would block until the run ends, and redirected from /dev/null it would
    report end of file straight away and cancel a run nobody cancelled.
    """
    try:
        if not stat.S_ISFIFO(os.fstat(0).st_mode):
            return
    except OSError:
        return

    def wait_for_close():
        try:
            while os.read(0, 4096):
                pass
        except OSError:
            pass

        request_stop(signal.SIGTERM)
        if on_cancel is not None:
            on_cancel()

    threading.Thread(target=wait_for_close, daemon=True).start()


def run(cmd, vital=True):
    """Run a command without a shell, aborting if a stop signal arrived.

    A shell is never involved, so a device path or a file name can not turn
    into extra commands. With vital=True a non zero exit raises
    CalledProcessError.
    """
    if stop_requested():
        raise CancelledError()

    subprocess.run(cmd, check=vital)


def sync():
    run(["sync"])


def settle():
    """Wait for udev to catch up with a partition table that just changed.

    parted returns as soon as the kernel accepted the new table, but the device
    node of a partition is created by udev afterwards. Without this wait mkfs
    and mount race against that creation.
    """
    udevadm = shutil.which("udevadm")
    if udevadm is None:
        log("Warning: udevadm command not found.")
        return

    subprocess.run(
        [udevadm, "settle", "--timeout=30"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_block_device(path, timeout=15.0):
    """Wait until a partition device node exists. Returns whether it showed up.

    'udevadm settle' already covers the normal case; this is the fallback for
    the systems where udev is slow or not running at all.
    """
    deadline = time.monotonic() + timeout

    while not os.path.exists(path):
        if stop_requested():
            raise CancelledError()
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.2)

    return True


def exit_as_cancelled():
    """Die by SIGTERM so MainWindow sees a cancellation instead of an error.

    The default handler has to be restored first, otherwise the process would
    only record the stop request again and keep running.
    """
    log("---Writing stopped---")
    sys.stdout.flush()
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    os.kill(os.getpid(), signal.SIGTERM)
    sys.exit(1)  # not reached, the signal above ends the process


SUPPORTED_HASH_ALGORITHMS = ("md5", "sha256", "sha512")
HASH_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB buffer for high performance

SUPPORTED_COMPRESSION_FORMATS = ("xz", "gz", "zst", "zstd", "bz2")
SUPPORTED_IMAGE_EXTENSIONS = (
    ".iso", ".img", ".raw",
    ".iso.xz", ".img.xz", ".raw.xz", ".xz",
    ".iso.gz", ".img.gz", ".raw.gz", ".gz",
    ".iso.zst", ".img.zst", ".raw.zst", ".zst", ".zstd",
    ".iso.bz2", ".img.bz2", ".raw.bz2", ".bz2",
)


def calculate_hash(filepath, algorithm="sha256"):
    """Compute hash of a file using md5, sha256 or sha512 with a 4 MiB buffer."""
    import hashlib

    algo = algorithm.lower()
    if algo not in SUPPORTED_HASH_ALGORITHMS:
        raise ValueError("Unsupported hash algorithm: {}".format(algorithm))

    hasher = hashlib.new(algo)
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def detect_hash_type(hash_str):
    """Detect whether a hex hash is md5, sha256 or sha512 based on length."""
    h = hash_str.strip().lower()
    if len(h) == 32:
        return "md5"
    elif len(h) == 64:
        return "sha256"
    elif len(h) == 128:
        return "sha512"
    return None


def detect_compression(filepath):
    """Detect compression format ('xz', 'gz', 'zst', 'bz2') by magic bytes or extension."""
    try:
        with open(filepath, "rb") as f:
            magic = f.read(6)
            if magic.startswith(b"\x1f\x8b"):
                return "gz"
            elif magic.startswith(b"\xfd7zXZ\x00"):
                return "xz"
            elif magic.startswith(b"\x28\xb5\x2f\xfd"):
                return "zst"
            elif magic.startswith(b"BZh"):
                return "bz2"
    except OSError:
        pass

    lower = filepath.lower()
    if lower.endswith(".xz"):
        return "xz"
    elif lower.endswith(".gz"):
        return "gz"
    elif lower.endswith(".zst") or lower.endswith(".zstd"):
        return "zst"
    elif lower.endswith(".bz2"):
        return "bz2"

    return None


def get_uncompressed_size(filepath, comp_type=None):
    """Attempt to detect uncompressed image size in bytes without full extraction."""
    if comp_type is None:
        comp_type = detect_compression(filepath)
    if not comp_type:
        try:
            return os.path.getsize(filepath)
        except OSError:
            return None

    if comp_type == "xz":
        xz_bin = shutil.which("xz")
        if xz_bin:
            try:
                res = subprocess.run(
                    [xz_bin, "--robot", "-l", filepath],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        parts = line.strip().split("\t")
                        if len(parts) >= 5 and parts[0] == "totals":
                            if parts[4].isdigit():
                                return int(parts[4])
            except Exception:
                pass

    elif comp_type in ("zst", "zstd"):
        try:
            import zstandard
            with open(filepath, "rb") as f:
                header = f.read(1024)
                size = zstandard.frame_content_size(header)
                if size and size > 0:
                    return size
        except Exception:
            pass

        zstd_bin = shutil.which("zstd")
        if zstd_bin:
            try:
                res = subprocess.run(
                    [zstd_bin, "-l", filepath],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        parts = line.split()
                        for p in parts:
                            if p.isdigit() and int(p) > 1024 * 1024:
                                return int(p)
            except Exception:
                pass

    elif comp_type == "gz":
        try:
            with open(filepath, "rb") as f:
                f.seek(-4, os.SEEK_END)
                import struct
                isize = struct.unpack("<I", f.read(4))[0]
                if isize > 0:
                    return isize
        except Exception:
            pass

    return None


def open_decompressed_stream(raw_file, comp_type):
    """Wrap a binary readable file object in an on-the-fly streaming decompressor."""
    if comp_type == "xz":
        import lzma
        return lzma.open(raw_file, "rb")
    elif comp_type == "gz":
        import gzip
        return gzip.open(raw_file, "rb")
    elif comp_type == "bz2":
        import bz2
        return bz2.open(raw_file, "rb")
    elif comp_type in ("zst", "zstd"):
        try:
            import zstandard
            dctx = zstandard.ZstdDecompressor()
            return dctx.stream_reader(raw_file)
        except ImportError:
            zstd_bin = shutil.which("zstd")
            if zstd_bin:
                proc = subprocess.Popen(
                    [zstd_bin, "-dc"],
                    stdin=raw_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=4 * 1024 * 1024,
                )
                return proc.stdout
            raise RuntimeError("Zstandard desteği için 'zstandard' modülü veya 'zstd' komutu gereklidir.")

    return raw_file

