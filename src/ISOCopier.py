#!/usr/bin/python3
"""ISO mode writer: partition the USB disk and copy the ISO contents onto it.

Like ImageWriter.py this script is executed as root through pkexec, so the
target drive is validated with the shared helpers in USBDeviceManager before
anything destructive happens. No command line is ever built through a shell.

stdout carries the progress protocol MainWindow parses (TOTAL_BYTES:, BYTES:,
COPIED:); everything else goes to stderr.
"""

import math
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from subprocess import Popen, PIPE

from USBDeviceManager import DriveError, prepare_usb_drive, read_sysfs_int
from USBDeviceManager import reassert_usb_drive, unmount_drive
from Utils import CancelledError, exit_as_cancelled, fail, log, open_as_caller
from Utils import request_stop, run, settle, stop_requested, sync
from Utils import wait_for_block_device, watch_stdin_for_cancel

UEFI_PARTITION_SIZE = 200 * 1024 * 1024  # 200MB EFI partition for Windows mode

# Everything this script mounts lives below one private directory. The
# permissions of a mounted filesystem come from its own root inode, so the
# mount points themselves cannot be locked down; a 0700 root owned parent makes
# the whole subtree unreachable for every other local user instead.
RUNTIME_DIRECTORY = "/run/pars-image-writer"

# The ISO is a file the user picked, so the kernel parses a filesystem of
# unknown origin as root. Without these options a crafted image could ship a
# setuid root binary or a device node, and while the copy runs any local user
# would be able to use it.
MOUNT_OPTIONS = "nosuid,nodev,noexec"

# parted aligns the first partition at 1MB and a filesystem needs room for its
# own metadata, so an ISO that is only just smaller than the disk still does
# not fit.
PARTITION_ALIGNMENT = 1024 * 1024
FILESYSTEM_OVERHEAD = 1.02


def get_partition_path(drive, part_num):
    """Return universal partition device path (handles /dev/sdX1, /dev/mmcblk0p1, /dev/nvme0n1p1)."""
    suffix = f"p{part_num}" if drive[-1].isdigit() else f"{part_num}"
    return f"{drive}{suffix}"


class IsoCopy:
    def __init__(self, iso_path, drive, is_windows=False, persistence=False):
        # Define file variables
        self.iso_mounted_path = os.path.join(RUNTIME_DIRECTORY, "iso")
        self.usb_mounted_path = os.path.join(RUNTIME_DIRECTORY, "usb")
        self.iso_file_path = iso_path  # e.g. "/home/user/Downloads/pars.iso"
        self.drive = drive  # e.g. "/dev/sdb"

        # Variables
        self.spawned_process = None
        self.exit_code = 0
        self.cancelled = False
        self.is_windows = is_windows
        self.persistence = persistence

        # Kept open for the whole run so the inode that was accepted cannot be
        # replaced by another one afterwards.
        self.iso_descriptor, self.iso_size = self.open_iso_file(iso_path)

        # Validate, unmount and claim the drive before a single byte is touched.
        try:
            self.block_name, self.drive_size = prepare_usb_drive(drive)
        except DriveError as error:
            fail(error)

        self.check_iso_fits()

        self.sector_size = read_sysfs_int(
            f"/sys/block/{self.block_name}/queue/logical_block_size"
        )

        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        # The GUI runs as the user and cannot signal a root process, so it
        # cancels by closing the pipe it holds on stdin.
        watch_stdin_for_cancel(self.stop_spawned_process)

    def open_iso_file(self, iso_path):
        """Open the ISO and make sure it is a real, non empty file.

        The open runs with the credentials of the user that invoked pkexec:
        this process is root, and a write is only ever meant to be started for
        a file the caller could have read on their own.

        O_NONBLOCK keeps the open from hanging on a FIFO, and the type is
        checked on the descriptor itself rather than on the path.
        """
        open_flags = os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC
        try:
            file_descriptor = open_as_caller(iso_path, open_flags)
        except OSError as error:
            fail(f"Could not read the ISO file: {error}")

        file_info = os.fstat(file_descriptor)

        if not stat.S_ISREG(file_info.st_mode):
            os.close(file_descriptor)
            fail(f"{iso_path} is not a regular file.")

        if file_info.st_size == 0:
            os.close(file_descriptor)
            fail(f"{iso_path} is empty.")

        return file_descriptor, file_info.st_size

    def check_iso_fits(self):
        """Reject an oversized image while the disk is still intact.

        Without this the partition table is wiped first and the copy only runs
        out of space minutes later, leaving the user with neither the old
        content of the disk nor a usable one.
        """
        required_bytes = int(self.iso_size * FILESYSTEM_OVERHEAD) + PARTITION_ALIGNMENT
        if self.is_windows:
            required_bytes += UEFI_PARTITION_SIZE

        if required_bytes > self.drive_size:
            fail(
                f"The ISO does not fit on the disk: {required_bytes} bytes needed, {self.drive_size} available."
            )

    def stop_spawned_process(self):
        if self.spawned_process:
            self.spawned_process.kill()

    def signal_handler(self, number, frame):
        request_stop(number)
        self.stop_spawned_process()

    def check_grub_prerequisites(self):
        """Ensure grub-install and target architecture modules exist before touching the drive."""
        if not shutil.which("grub-install"):
            raise DriveError("grub-install executable not found. Please install grub2-common.")

        targets = ["i386-pc"]
        if not self.is_windows:
            targets.append("x86_64-efi")

        missing_targets = []
        for target in targets:
            found = False
            for base_dir in ("/usr/lib/grub", "/usr/share/grub", "/usr/lib/grub-legacy"):
                if os.path.isdir(os.path.join(base_dir, target)):
                    found = True
                    break
            if not found:
                missing_targets.append(target)

        if missing_targets:
            raise DriveError(
                "Required GRUB platform modules missing for: {}. Please install grub-pc-bin and grub-efi-amd64-bin.".format(
                    ", ".join(missing_targets)
                )
            )

    def start_writing(self):
        try:
            # Last chance to notice that the disk was swapped, unplugged or
            # mounted between the checks in __init__ and the first write.
            reassert_usb_drive(self.drive, self.block_name)

            self.check_grub_prerequisites()

            self.create_partition_table(self.drive)

            if self.is_windows:
                self.create_windows_partitions(self.drive)
            else:
                self.create_fat32_partition(self.drive)

            self.mount_folders(self.drive)

            self.copy_dir_with_dd(self.iso_mounted_path, self.usb_mounted_path)

            if self.is_windows:
                time.sleep(2)

            self.install_grub(self.drive, self.usb_mounted_path)

            if self.is_windows:
                self.windows_iso_addition(self.usb_mounted_path)

        except CancelledError:
            self.cancelled = True
        except (OSError, subprocess.CalledProcessError, DriveError) as error:
            log("Exception happened: {}".format(error))
            self.exit_code = 1
        finally:
            self.finish_writing()

        if self.cancelled:
            exit_as_cancelled()

        if self.exit_code:
            sys.exit(self.exit_code)

    def create_partition_table(self, drive):
        # Delete old partitions
        run(["dd", "if=/dev/zero", f"of={drive}", "bs=1M", "count=1"])
        run(["parted", drive, "mktable", "msdos"])

    def wait_for_partition(self, partition):
        """parted returns before udev created the node mkfs is about to use."""
        settle()
        if not wait_for_block_device(partition):
            raise DriveError(f"{partition} did not appear after partitioning.")

    def create_fat32_partition(self, drive):
        partition1 = get_partition_path(drive, 1)
        partition2 = get_partition_path(drive, 2)

        if not self.persistence:
            # Standard single FAT32 partition
            run(["parted", drive, "mkpart", "primary", "fat32", "1", "100%"])
            self.wait_for_partition(partition1)
            run(["wipefs", "-a", partition1, "--force"], False)
            run(["mkfs.vfat", partition1])
            run(["parted", drive, "set", "1", "boot", "on"])  # bios boot support
            return

        # Persistence mode: Partition 1 for ISO, Partition 2 (ext4) for live persistence
        fat32_size_bytes = int(self.iso_size * 1.15) + (256 * 1024 * 1024)
        fat32_sectors = math.ceil(fat32_size_bytes / self.sector_size)
        total_sectors = int(self.drive_size / self.sector_size)

        if total_sectors - fat32_sectors < int((100 * 1024 * 1024) / self.sector_size):
            raise DriveError("Drive does not have enough free space for a persistence partition.")

        run([
            "parted", "-a", "optimal", drive,
            "mkpart", "primary", "fat32", "1s", f"{fat32_sectors}s"
        ])
        run([
            "parted", "-a", "optimal", drive,
            "mkpart", "primary", "ext4", f"{fat32_sectors + 1}s", "100%"
        ])

        self.wait_for_partition(partition1)
        self.wait_for_partition(partition2)

        run(["wipefs", "-a", partition1, "--force"], False)
        run(["wipefs", "-a", partition2, "--force"], False)

        run(["mkfs.vfat", partition1])
        run(["mkfs.ext4", "-F", "-L", "persistence", partition2])

        run(["parted", drive, "set", "1", "boot", "on"])

        # Create persistence.conf on partition 2
        persistence_mount = os.path.join(RUNTIME_DIRECTORY, "persistence")
        os.makedirs(persistence_mount, mode=0o700, exist_ok=True)
        run(["mount", partition2, persistence_mount])
        try:
            with open(os.path.join(persistence_mount, "persistence.conf"), "w") as f:
                f.write("/ union\n")
            sync()
        finally:
            run(["umount", persistence_mount], False)

    def create_windows_partitions(self, drive):
        partition1 = get_partition_path(drive, 1)
        partition2 = get_partition_path(drive, 2)

        total_sectors = int(self.drive_size / self.sector_size)
        uefi_sectors = math.ceil(UEFI_PARTITION_SIZE / self.sector_size)
        ntfs_sector_end = total_sectors - uefi_sectors - 1

        if ntfs_sector_end < 1:
            raise DriveError(f"{drive} is too small for Windows mode.")

        # Create NTFS partition1 (windows iso files here)
        run(
            [
                "parted",
                "-a",
                "minimal",
                drive,
                "mkpart",
                "primary",
                "ntfs",
                "1s",  # bootable needs to start from sector 1
                f"{ntfs_sector_end}s",
            ]
        )

        # Create FAT32 partition2 (uefi here)
        run(
            [
                "parted",
                "-a",
                "minimal",
                drive,
                "mkpart",
                "primary",
                "fat32",
                f"{ntfs_sector_end + 1}s",
                "100%",
            ]
        )
        self.wait_for_partition(partition1)
        self.wait_for_partition(partition2)

        run(["wipefs", "-a", partition1, "--force"], False)
        run(["wipefs", "-a", partition2, "--force"], False)

        run(["mkfs.ntfs", "-f", "-v", partition1])
        run(["mkfs.fat", "-F32", partition2])

        run(["parted", drive, "set", "1", "boot", "on"])

        # Create UEFI supports file NTFS format on partition2
        # uefi image url: "https://github.com/pbatard/rufus/raw/master/res/uefi/assets/uefi-ntfs.img",
        uefi_ntfs_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "assets", "uefi-ntfs.img"
        )
        if not os.path.isfile(uefi_ntfs_path):
            raise DriveError("UEFI helper image not found: {}".format(uefi_ntfs_path))

        run(["dd", "if={}".format(uefi_ntfs_path), "of={}".format(partition2)])

        run(["parted", drive, "set", "2", "hidden", "on"])
        run(["parted", drive, "set", "2", "esp", "on"])

        sync()

    def create_runtime_directory(self):
        """Create the private 0700 directory both mount points live in."""
        if os.path.islink(RUNTIME_DIRECTORY):
            raise DriveError("{} is a symbolic link.".format(RUNTIME_DIRECTORY))

        os.makedirs(RUNTIME_DIRECTORY, mode=0o700, exist_ok=True)
        # makedirs only applies the mode when it creates the directory, and the
        # umask can take bits off even then.
        os.chown(RUNTIME_DIRECTORY, 0, 0)
        os.chmod(RUNTIME_DIRECTORY, 0o700)

        os.makedirs(self.iso_mounted_path, mode=0o700, exist_ok=True)
        os.makedirs(self.usb_mounted_path, mode=0o700, exist_ok=True)

    def mount_iso(self):
        """Mount source ISO image with fallback cascade across filesystem types."""
        types_to_try = ["udf", "iso9660"] if self.is_windows else ["iso9660", "udf"]
        mounted = False
        last_error = None
        for fs_type in types_to_try:
            try:
                run([
                    "mount",
                    "-o",
                    "ro," + MOUNT_OPTIONS,
                    "-t",
                    fs_type,
                    self.iso_file_path,
                    self.iso_mounted_path,
                ])
                mounted = True
                break
            except Exception as e:
                last_error = e

        if not mounted:
            # Fallback to auto-detection without explicit -t
            try:
                run([
                    "mount",
                    "-o",
                    "ro," + MOUNT_OPTIONS,
                    self.iso_file_path,
                    self.iso_mounted_path,
                ])
                mounted = True
            except Exception as e:
                raise DriveError("Failed to mount ISO image ({}): {}".format(self.iso_file_path, last_error or e))

    def mount_usb(self, partition):
        """Mount target USB partition with fallback cascade (ntfs3 -> ntfs-3g -> ntfs or vfat)."""
        types_to_try = ["ntfs3", "ntfs-3g", "ntfs"] if self.is_windows else ["vfat"]
        mounted = False
        last_error = None
        for fs_type in types_to_try:
            try:
                run([
                    "mount",
                    "-o",
                    "rw," + MOUNT_OPTIONS,
                    "-t",
                    fs_type,
                    partition,
                    self.usb_mounted_path,
                ])
                mounted = True
                break
            except Exception as e:
                last_error = e

        if not mounted:
            # Fallback without explicit -t
            try:
                run([
                    "mount",
                    "-o",
                    "rw," + MOUNT_OPTIONS,
                    partition,
                    self.usb_mounted_path,
                ])
                mounted = True
            except Exception as e:
                raise DriveError("Failed to mount USB partition ({}): {}".format(partition, last_error or e))

    def mount_folders(self, drive):
        partition1 = get_partition_path(drive, 1)

        # Unmount first if already mounted
        self.unmount_tmp_folders()
        self.remove_tmp_folders()

        # The desktop may have auto mounted the partitions we just created.
        unmount_drive(drive, self.block_name)

        self.create_runtime_directory()

        self.mount_iso()
        self.mount_usb(partition1)

    def copy_dir_with_dd(self, src, dest):
        sync()

        copy_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "copy_dir_with_dd.sh"
        )

        with Popen(
            [copy_script, src, dest],
            stdout=PIPE,
            # pv reports the copied byte counts on stderr, so it has to be
            # merged into the stream we read.
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            self.spawned_process = process
            for line in process.stdout:
                if stop_requested():
                    process.kill()
                    break

                # The script reports plain byte counts, everything else is a
                # protocol line of its own (TOTAL_BYTES:, COPIED:).
                if line.strip().isdigit():
                    sys.stdout.write(f"BYTES:{line}")
                else:
                    sys.stdout.write(line)
                sys.stdout.flush()

        self.spawned_process = None

        if stop_requested():
            raise CancelledError()

        # Without this check a half copied USB disk would get a boot loader and
        # be reported as finished.
        if process.returncode != 0:
            raise DriveError(
                f"Copying the ISO contents failed with exit code {process.returncode}."
            )

        sync()

    def install_grub(self, drive, usb_mounted_path):
        sync()

        boot_directory = os.path.join(usb_mounted_path, "boot")

        if self.is_windows:
            run(
                [
                    "grub-install",
                    drive,
                    "--target=i386-pc",
                    "--force",
                    f"--boot-directory={boot_directory}",
                ]
            )
            return

        # Remove grub & efi information on copied ISO file data:
        shutil.rmtree(os.path.join(boot_directory, "grub"), ignore_errors=True)
        shutil.rmtree(os.path.join(usb_mounted_path, "EFI"), ignore_errors=True)

        # Install new grub on efi partition
        run(
            [
                "grub-install",
                "--target=i386-pc",
                f"--efi-directory={usb_mounted_path}",
                f"--boot-directory={boot_directory}",
                drive,
            ]
        )
        run(
            [
                "grub-install",
                "--target=x86_64-efi",
                "--removable",
                "--efi-directory={}".format(usb_mounted_path),
                "--boot-directory={}".format(boot_directory),
                drive,
            ]
        )
        run(["grub-install", "--recheck", drive])

    def windows_iso_addition(self, usb_mounted_path):
        grub_cfg_path = os.path.join(usb_mounted_path, "boot", "grub", "grub.cfg")
        with open(grub_cfg_path, "a") as grubcfg:
            grubcfg.write("insmod part_msdos\n")
            grubcfg.write("insmod ntfs\n")
            grubcfg.write("insmod ntldr\n")
            grubcfg.write("ntldr /bootmgr\n")
            grubcfg.write("boot\n")

    def finish_writing(self):
        # Runs while unwinding an error or a cancel too, so it must not raise.
        subprocess.run(["sync"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for target in (
            self.iso_mounted_path,
            self.usb_mounted_path,
            get_partition_path(self.drive, 1),
            get_partition_path(self.drive, 2),
            os.path.join(RUNTIME_DIRECTORY, "persistence"),
        ):
            res = subprocess.run(["umount", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode != 0:
                # Lazy unmount fallback to prevent EBUSY locks from desktop indexers
                subprocess.run(["umount", "-l", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        shutil.rmtree(RUNTIME_DIRECTORY, ignore_errors=True)

    def unmount_tmp_folders(self):
        for path in (self.iso_mounted_path, self.usb_mounted_path):
            res = subprocess.run(["umount", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode != 0:
                subprocess.run(["umount", "-l", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def remove_tmp_folders(self):
        shutil.rmtree(self.iso_mounted_path, ignore_errors=True)
        shutil.rmtree(self.usb_mounted_path, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4, 5):
        sys.stderr.write(
            "Usage: {} [iso path] [drive] [is_windows=false] [persistence=false]\n".format(sys.argv[0])
        )
        sys.exit(1)

    is_windows = len(sys.argv) >= 4 and sys.argv[3] == "true"
    persistence = len(sys.argv) >= 5 and sys.argv[4] == "true"

    IsoCopy(sys.argv[1], sys.argv[2], is_windows=is_windows, persistence=persistence).start_writing()
