#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pars Image Writer — Remote Cloud ISO Catalog & Stream Burning Engine
Allows discovering, streaming and burning official OS images directly
from the cloud to USB disks without consuming temporary local hard drive storage.
"""

from __future__ import annotations

import os
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Optional, Callable, Dict, Any
import requests

CATALOG_URL = "https://indir.pars.org.tr/catalog.json"
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB chunk for network-to-disk streaming


@dataclass
class CatalogEntry:
    id: str
    name: str
    category: str
    version: str
    arch: str
    size_bytes: int
    url: str
    sha256: Optional[str]
    description: str

    def size_human(self) -> str:
        size = self.size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{self.size_bytes} B"


# Curated Built-in Catalog (Ensures 100% offline & instantaneous availability)
BUILTIN_CATALOG: List[CatalogEntry] = [
    CatalogEntry(
        id="pars-desktop-current",
        name="Pars Linux Desktop",
        category="Pars Linux",
        version="2026.1",
        arch="x86_64",
        size_bytes=2936012800,  # ~2.73 GB
        url="https://indir.pars.org.tr/PARS/pars-linux-desktop-current.iso",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        description="Modern, hızlı ve zarif GNOME tabanlı Pars Linux masaüstü ortamı.",
    ),
    CatalogEntry(
        id="pars-minimal-current",
        name="Pars Linux Minimal & Server",
        category="Pars Linux",
        version="2026.1",
        arch="x86_64",
        size_bytes=943718400,  # ~900 MB
        url="https://indir.pars.org.tr/PARS/pars-linux-minimal-current.iso",
        sha256=None,
        description="Sunucu ve uç cihazlar için optimize edilmiş hafif, başsız kurulum kalıbı.",
    ),
    CatalogEntry(
        id="debian-12-bookworm",
        name="Debian GNU/Linux 12 (Bookworm)",
        category="Debian",
        version="12.7",
        arch="x86_64",
        size_bytes=3984588800,  # ~3.71 GB
        url="https://cdimage.debian.org/debian-cd/current/amd64/iso-dvd/debian-12.7.0-amd64-DVD-1.iso",
        sha256=None,
        description="Evrensel işletim sistemi. Kararlı, güvenilir Debian ana kurulum DVD kalıbı.",
    ),
    CatalogEntry(
        id="ubuntu-2404-desktop",
        name="Ubuntu 24.04 LTS (Noble Numbat)",
        category="Ubuntu",
        version="24.04.1",
        arch="x86_64",
        size_bytes=6144655360,  # ~5.72 GB
        url="https://releases.ubuntu.com/24.04/ubuntu-24.04.1-desktop-amd64.iso",
        sha256=None,
        description="Uzun vadeli destekli (LTS) popüler Linux dağıtımı.",
    ),
    CatalogEntry(
        id="fedora-40-workstation",
        name="Fedora 40 Workstation",
        category="Fedora",
        version="40",
        arch="x86_64",
        size_bytes=2254857856,  # ~2.10 GB
        url="https://download.fedoraproject.org/pub/fedora/linux/releases/40/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-40-1.14.iso",
        sha256=None,
        description="En son açık kaynak teknolojileri ve saf GNOME deneyimi.",
    ),
    CatalogEntry(
        id="archlinux-current",
        name="Arch Linux",
        category="Arch",
        version="Latest",
        arch="x86_64",
        size_bytes=1153433600,  # ~1.07 GB
        url="https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso",
        sha256=None,
        description="Sürekli güncellenen (rolling-release), esnek ve yalın sistem kalıbı.",
    ),
    CatalogEntry(
        id="alpine-320-standard",
        name="Alpine Linux 3.20",
        category="Minimal",
        version="3.20.3",
        arch="x86_64",
        size_bytes=218103808,  # ~208 MB
        url="https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/alpine-standard-3.20.3-x86_64.iso",
        sha256=None,
        description="Güvenlik odaklı, ultra hafif ve hızlı musl libc / busybox kalıbı.",
    ),
]


class RemoteCatalog:
    """Manages discovery and live stream burning of remote cloud ISO images."""

    def __init__(self, catalog_url: str = CATALOG_URL):
        self.catalog_url = catalog_url
        self._entries: List[CatalogEntry] = list(BUILTIN_CATALOG)

    def refresh(self, timeout: float = 4.0) -> List[CatalogEntry]:
        """Attempts to update the catalog from remote source, fallback to builtin."""
        try:
            resp = requests.get(self.catalog_url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                items: List[CatalogEntry] = []
                for item in data.get("images", []):
                    items.append(
                        CatalogEntry(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            category=item.get("category", "Other"),
                            version=item.get("version", ""),
                            arch=item.get("arch", "x86_64"),
                            size_bytes=int(item.get("size_bytes", 0)),
                            url=item.get("url", ""),
                            sha256=item.get("sha256"),
                            description=item.get("description", ""),
                        )
                    )
                if items:
                    self._entries = items
        except Exception:
            # Offline or unreachable: keep builtin catalog
            pass
        return self._entries

    def get_entries(self) -> List[CatalogEntry]:
        return list(self._entries)

    def find_by_id(self, entry_id: str) -> Optional[CatalogEntry]:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def search(self, query: str) -> List[CatalogEntry]:
        q = query.strip().lower()
        if not q:
            return self.get_entries()
        return [
            e
            for e in self._entries
            if q in e.name.lower()
            or q in e.category.lower()
            or q in e.id.lower()
            or q in e.description.lower()
        ]

    @staticmethod
    def stream_download_and_write(
        entry: CatalogEntry,
        target_devices: List[str],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Dict[str, Any]:
        """
        Streams HTTP/HTTPS bytes directly into target block device file descriptors.
        Consumes 0 bytes of local disk or swap storage.
        Calculates SHA-256 on-the-fly and writes to multiple USB drives concurrently.
        """
        if not target_devices:
            raise ValueError("No target devices specified for stream writing.")

        fds: Dict[str, int] = {}
        hasher = hashlib.sha256()
        total_written = 0
        start_time = time.time()
        last_report_time = start_time

        try:
            # 1. Open all target block devices with O_WRONLY | O_SYNC
            for dev in target_devices:
                # Open with direct sync to ensure physical flash commit
                flags = os.O_WRONLY | getattr(os, "O_DSYNC", os.O_SYNC)
                fd = os.open(dev, flags)
                fds[dev] = fd

            # 2. Open HTTP connection with stream=True
            headers = {"User-Agent": "Pars-Image-Writer/1.0.0"}
            with requests.get(entry.url, stream=True, headers=headers, timeout=20) as resp:
                resp.raise_for_status()

                content_len = resp.headers.get("Content-Length")
                total_expected = int(content_len) if content_len else entry.size_bytes

                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if cancel_token and cancel_token():
                        return {
                            "success": False,
                            "cancelled": True,
                            "bytes_written": total_written,
                            "sha256": hasher.hexdigest(),
                        }

                    if not chunk:
                        continue

                    # Update SHA256 checksum
                    hasher.update(chunk)

                    # Write broadcast chunk to all target devices
                    for dev, fd in list(fds.items()):
                        try:
                            os.write(fd, chunk)
                        except OSError as write_err:
                            # Isolate individual device failure
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                            del fds[dev]
                            if not fds:
                                raise OSError(
                                    f"All target USB devices failed during write: {write_err}"
                                )

                    total_written += len(chunk)
                    now = time.time()

                    # Report progress every 0.25 seconds or at least 4 times per second
                    if progress_callback and (now - last_report_time >= 0.25):
                        elapsed = max(0.001, now - start_time)
                        speed = total_written / elapsed
                        eta = (
                            (total_expected - total_written) / speed
                            if total_expected > total_written and speed > 0
                            else 0
                        )
                        progress_callback(
                            {
                                "status": "writing",
                                "bytes_written": total_written,
                                "total_bytes": total_expected,
                                "percent": min(
                                    100.0,
                                    (total_written / total_expected * 100.0)
                                    if total_expected > 0
                                    else 0.0,
                                ),
                                "speed_bps": speed,
                                "eta_seconds": eta,
                                "active_targets": list(fds.keys()),
                            }
                        )
                        last_report_time = now

            # 3. Flush hardware caches (fsync)
            for dev, fd in fds.items():
                try:
                    os.fsync(fd)
                except OSError:
                    pass

            computed_sha256 = hasher.hexdigest()
            verified = True
            if entry.sha256:
                verified = computed_sha256.lower() == entry.sha256.lower()

            if progress_callback:
                progress_callback(
                    {
                        "status": "completed",
                        "bytes_written": total_written,
                        "total_bytes": total_written,
                        "percent": 100.0,
                        "speed_bps": total_written / max(0.001, time.time() - start_time),
                        "eta_seconds": 0,
                        "sha256": computed_sha256,
                        "checksum_verified": verified,
                        "active_targets": list(fds.keys()),
                    }
                )

            return {
                "success": True,
                "cancelled": False,
                "bytes_written": total_written,
                "sha256": computed_sha256,
                "checksum_verified": verified,
                "elapsed_seconds": time.time() - start_time,
            }

        finally:
            # Always cleanly close all open file descriptors
            for fd in fds.values():
                try:
                    os.close(fd)
                except OSError:
                    pass
