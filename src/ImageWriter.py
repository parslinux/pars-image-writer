#!/usr/bin/python3
"""Raw (dd style) image writer for Pars Image Writer.

This script is executed as root through pkexec, so every input coming from the
GUI is treated as untrusted and validated again here. The drive validation
itself lives in USBDeviceManager and is shared with ISOCopier.py.

stdout is a machine readable progress stream consumed by MainWindow:
one "<written_bytes> <total_bytes>" line per update, nothing else.
All diagnostics go to stderr.

Exit codes:
    0   image written successfully
    1   validation or I/O error
    killed by SIGTERM when the user cancels (MainWindow expects this)
"""

import os
import shutil
import signal
import stat
import subprocess
import sys

from USBDeviceManager import DriveError, open_drive_exclusive, validate_usb_drive
from USBDeviceManager import unmount_drive
from Utils import (
    detect_compression,
    exit_as_cancelled,
    fail,
    get_uncompressed_size,
    log,
    open_as_caller,
    open_decompressed_stream,
    request_stop,
    stop_requested,
    watch_stdin_for_cancel,
)

BUFFER_SIZE = 4 * 1024 * 1024  # 4 MiB read/write chunk


def receive_stop_signal(number, frame):
    request_stop(number)


def open_image_file(filepath):
    """Open the image read-only and make sure it is a usable regular file.

    The open runs with the credentials of the user that invoked pkexec. This
    process is root and could otherwise be pointed at any file on the machine,
    and copying /etc/shadow onto a USB disk is not what the person answering
    the authentication prompt agreed to.

    O_NONBLOCK keeps the open from hanging forever on a FIFO or on a device
    node, and the type is checked on the descriptor itself, so the file cannot
    be swapped between the check and the read.

    Supports automatic streaming decompression for .xz, .gz, .zst, and .bz2 files.
    """
    open_flags = os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC
    try:
        file_descriptor = open_as_caller(filepath, open_flags)
    except OSError as error:
        fail("Could not open the image file: {}".format(error))

    file_info = os.fstat(file_descriptor)
    if not stat.S_ISREG(file_info.st_mode):
        os.close(file_descriptor)
        fail("{} is not a regular file.".format(filepath))

    # O_NONBLOCK has no meaning for regular files, but do not leave it set.
    os.set_blocking(file_descriptor, True)
    image_file = os.fdopen(file_descriptor, "rb")

    if file_info.st_size == 0:
        image_file.close()
        fail("{} is empty.".format(filepath))

    # Check for compressed formats (.xz, .gz, .zst, .bz2)
    comp_type = detect_compression(filepath)
    if comp_type:
        log(f"Compressed image detected ({comp_type.upper()}). Streaming decompress active.")
        uncompressed_size = get_uncompressed_size(filepath, comp_type)
        try:
            stream = open_decompressed_stream(image_file, comp_type)
        except Exception as err:
            image_file.close()
            fail(f"Akış açma motoru başlatılamadı: {err}")

        total_bytes = uncompressed_size if (uncompressed_size and uncompressed_size > 0) else file_info.st_size
        return stream, total_bytes, comp_type

    return image_file, file_info.st_size, None


def write_image(image_file, drive_files, total_bytes):
    """Copy the image onto the drive(s), reporting progress on stdout.

    The drives are opened with O_DSYNC, so every write only returns once the data
    is on the stick. When multiple target drives are provided, chunks are written
    in broadcast mode to all drives simultaneously with per-device fault isolation.
    """
    written_bytes = 0
    active_drives = list(drive_files)
    failed_drives = []

    print(f"0 {total_bytes}")
    sys.stdout.flush()

    while not stop_requested():
        chunk = image_file.read(BUFFER_SIZE)
        if not chunk:
            break

        # Broadcast write chunk with per-drive fault isolation
        for drive_file in list(active_drives):
            try:
                drive_file.write(chunk)
                drive_file.flush()
            except OSError as err:
                d_name = getattr(drive_file, "_target_drive", "drive")
                log(f"Write error on {d_name}: {err}. Removing from active broadcast.")
                try:
                    drive_file.close()
                except Exception:
                    pass
                active_drives.remove(drive_file)
                failed_drives.append(drive_file)

        if not active_drives:
            raise OSError("All target drives encountered I/O write failures.")

        written_bytes += len(chunk)

        if total_bytes > 0 and written_bytes > total_bytes:
            total_bytes = written_bytes

        print(f"{written_bytes} {total_bytes}")
        sys.stdout.flush()

    if stop_requested():
        return False

    for drive_file in list(active_drives):
        try:
            drive_file.flush()
            os.fsync(drive_file.fileno())
        except OSError as err:
            d_name = getattr(drive_file, "_target_drive", "drive")
            log(f"Error during final sync of {d_name}: {err}")
            failed_drives.append(drive_file)
            active_drives.remove(drive_file)

    if not active_drives:
        raise OSError("All target drives encountered I/O write failures during final sync.")

    if total_bytes <= 0:
        total_bytes = written_bytes

    print(f"{total_bytes} {total_bytes}")
    sys.stdout.flush()

    return True


def eject_drive(drive):
    """Eject the drive. Failing to eject does not invalidate the written image."""
    eject = shutil.which("eject")
    if eject is None:
        log("Warning: eject command not found.")
        return

    result = subprocess.run(
        [eject, drive], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if result.returncode != 0:
        log(f"Warning: could not eject {drive}.")


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: ./ImageWriter.py /file/path/iso.iso /dev/sdX [/dev/sdY ...]\n")
        sys.exit(1)

    filepath = sys.argv[1]

    # Parse and normalize target drives (supports single, multiple, or comma-separated drives)
    raw_targets = []
    for arg in sys.argv[2:]:
        # Ignore legacy boolean flags (e.g. is_windows)
        if arg.lower() in ("true", "false"):
            continue
        for part in arg.split(","):
            part = part.strip()
            if part:
                if not part.startswith("/dev/"):
                    part = "/dev/" + part
                raw_targets.append(part)

    # Deduplicate while preserving order
    target_drives = []
    seen = set()
    for d in raw_targets:
        if d not in seen:
            seen.add(d)
            target_drives.append(d)

    if not target_drives:
        fail("No valid target drive specified.")

    # The image is validated first so a bad file never costs the user the
    # mounted filesystems of the drive.
    image_file, total_bytes, comp_type = open_image_file(filepath)

    drive_handles = []
    opened_descriptors = []

    try:
        for drive in target_drives:
            block_name = validate_usb_drive(drive)
            unmount_drive(drive, block_name)
            # O_DSYNC: without it the writes only reach the page cache
            file_descriptor, drive_size = open_drive_exclusive(
                drive, block_name, sync_writes=True
            )
            opened_descriptors.append(file_descriptor)

            if total_bytes > drive_size and comp_type is None:
                fail(
                    f"The image is larger than the disk {drive}: {total_bytes} bytes > {drive_size} bytes."
                )

            handle = os.fdopen(file_descriptor, "wb", buffering=BUFFER_SIZE)
            handle._target_drive = drive
            drive_handles.append(handle)
    except DriveError as error:
        for fd in opened_descriptors:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            image_file.close()
        except Exception:
            pass
        fail(error)

    if len(target_drives) > 1:
        log(f"Broadcast multi-write active: {len(target_drives)} target devices ({', '.join(target_drives)})")

    # From here on a cancel request must not kill the process mid write: the
    # handler only raises a flag and the write loop leaves the drive in a
    # flushed, consistent state before exiting. The GUI cancels by closing the
    # pipe on stdin, a signal only arrives when the script is used by hand.
    signal.signal(signal.SIGTERM, receive_stop_signal)
    signal.signal(signal.SIGINT, receive_stop_signal)
    watch_stdin_for_cancel()

    completed = False
    try:
        completed = write_image(image_file, drive_handles, total_bytes)
    except OSError as error:
        fail(f"Writing failed: {error}")
    finally:
        for handle in drive_handles:
            try:
                handle.close()
            except OSError:
                pass
        try:
            image_file.close()
        except Exception:
            pass

    if not completed:
        exit_as_cancelled()

    for drive in target_drives:
        eject_drive(drive)

    sys.exit(0)


if __name__ == "__main__":
    main()

