#!/usr/bin/python3
"""Headless command-line interface for Pars Image Writer.

Provides full scripting, terminal automation and headless image burning
without requiring GTK or any desktop environment. Supports machine-readable
JSON progress streaming (--json) for web panels and automated pipelines.
"""

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from collections import deque
from subprocess import Popen, PIPE

import USBDeviceManager
from Utils import (
    calculate_hash,
    detect_compression,
    detect_hash_type,
    get_uncompressed_size,
    SUPPORTED_HASH_ALGORITHMS,
    SUPPORTED_IMAGE_EXTENSIONS,
)

# Verification defaults
SHA256SUMS_URL = "https://indir.pars.org.tr/PARS/SHA256SUMS"
MD5SUMS_URL = "https://indir.pars.org.tr/PARS/MD5SUMS"
REQUEST_TIMEOUT_SECONDS = 15

# Speed calculation window
SPEED_WINDOW_SECONDS = 5.0
MIN_SPEED_SECONDS = 0.5


def get_version():
    """Retrieve version from __version__ file or return default."""
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__version__")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r") as f:
                return f.read().strip()
        except OSError:
            pass
    return "1.0.0"


def find_script(script_name):
    """Find the path to ImageWriter.py or ISOCopier.py."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name),
        os.path.join("/usr/share/pars/pars-image-writer/src", script_name),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]


def format_duration(seconds):
    """Format seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def calculate_file_hash(file_path, algorithm="md5"):
    """Compute hash of a file with progress updates."""
    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


class ProgressTracker:
    """Computes transfer speed and ETA using a sliding time window."""

    def __init__(self, total_bytes):
        self.total_bytes = total_bytes
        self.written_bytes = 0
        self.history = deque()
        self.start_time = time.monotonic()
        self.last_update_time = 0
        self.last_emitted_percent = -1

    def update(self, written_bytes):
        self.written_bytes = written_bytes
        now = time.monotonic()
        self.history.append((now, written_bytes))

        # Evict samples older than SPEED_WINDOW_SECONDS
        cutoff = now - SPEED_WINDOW_SECONDS
        while len(self.history) > 1 and self.history[0][0] < cutoff:
            self.history.popleft()

    def get_speed_mb(self):
        """Calculate average speed in MB/s over the sliding window."""
        if len(self.history) < 2:
            elapsed = time.monotonic() - self.start_time
            if elapsed >= MIN_SPEED_SECONDS and elapsed > 0:
                return (self.written_bytes / elapsed) / (1000 * 1000)
            return 0.0

        oldest_time, oldest_bytes = self.history[0]
        latest_time, latest_bytes = self.history[-1]
        time_delta = latest_time - oldest_time
        if time_delta < MIN_SPEED_SECONDS:
            return 0.0
        bytes_delta = latest_bytes - oldest_bytes
        return max(0.0, (bytes_delta / time_delta) / (1000 * 1000))

    def get_eta_seconds(self):
        """Estimate remaining time in seconds based on current speed."""
        speed_mb = self.get_speed_mb()
        if speed_mb <= 0:
            return None
        remaining_bytes = max(0, self.total_bytes - self.written_bytes)
        speed_bytes = speed_mb * 1000 * 1000
        return int(remaining_bytes / speed_bytes)

    def get_percent(self):
        """Calculate percentage completed."""
        if self.total_bytes <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.written_bytes / self.total_bytes) * 100))


def render_progress_bar(percent, speed_mb, eta_seconds, width=30, multi_count=1):
    """Render ANSI terminal progress bar."""
    filled = int(width * (percent / 100.0))
    bar = "█" * filled + "░" * (width - filled)
    eta_str = format_duration(eta_seconds)
    multi_tag = f" | {multi_count} Disk" if multi_count > 1 else ""
    return f"\r\033[K[{bar}] {percent:5.1f}% | {speed_mb:6.1f} MB/s | Kalan: {eta_str}{multi_tag}"


def handle_device_listing(as_json=False):
    """List connected USB drives and exit."""
    devices = USBDeviceManager.get_usb_devices()
    if as_json:
        result = [
            {
                "device": f"/dev/{d[0]}",
                "name": d[0],
                "label": d[1],
                "size": d[2],
            }
            for d in devices
        ]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    if not devices:
        print("Bağlı herhangi bir USB depolama birimi bulunamadı.")
        sys.exit(0)

    print("Bağlı USB Sürücüler:")
    print("-" * 55)
    print(f"{'Aygıt':<12} {'Kapasite':<10} {'Model / Etiket'}")
    print("-" * 55)
    for d in devices:
        dev_path = f"/dev/{d[0]}"
        label = d[1]
        size = d[2]
        print(f"{dev_path:<12} {size:<10} {label}")
    print("-" * 55)
    sys.exit(0)


def verify_integrity(iso_path, expected_checksum=None, algorithm=None, as_json=False):
    """Verify integrity of ISO image using SHA-256, SHA-512 or MD5."""
    algo = algorithm.lower() if algorithm else None
    expected_hash = expected_checksum.strip().lower() if expected_checksum else None

    if expected_hash and not algo:
        algo = detect_hash_type(expected_hash) or "sha256"

    # If no expected hash given, check local files first
    iso_dir = os.path.dirname(iso_path)
    iso_name = os.path.basename(iso_path)
    base_no_ext = os.path.splitext(iso_path)[0]

    if not expected_hash:
        for ext, detected_algo in [(".sha256", "sha256"), (".sha512", "sha512"), (".md5", "md5")]:
            for cand in [iso_path + ext, base_no_ext + ext]:
                if os.path.isfile(cand):
                    try:
                        with open(cand, "r") as f:
                            content = f.read().strip()
                            expected_hash = content.split()[0].lower()
                            algo = detected_algo
                            break
                    except OSError:
                        pass
            if expected_hash:
                break

    if not algo:
        algo = "sha256"

    if not as_json:
        print(f"Kalıp bütünlüğü hesaplanıyor [{algo.upper()}]...")
    else:
        print(json.dumps({"event": "verifying", "file": iso_name, "algorithm": algo}), flush=True)

    calculated_hash = calculate_hash(iso_path, algo).lower()

    # If we have an expected hash (from parameter or local file)
    if expected_hash:
        matched = (calculated_hash == expected_hash)
        if matched:
            if not as_json:
                print(f"✓ Sağlama doğrulaması BAŞARILI [{algo.upper()}]: {calculated_hash}")
            else:
                print(json.dumps({"event": "verified", "status": "ok", "algorithm": algo, "hash": calculated_hash}), flush=True)
            return True
        else:
            msg = f"Sağlama uyuşmazlığı! Beklenen: {expected_hash}, Hesaplanan: {calculated_hash}"
            if not as_json:
                sys.stderr.write(f"Hata: {msg}\n")
            else:
                print(json.dumps({"event": "error", "message": msg, "code": 1}), flush=True)
            return False

    # Try online verification (SHA256SUMS first, then MD5SUMS)
    try:
        import requests
        # 1. Try online SHA256SUMS
        try:
            resp = requests.get(SHA256SUMS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                calc_sha256 = calculated_hash if algo == "sha256" else calculate_hash(iso_path, "sha256").lower()
                matched = any(line.strip().split()[:1] == [calc_sha256] for line in resp.text.splitlines())
                if matched:
                    if not as_json:
                        print(f"✓ Çevrimiçi sunucu doğrulaması BAŞARILI [SHA-256]: {calc_sha256}")
                    else:
                        print(json.dumps({"event": "verified", "status": "ok", "algorithm": "sha256", "hash": calc_sha256}), flush=True)
                    return True
        except requests.RequestException:
            pass

        # 2. Try online MD5SUMS
        try:
            resp = requests.get(MD5SUMS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                calc_md5 = calculated_hash if algo == "md5" else calculate_hash(iso_path, "md5").lower()
                matched = any(line.strip().split()[:1] == [calc_md5] for line in resp.text.splitlines())
                if matched:
                    if not as_json:
                        print(f"✓ Çevrimiçi sunucu doğrulaması BAŞARILI [MD5]: {calc_md5}")
                    else:
                        print(json.dumps({"event": "verified", "status": "ok", "algorithm": "md5", "hash": calc_md5}), flush=True)
                    return True
        except requests.RequestException:
            pass

        msg = f"Çevrimiçi doğrulama listelerinde eşleşen özet bulunamadı: {calculated_hash}"
        if not as_json:
            sys.stderr.write(f"Hata: {msg}\n")
        else:
            print(json.dumps({"event": "error", "message": msg, "code": 1}), flush=True)
        return False
    except Exception as exc:
        msg = f"Çevrimiçi doğrulama sunucusuna erişilemedi: {exc}"
        if not as_json:
            sys.stderr.write(f"Uyarı: {msg}\n")
        else:
            print(json.dumps({"event": "warning", "message": msg}), flush=True)
        return False


def handle_catalog_listing(as_json=False):
    """List available operating system images in the cloud catalog."""
    from Catalog import RemoteCatalog

    cat = RemoteCatalog()
    entries = cat.get_entries()

    if as_json:
        data = [
            {
                "id": e.id,
                "name": e.name,
                "category": e.category,
                "version": e.version,
                "arch": e.arch,
                "size_bytes": e.size_bytes,
                "size_human": e.size_human(),
                "url": e.url,
                "sha256": e.sha256,
                "description": e.description,
            }
            for e in entries
        ]
        print(json.dumps(data, indent=2), flush=True)
        sys.exit(0)

    print("=" * 82)
    print("  Pars Image Writer — Bulut İmaj Kataloğu (Remote ISO Catalog)")
    print("=" * 82)
    print(f"{'ID':<24} {'İsim':<26} {'Sürüm':<8} {'Mimari':<8} {'Boyut':<10}")
    print("-" * 82)
    for e in entries:
        print(f"{e.id:<24} {e.name:<26} {e.version:<8} {e.arch:<8} {e.size_human():<10}")
    print("-" * 82)
    print("Doğrudan indirmeden USB'ye canlı yazmak için:")
    print("  pars-image-writer-cli --cloud-write <ID> -d /dev/sdX")
    print("=" * 82)
    sys.exit(0)


def handle_cloud_write(entry_id, raw_devices, yes=False, as_json=False):
    """Stream download and burn directly into target USB block devices."""
    from Catalog import RemoteCatalog

    cat = RemoteCatalog()
    entry = cat.find_by_id(entry_id)
    if not entry:
        err_msg = f"Bulut kataloğunda '{entry_id}' kimlikli bir kalıp bulunamadı. Kataloğu görmek için: --catalog"
        if as_json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    if not raw_devices:
        err_msg = "En az bir hedef USB aygıtı belirtilmelidir (-d /dev/sdX)."
        if as_json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    target_devices = []
    seen = set()
    for d_arg in raw_devices:
        for part in d_arg.split(","):
            part = part.strip()
            if part:
                if not part.startswith("/dev/"):
                    part = f"/dev/{part}"
                if part not in seen:
                    seen.add(part)
                    target_devices.append(part)

    # 5-stage drive validation
    validated_targets = []
    for dev_path in target_devices:
        try:
            block_name = USBDeviceManager.validate_usb_drive(dev_path)
            validated_targets.append(dev_path)
        except USBDeviceManager.DriveError as error:
            err_msg = f"Güvenlik Engeli ({dev_path}): {error}"
            if as_json:
                print(json.dumps({"event": "error", "message": str(error), "device": dev_path, "code": 3}), flush=True)
            else:
                sys.stderr.write(f"Hata: {err_msg}\n")
            sys.exit(3)

    if not yes and not as_json:
        print("\n" + "=" * 64)
        print("  UYARI: CANLI BULUT YAZMA İŞLEMİ (STREAM BURN)")
        print("=" * 64)
        print(f"  Kalıp           : {entry.name} ({entry.version}) [{entry.size_human()}]")
        print(f"  Hedef Aygıt(lar): {', '.join(validated_targets)}")
        print("  DİKKAT: Seçilen disklerin TÜM VERİLERİ GERİ ALINAMAZ ŞEKİLDE SİLİNECEK!")
        print("=" * 64)
        confirm = input("İşlemi onaylıyor musunuz? (evet/hayır): ").strip().lower()
        if confirm not in ("evet", "e", "yes", "y"):
            print("İşlem kullanıcı tarafından iptal edildi.")
            sys.exit(0)

    if not as_json:
        print(f"\nCanlı akış başlatılıyor: {entry.name} -> {', '.join(validated_targets)}")

    multi_count = len(validated_targets)

    def on_progress(p_data):
        if as_json:
            print(json.dumps({"event": "progress", **p_data}), flush=True)
        else:
            pct = p_data.get("percent", 0.0)
            spd = p_data.get("speed_bps", 0.0) / (1024 * 1024)
            eta = p_data.get("eta_seconds", 0)
            print(render_progress_bar(pct, spd, eta, multi_count=multi_count), end="", flush=True)

    result = cat.stream_download_and_write(entry, validated_targets, progress_callback=on_progress)
    if result.get("success"):
        if as_json:
            print(json.dumps({"event": "completed", **result}), flush=True)
        else:
            print(f"\n\n✓ Canlı bulut yazma işlemi başarıyla tamamlandı!")
            print(f"  Hesaplanan SHA-256: {result.get('sha256')}")
            print(f"  Toplam yazılan     : {result.get('bytes_written')} bayt")
        sys.exit(0)
    else:
        err_msg = "Canlı yazma işlemi tamamlanamadı."
        if as_json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 1}), flush=True)
        else:
            sys.stderr.write(f"\nHata: {err_msg}\n")
        sys.exit(1)


def handle_netboot(iso_path, port=8088, as_json=False):
    """Launch local micro PXE/HTTP network boot server."""
    from NetbootServer import NetbootServer, get_local_ip

    iso_path = os.path.abspath(iso_path)
    if not os.path.isfile(iso_path):
        err_msg = f"Kalıp dosyası bulunamadı: {iso_path}"
        if as_json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    def log_cb(msg):
        if as_json:
            print(json.dumps({"event": "netboot_log", "message": msg}), flush=True)
        else:
            print(f"  [NETBOOT] {msg}")

    server = NetbootServer(iso_path, port=port, log_callback=log_cb)
    server.start()

    if as_json:
        print(
            json.dumps(
                {
                    "event": "netboot_started",
                    "host": server.host,
                    "port": server.port,
                    "boot_url": server.get_boot_url(),
                    "iso_url": server.get_iso_url(),
                }
            ),
            flush=True,
        )
    else:
        print("\n" + "=" * 68)
        print("  Pars Image Writer — PXE & HTTP Ağ Kurulum İstasyonu (Netboot)")
        print("=" * 68)
        print(f"  Yerel IP Adresi       : {server.host}")
        print(f"  Yayın Portu           : {server.port}")
        print(f"  Sunulan İmaj Dosyası  : {server.iso_name}")
        print(f"  iPXE Önyükleme URL'i  : {server.get_boot_url()}")
        print(f"  Doğrudan İndirme URL'i: {server.get_iso_url()}")
        print("-" * 68)
        print("  İstemci bilgisayarda Boot Menüden 'UEFI HTTP Boot' seçeneğini")
        print(f"  kullanarak yukarıdaki iPXE URL'sini girin.")
        print("  Sunucuyu durdurmak için: Ctrl+C")
        print("=" * 68 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        if as_json:
            print(json.dumps({"event": "netboot_stopped"}), flush=True)
        else:
            print("\nNetboot sunucusu kapatıldı.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="pars-image-writer-cli",
        description="Pars Image Writer — Bağımsız Headless Terminal Disk Yazma Aracı",
        add_help=True,
    )
    parser.add_argument(
        "-f", "--file",
        dest="file",
        help="Yazdırılacak .iso veya .img kalıp dosyasının yolu.",
    )
    parser.add_argument(
        "-d", "--device", "--devices",
        dest="devices",
        nargs="+",
        help="Hedef USB blok aygıtı veya aygıtları (örn. /dev/sdb veya /dev/sdb /dev/sdc).",
    )
    parser.add_argument(
        "-m", "--mode",
        dest="mode",
        choices=["dd", "iso", "windows"],
        default="dd",
        help="Yazma modu: dd (varsayılan), iso, windows.",
    )
    parser.add_argument(
        "-c", "--verify",
        dest="verify",
        action="store_true",
        help="Yazma öncesi hash bütünlüğünü denetle (SHA-256, SHA-512 veya MD5).",
    )
    parser.add_argument(
        "--checksum",
        dest="checksum",
        help="Doğrulanacak beklenen sağlama özeti (MD5, SHA-256 veya SHA-512).",
    )
    parser.add_argument(
        "--algo",
        dest="algo",
        choices=["sha256", "sha512", "md5"],
        help="Sağlama algoritması (varsayılan: otomatik algılama / sha256).",
    )
    parser.add_argument(
        "-p", "--persistence",
        dest="persistence",
        action="store_true",
        help="GNU/Linux ISO modunda Live USB kalıcı depolama (persistence) bölümü oluştur.",
    )
    parser.add_argument(
        "-y", "--yes",
        dest="yes",
        action="store_true",
        help="Onay sorgusunu atla (otomasyon ve betikler için).",
    )
    parser.add_argument(
        "-j", "--json",
        dest="json",
        action="store_true",
        help="İlerleme durumunu stdout üzerine JSON akışı olarak bas.",
    )
    parser.add_argument(
        "-l", "--list",
        dest="list",
        action="store_true",
        help="Bağlı USB aygıtlarını listele ve çık.",
    )
    parser.add_argument(
        "-C", "--catalog",
        dest="catalog",
        action="store_true",
        help="Bulut imaj kataloğundaki resmi işletim sistemlerini listele.",
    )
    parser.add_argument(
        "--cloud-write",
        dest="cloud_write",
        metavar="ID",
        help="Katalogdaki bir işletim sistemini yerel diske indirmeden canlı akışla doğrudan USB'ye yaz.",
    )
    parser.add_argument(
        "-N", "--netboot",
        dest="netboot",
        action="store_true",
        help="Yerel ağ üzerinde PXE / UEFI HTTP Boot kurulum sunucusu modunu başlat.",
    )
    parser.add_argument(
        "--netboot-port",
        dest="netboot_port",
        type=int,
        default=8088,
        help="Netboot sunucusunun dinleyeceği HTTP portu (varsayılan: 8088).",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"Pars Image Writer {get_version()}",
        help="Sürüm bilgisini göster ve çık.",
    )

    args = parser.parse_args()

    # List USB devices
    if args.list:
        handle_device_listing(as_json=args.json)

    # Cloud Catalog listing
    if args.catalog:
        handle_catalog_listing(as_json=args.json)

    # Cloud streaming write directly to USB
    if args.cloud_write:
        handle_cloud_write(args.cloud_write, args.devices, yes=args.yes, as_json=args.json)

    # Netboot micro-server mode
    if args.netboot:
        if not args.file:
            err_msg = "Netboot sunucusu için bir kalıp dosyası belirtilmelidir (-f <kalıp.iso>)."
            if args.json:
                print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
            else:
                sys.stderr.write(f"Hata: {err_msg}\n")
            sys.exit(2)
        handle_netboot(args.file, port=args.netboot_port, as_json=args.json)

    # Validate mandatory arguments for local file writing
    if not args.file or not args.devices:
        err_msg = "Eksik parametre: --file (-f) ve en az bir --device (-d) belirtilmelidir."
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
            parser.print_usage(sys.stderr)
        sys.exit(2)

    iso_path = os.path.abspath(args.file)
    if not os.path.isfile(iso_path):
        err_msg = f"Kalıp dosyası bulunamadı veya normal bir dosya değil: {args.file}"
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    # Check file extensions and compression format
    lower_path = iso_path.lower()
    comp_type = detect_compression(iso_path)
    is_valid_format = any(lower_path.endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS) or (comp_type is not None)
    if not is_valid_format:
        err_msg = "Desteklenmeyen dosya formatı. Desteklenenler: .iso, .img, .raw, .xz, .gz, .zst, .bz2"
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    # Parse and normalize target device paths
    raw_devices = []
    for d_arg in args.devices:
        for part in d_arg.split(","):
            part = part.strip()
            if part:
                if not part.startswith("/dev/"):
                    part = f"/dev/{part}"
                raw_devices.append(part)

    # Deduplicate devices preserving order
    target_devices = []
    seen = set()
    for d in raw_devices:
        if d not in seen:
            seen.add(d)
            target_devices.append(d)

    if not target_devices:
        err_msg = "Geçerli bir hedef USB aygıtı belirtilmedi."
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    # Validate target drives with 5-stage safety filters
    validated_targets = []
    for dev_path in target_devices:
        try:
            block_name = USBDeviceManager.validate_usb_drive(dev_path)
            validated_targets.append((dev_path, block_name))
        except USBDeviceManager.DriveError as error:
            err_msg = f"Güvenlik Engeli ({dev_path}): {error}"
            if args.json:
                print(json.dumps({"event": "error", "message": str(error), "device": dev_path, "code": 3}), flush=True)
            else:
                sys.stderr.write(f"Hata: {err_msg}\n")
            sys.exit(3)

    # Verify integrity if requested
    if args.verify or args.checksum:
        if not verify_integrity(
            iso_path,
            expected_checksum=args.checksum,
            algorithm=args.algo,
            as_json=args.json,
        ):
            sys.exit(1)

    # File size and compression inquiry
    try:
        iso_size = os.path.getsize(iso_path)
    except OSError as err:
        err_msg = f"Dosya boyutu okunamadı: {err}"
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(2)

    uncompressed_size = get_uncompressed_size(iso_path, comp_type) if comp_type else iso_size
    effective_total_size = uncompressed_size if (uncompressed_size and uncompressed_size > 0) else iso_size

    # Confirmation prompt unless --yes
    if not args.yes:
        print("\n" + "=" * 62)
        print(" Pars Image Writer — Yazma Öncesi Bilgilendirme")
        print("=" * 62)
        print(f" Kalıp Dosyası : {iso_path}")
        print(f" Kalıp Boyutu  : {USBDeviceManager.format_size(iso_size)} ({iso_size} bayt)")
        if comp_type:
            uncomp_info = USBDeviceManager.format_size(uncompressed_size) if uncompressed_size else "Bilinmiyor (Dinamik akış)"
            print(f" Sıkıştırma    : {comp_type.upper()} (Anında Akış Açma / Streaming Decompress)")
            print(f" Açılmış Boyut : {uncomp_info}")

        if len(validated_targets) == 1:
            print(f" Hedef Sürücü  : {validated_targets[0][0]} (Aygıt: {validated_targets[0][1]})")
        else:
            print(f" Hedef Sürücüler ({len(validated_targets)} Aygıt - Eşzamanlı Çoklu Yazma İstasyonu):")
            for dev_p, blk in validated_targets:
                print(f"   • {dev_p} (Aygıt: {blk})")

        print(f" Yazma Modu    : {args.mode.upper()}")
        if args.persistence:
            print(" Kalıcılık     : AKTİF (Live Persistence Bölümü Oluşturulacak)")
        print("=" * 62)
        print(" ⚠️  DİKKAT: Seçilen hedef sürücü(ler) üzerindeki TÜM VERİLER")
        print("    KALICI OLARAK SİLİNECEKTİR! Bu işlem GERİ ALINAMAZ.")
        print("=" * 62)

        try:
            choice = input(" Devam etmek istiyor musunuz? [e/H]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nİşlem kullanıcı tarafından iptal edildi.")
            sys.exit(130)

        if choice not in ("e", "evet", "y", "yes"):
            print("İşlem iptal edildi.")
            sys.exit(130)

    # Determine backend script
    mode = args.mode.lower()
    is_windows = "false"
    persistence_flag = "true" if args.persistence else "false"

    if mode == "dd":
        script_file = find_script("ImageWriter.py")
        cmd_args = [iso_path] + [t[0] for t in validated_targets]
    elif mode == "iso":
        if len(validated_targets) > 1:
            err_msg = "ISO hibrit modu yalnızca tek aygıta yazmayı destekler. Çoklu yazma için DD modu kullanılmalıdır."
            if args.json:
                print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
            else:
                sys.stderr.write(f"Hata: {err_msg}\n")
            sys.exit(2)
        script_file = find_script("ISOCopier.py")
        cmd_args = [iso_path, validated_targets[0][0], "false", persistence_flag]
    elif mode == "windows":
        if len(validated_targets) > 1:
            err_msg = "Windows ISO modu yalnızca tek aygıta yazmayı destekler. Çoklu yazma için DD modu kullanılmalıdır."
            if args.json:
                print(json.dumps({"event": "error", "message": err_msg, "code": 2}), flush=True)
            else:
                sys.stderr.write(f"Hata: {err_msg}\n")
            sys.exit(2)
        script_file = find_script("ISOCopier.py")
        cmd_args = [iso_path, validated_targets[0][0], "true", "false"]
    else:
        sys.exit(2)

    # Build command
    if os.geteuid() == 0:
        cmd = [sys.executable, script_file] + cmd_args
    else:
        cmd = ["pkexec", script_file] + cmd_args

    # Setup process with stdin pipe for cooperative cancellation
    try:
        process = Popen(
            cmd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as err:
        err_msg = f"Çalıştırıcı bulunamadı: {err}"
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 1}), flush=True)
        else:
            sys.stderr.write(f"Hata: {err_msg}\n")
        sys.exit(1)

    cancelled = False

    def handle_signal(sig, frame):
        nonlocal cancelled
        cancelled = True
        # Cooperative cancel: closing stdin pipe notifies the writer script
        if process.stdin and not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                pass
        if args.json:
            print(json.dumps({"event": "cancelled", "status": "cancelled"}), flush=True)
        else:
            sys.stderr.write("\nİşlem iptal ediliyor, tamponlar diske yazılıyor...\n")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    tracker = ProgressTracker(effective_total_size)
    multi_count = len(validated_targets)

    if args.json:
        print(
            json.dumps(
                {
                    "event": "start",
                    "file": os.path.basename(iso_path),
                    "devices": [t[1] for t in validated_targets],
                    "total_bytes": effective_total_size,
                    "mode": mode,
                    "compression": comp_type,
                    "multi_write": multi_count > 1,
                }
            ),
            flush=True,
        )
    else:
        multi_info = f" ({multi_count} Diske Eşzamanlı)" if multi_count > 1 else ""
        comp_info = f" [{comp_type.upper()} Akışı]" if comp_type else ""
        print(f"\nYazma işlemi başlatıldı [{mode.upper()} Modu]{multi_info}{comp_info}...")

    last_json_emit = 0
    iso_total_bytes = effective_total_size
    iso_copied_bytes = 0
    iso_tmp_bytes = 0

    # Stream stdout from backend
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            if mode == "dd":
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    written = int(parts[0])
                    total = int(parts[1])
                    if total > 0:
                        tracker.total_bytes = total
                    tracker.update(written)

                    pct = tracker.get_percent()
                    speed = tracker.get_speed_mb()
                    eta = tracker.get_eta_seconds()

                    now = time.monotonic()
                    if args.json:
                        if now - last_json_emit >= 0.25 or pct >= 100.0:
                            last_json_emit = now
                            print(
                                json.dumps(
                                    {
                                        "event": "progress",
                                        "written_bytes": written,
                                        "total_bytes": tracker.total_bytes,
                                        "percent": round(pct, 1),
                                        "speed_mb": round(speed, 1),
                                        "eta_seconds": eta,
                                        "devices": [t[1] for t in validated_targets],
                                    }
                                ),
                                flush=True,
                            )
                    else:
                        print(render_progress_bar(pct, speed, eta, multi_count=multi_count), end="", flush=True)

            else:
                # ISO / Windows ISO mode progress protocol
                if line.startswith("TOTAL_BYTES:"):
                    val = line[len("TOTAL_BYTES:"):]
                    if val.isdigit():
                        iso_total_bytes = int(val)
                        tracker.total_bytes = iso_total_bytes
                elif line.startswith("BYTES:"):
                    val = line[len("BYTES:"):]
                    if val.isdigit():
                        iso_tmp_bytes = int(val)
                        tracker.update(iso_copied_bytes + iso_tmp_bytes)
                elif line.startswith("COPIED:"):
                    parts = line.split(":")
                    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                        iso_copied_bytes += iso_tmp_bytes
                        iso_tmp_bytes = 0
                        tracker.update(iso_copied_bytes)

                pct = tracker.get_percent()
                speed = tracker.get_speed_mb()
                eta = tracker.get_eta_seconds()

                now = time.monotonic()
                if args.json:
                    if now - last_json_emit >= 0.25 or pct >= 100.0:
                        last_json_emit = now
                        print(
                            json.dumps(
                                {
                                    "event": "progress",
                                    "written_bytes": tracker.written_bytes,
                                    "total_bytes": tracker.total_bytes,
                                    "percent": round(pct, 1),
                                    "speed_mb": round(speed, 1),
                                    "eta_seconds": eta,
                                }
                            ),
                            flush=True,
                        )
                else:
                    print(render_progress_bar(pct, speed, eta), end="", flush=True)

    except Exception as exc:
        if not cancelled:
            sys.stderr.write(f"\nİlerleme akışı okunurken hata: {exc}\n")

    # Wait for process exit
    returncode = process.wait()

    if cancelled:
        sys.exit(130)

    if returncode == 0:
        elapsed = time.monotonic() - tracker.start_time
        if args.json:
            print(
                json.dumps(
                    {
                        "event": "completed",
                        "status": "success",
                        "elapsed_seconds": round(elapsed, 1),
                    }
                ),
                flush=True,
            )
        else:
            print(f"\n\n✓ Yazma işlemi başarıyla tamamlandı! (Geçen süre: {format_duration(elapsed)})")
            print("  USB diski güvenle çıkarabilirsiniz.")
        sys.exit(0)

    # Error handling based on exit codes
    stderr_output = process.stderr.read().strip() if process.stderr else ""

    if returncode in (126, 127):
        err_msg = "PolicyKit yetkilendirmesi reddedildi veya yapılamadı."
        if args.json:
            print(json.dumps({"event": "error", "message": err_msg, "code": 126}), flush=True)
        else:
            sys.stderr.write(f"\nHata: {err_msg}\n")
        sys.exit(126)

    err_msg = stderr_output or "Yazma işlemi sırasında bilinmeyen bir hata oluştu."
    if args.json:
        print(json.dumps({"event": "error", "message": err_msg, "code": 1}), flush=True)
    else:
        sys.stderr.write(f"\nHata: {err_msg}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
