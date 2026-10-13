#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pars Image Writer — Micro PXE & HTTP Netboot Server
Allows booting and installing Linux operating systems across the local area network (LAN)
without requiring physical USB flash drives.
Supports UEFI HTTP Boot and iPXE network chainloading with HTTP 206 byte-range support.
"""

from __future__ import annotations

import os
import sys
import socket
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Dict, Any, Callable


def get_local_ip() -> str:
    """Detects the primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets, just routes to determine interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class NetbootHTTPHandler(SimpleHTTPRequestHandler):
    """
    HTTP handler optimized for network bootloaders.
    Provides standard byte-range (HTTP 206) support essential for UEFI HTTP Boot.
    """

    server_instance: Any = None

    def log_message(self, format: str, *args: Any) -> None:
        client_ip = self.client_address[0]
        msg = format % args
        if self.server_instance and self.server_instance.log_callback:
            self.server_instance.log_callback(f"[{client_ip}] {msg}")

    def do_GET(self) -> None:
        if self.path in ("/", "/ipxe", "/boot.ipxe"):
            self.send_ipxe_script()
            return

        # Serve static files (ISO images, kernel, initrd) with byte range support
        super().do_GET()

    def send_ipxe_script(self) -> None:
        iso_name = os.path.basename(self.server_instance.iso_path)
        local_ip = self.server_instance.host
        port = self.server_instance.port

        script = f"""#!ipxe
# Pars Image Writer Network Boot Script
echo ========================================================
echo   Pars Image Writer - LAN Network Boot Station
echo ========================================================
echo Booting {iso_name} from http://{local_ip}:{port}/
echo Initializing network and kernel...

# SANBoot or memdisk ISO chainload
set base-url http://{local_ip}:{port}
kernel ${{base-url}}/vmlinuz || sanboot --no-describe ${{base-url}}/{iso_name} || goto failed
boot

:failed
echo [ERROR] Network boot failed or ISO could not be chainloaded.
shell
"""
        data = script.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


class NetbootServer:
    """Manages background lifecycle of the local network installation server."""

    def __init__(
        self,
        iso_path: str,
        host: Optional[str] = None,
        port: int = 8088,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        if not os.path.isfile(iso_path):
            raise FileNotFoundError(f"ISO file does not exist: {iso_path}")

        self.iso_path = os.path.abspath(iso_path)
        self.iso_dir = os.path.dirname(self.iso_path)
        self.iso_name = os.path.basename(self.iso_path)
        self.host = host or get_local_ip()
        self.port = port
        self.log_callback = log_callback
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_boot_url(self) -> str:
        return f"http://{self.host}:{self.port}/boot.ipxe"

    def get_iso_url(self) -> str:
        return f"http://{self.host}:{self.port}/{self.iso_name}"

    def start(self) -> None:
        """Starts the netboot HTTP server in a background thread."""
        if self._is_running:
            return

        NetbootHTTPHandler.server_instance = self
        original_cwd = os.getcwd()

        from functools import partial

        handler = partial(NetbootHTTPHandler, directory=self.iso_dir)

        try:
            self._server = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError:
            # Fallback to wildcard bind
            self._server = ThreadingHTTPServer(("0.0.0.0", self.port), handler)

        self._is_running = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        if self.log_callback:
            self.log_callback(
                f"Netboot server started: {self.get_boot_url()} (Serving {self.iso_name})"
            )

    def stop(self) -> None:
        """Stops the netboot HTTP server cleanly."""
        if not self._is_running or not self._server:
            return

        self._is_running = False
        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception:
            pass

        if self.log_callback:
            self.log_callback("Netboot server stopped.")
