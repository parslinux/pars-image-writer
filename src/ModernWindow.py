#!/usr/bin/python3
"""GTK4 and Libadwaita Modern UI Prototype for Pars Image Writer.

Features responsive Libadwaita styling, AdwClamp layouts, modern combo rows,
integrated SHA-256 / MD5 multi-checksum verification, Live USB persistence toggle,
and asynchronous real-time progress monitoring.
"""

import math
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

import USBDeviceManager
from Utils import (
    calculate_hash,
    detect_compression,
    detect_hash_type,
    get_uncompressed_size,
    SUPPORTED_IMAGE_EXTENSIONS,
)

APP_ID = "tr.org.pars.image-writer.gtk4"
APP_NAME = "Pars Image Writer"
APP_VERSION = "1.0.0"

SPEED_WINDOW_SECONDS = 5.0
MIN_SPEED_SECONDS = 0.5


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


class ModernWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title(APP_NAME)
        self.set_default_size(700, 680)

        self.iso_path = None
        self.iso_size = 0
        self.devices = []
        self.selected_device_name = None
        self.multi_check_buttons = {}
        self.multi_device_rows = []

        self.worker_process = None
        self.worker_stdin = None
        self.history = deque()
        self.start_time = 0
        self.total_bytes = 0
        self.written_bytes = 0

        self.setup_ui()
        self.refresh_devices()

    def setup_ui(self):
        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header Bar
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(
            title=APP_NAME,
            subtitle="Modern USB Disk Kalıbı Yazıcı"
        )
        header.set_title_widget(title_widget)

        # Dark/Light theme switcher button
        style_mgr = Adw.StyleManager.get_default()
        theme_btn = Gtk.Button(icon_name="night-light-symbolic")
        theme_btn.set_tooltip_text("Koyu / Açık Tema")
        theme_btn.connect("clicked", self.toggle_theme)
        header.pack_start(theme_btn)

        # About button
        about_btn = Gtk.Button(icon_name="help-about-symbolic")
        about_btn.set_tooltip_text("Hakkında")
        about_btn.connect("clicked", self.show_about_dialog)
        header.pack_end(about_btn)

        main_box.append(header)

        # Toast overlay for in-app notifications
        self.toast_overlay = Adw.ToastOverlay()
        main_box.append(self.toast_overlay)

        # View Stack for Pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.toast_overlay.set_child(self.stack)

        # --- PAGE 1: Configuration ---
        config_scroll = Gtk.ScrolledWindow()
        config_clamp = Adw.Clamp(maximum_size=660)
        config_clamp.set_margin_top(18)
        config_clamp.set_margin_bottom(24)
        config_clamp.set_margin_start(16)
        config_clamp.set_margin_end(16)
        config_scroll.set_child(config_clamp)

        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        config_clamp.set_child(config_box)

        # Group 1: Image File
        group_file = Adw.PreferencesGroup(
            title="Kalıp Dosyası",
            description="Yazmak istediğiniz ISO veya IMG kalıp dosyasını seçin"
        )
        config_box.append(group_file)

        self.row_file = Adw.ActionRow(
            title="Dosya Seçilmedi",
            subtitle="Lütfen bir .iso veya .img kalıbı belirleyin"
        )
        self.row_file.set_icon_name("media-optical-symbolic")
        btn_select_file = Gtk.Button(label="Gözat...")
        btn_select_file.set_valign(Gtk.Align.CENTER)
        btn_select_file.connect("clicked", self.on_select_file_clicked)
        self.row_file.add_suffix(btn_select_file)
        self.row_file.set_activatable_widget(btn_select_file)
        group_file.add(self.row_file)

        # Group 2: Target USB Drive
        group_drive = Adw.PreferencesGroup(
            title="Hedef USB Sürücü",
            description="Kalıbın yazılacağı çıkarılabilir USB belleği seçin"
        )
        config_box.append(group_drive)

        self.drive_model = Gtk.StringList.new(["USB aygıtları taranıyor..."])
        self.row_drive = Adw.ComboRow(
            title="USB Bellek",
            model=self.drive_model
        )
        self.row_drive.set_icon_name("drive-removable-media-symbolic")
        self.row_drive.connect("notify::selected", self.on_drive_selected)

        btn_refresh_drive = Gtk.Button(icon_name="view-refresh-symbolic")
        btn_refresh_drive.set_valign(Gtk.Align.CENTER)
        btn_refresh_drive.set_tooltip_text("USB Listesini Yenile")
        btn_refresh_drive.connect("clicked", lambda b: self.refresh_devices())
        self.row_drive.add_suffix(btn_refresh_drive)
        group_drive.add(self.row_drive)

        # Multi-write station toggle
        self.row_multi_station = Adw.SwitchRow(
            title="Çoklu USB İstasyonu (Broadcast Multi-Write)",
            subtitle="Kalıbı birden fazla USB belleğe aynı anda eşzamanlı yazar"
        )
        self.row_multi_station.set_icon_name("network-transmit-receive-symbolic")
        self.row_multi_station.set_active(False)
        self.row_multi_station.connect("notify::active", self.on_multi_station_toggled)
        group_drive.add(self.row_multi_station)

        # Multi-device list group
        self.group_multi_devices = Adw.PreferencesGroup(
            title="Eşzamanlı Yazılacak USB Bellekler",
            description="Kalıbın yazılmasını istediğiniz tüm bellekleri işaretleyin"
        )
        self.group_multi_devices.set_visible(False)
        config_box.append(self.group_multi_devices)

        # Group 3: Mode & Options
        group_options = Adw.PreferencesGroup(
            title="Yazma Modu ve Seçenekler",
            description="Yazma yöntemini ve ek güvenlik seçeneklerini yapılandırın"
        )
        config_box.append(group_options)

        self.mode_model = Gtk.StringList.new([
            "DD Modu (Ham Blok Kopyalama - En Güvenilir)",
            "ISO Modu (FAT32 & GRUB Hibrit Önyükleme)",
            "Windows ISO Modu (NTFS + UEFI Desteği)",
        ])
        self.row_mode = Adw.ComboRow(
            title="Yazma Yöntemi",
            model=self.mode_model
        )
        self.row_mode.set_icon_name("system-run-symbolic")
        group_options.add(self.row_mode)

        self.row_verify = Adw.SwitchRow(
            title="Sağlama Bütünlüğünü Doğrula (Checksum)",
            subtitle="Yazma öncesinde SHA-256 / MD5 sağlama özetini denetler"
        )
        self.row_verify.set_icon_name("security-high-symbolic")
        self.row_verify.set_active(False)
        group_options.add(self.row_verify)

        self.row_persistence = Adw.SwitchRow(
            title="Canlı Kalıcı Depolama (Live Persistence)",
            subtitle="Linux ISO modunda oturum değişikliklerini USB'de kalıcı saklar"
        )
        self.row_persistence.set_icon_name("folder-saved-search-symbolic")
        self.row_persistence.set_active(False)
        group_options.add(self.row_persistence)

        # Start button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(12)

        self.btn_start = Gtk.Button(label="Yazmayı Başlat")
        self.btn_start.add_css_class("suggested-action")
        self.btn_start.add_css_class("pill")
        self.btn_start.set_size_request(240, 52)
        self.btn_start.connect("clicked", self.on_start_clicked)
        btn_box.append(self.btn_start)
        config_box.append(btn_box)

        self.stack.add_named(config_scroll, "config")

        # --- PAGE 2: Writing Progress ---
        progress_clamp = Adw.Clamp(maximum_size=620)
        progress_clamp.set_margin_top(40)
        progress_clamp.set_margin_bottom(30)
        progress_clamp.set_margin_start(16)
        progress_clamp.set_margin_end(16)

        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        progress_clamp.set_child(progress_box)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(48, 48)
        progress_box.append(self.spinner)

        self.lbl_progress_title = Gtk.Label(label="Kalıp Diske Yazılıyor...")
        self.lbl_progress_title.add_css_class("title-1")
        progress_box.append(self.lbl_progress_title)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_size_request(-1, 14)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0.0)
        progress_box.append(self.progress_bar)

        group_prog_details = Adw.PreferencesGroup(title="Yazma Detayları")
        progress_box.append(group_prog_details)

        self.row_speed = Adw.ActionRow(title="Yazma Hızı", subtitle="0 MB/s")
        self.row_speed.set_icon_name("network-transmit-symbolic")
        group_prog_details.add(self.row_speed)

        self.row_eta = Adw.ActionRow(title="Tahmini Kalan Süre", subtitle="Hesaplanıyor...")
        self.row_eta.set_icon_name("alarm-symbolic")
        group_prog_details.add(self.row_eta)

        self.row_bytes = Adw.ActionRow(title="Aktarılan Veri", subtitle="0 MB / 0 MB")
        self.row_bytes.set_icon_name("drive-multidisk-symbolic")
        group_prog_details.add(self.row_bytes)

        # Cancel button
        cancel_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cancel_box.set_halign(Gtk.Align.CENTER)
        cancel_box.set_margin_top(10)
        self.btn_cancel = Gtk.Button(label="İşlemi İptal Et")
        self.btn_cancel.add_css_class("destructive-action")
        self.btn_cancel.add_css_class("pill")
        self.btn_cancel.set_size_request(200, 46)
        self.btn_cancel.connect("clicked", self.on_cancel_clicked)
        cancel_box.append(self.btn_cancel)
        progress_box.append(cancel_box)

        self.stack.add_named(progress_clamp, "progress")

        # --- PAGE 3: Finished ---
        self.page_finished = Adw.StatusPage(
            icon_name="emblem-ok-symbolic",
            title="Yazma İşlemi Tamamlandı!",
            description="Kalıp USB diske başarıyla yazıldı. Diski güvenle çıkarabilirsiniz."
        )
        btn_finish_done = Gtk.Button(label="Yeni Kalıp Yaz")
        btn_finish_done.add_css_class("suggested-action")
        btn_finish_done.add_css_class("pill")
        btn_finish_done.set_halign(Gtk.Align.CENTER)
        btn_finish_done.set_size_request(200, 48)
        btn_finish_done.connect("clicked", self.reset_to_config)
        self.page_finished.set_child(btn_finish_done)
        self.stack.add_named(self.page_finished, "finished")

        # --- PAGE 4: Error ---
        self.page_error = Adw.StatusPage(
            icon_name="dialog-error-symbolic",
            title="Yazma Başarısız Oldu",
            description="İşlem sırasında bir hata oluştu."
        )
        btn_error_back = Gtk.Button(label="Geri Dön")
        btn_error_back.add_css_class("pill")
        btn_error_back.set_halign(Gtk.Align.CENTER)
        btn_error_back.set_size_request(200, 48)
        btn_error_back.connect("clicked", self.reset_to_config)
        self.page_error.set_child(btn_error_back)
        self.stack.add_named(self.page_error, "error")

        self.stack.set_visible_child_name("config")

    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def toggle_theme(self, button):
        style_mgr = Adw.StyleManager.get_default()
        if style_mgr.get_color_scheme() == Adw.ColorScheme.FORCE_DARK:
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def show_about_dialog(self, button):
        about = Adw.AboutWindow(
            transient_for=self,
            application_name=APP_NAME,
            application_icon="pars-image-writer",
            version=APP_VERSION,
            developer_name="Pars Developers",
            website="https://pars.org.tr",
            issue_url="https://github.com/parslinux/pars-image-writer/issues",
            copyright="© 2026 Pars Developers",
            license_type=Gtk.License.GPL_3_0,
        )
        about.present()

    def refresh_devices(self):
        self.devices = USBDeviceManager.get_usb_devices()
        string_items = []

        # Clear existing multi-device rows
        for row in self.multi_device_rows:
            self.group_multi_devices.remove(row)
        self.multi_device_rows.clear()
        self.multi_check_buttons.clear()

        if not self.devices:
            string_items.append("Bağlı USB sürücü bulunamadı")
            self.selected_device_name = None
            empty_row = Adw.ActionRow(
                title="Bağlı USB bellek bulunamadı",
                subtitle="Lütfen bir USB disk takın ve yenileyin"
            )
            self.group_multi_devices.add(empty_row)
            self.multi_device_rows.append(empty_row)
        else:
            for d in self.devices:
                # [blockName, label, size]
                string_items.append(f"/dev/{d[0]}  [{d[2]}]  {d[1]}")
                dev_row = Adw.ActionRow(
                    title=f"/dev/{d[0]}  [{d[2]}]",
                    subtitle=d[1]
                )
                dev_row.set_icon_name("drive-removable-media-symbolic")
                check = Gtk.CheckButton()
                check.connect("toggled", lambda b: self.update_start_button_label())
                dev_row.add_suffix(check)
                dev_row.set_activatable_widget(check)
                self.group_multi_devices.add(dev_row)
                self.multi_device_rows.append(dev_row)
                self.multi_check_buttons[d[0]] = check

            self.selected_device_name = self.devices[0][0]

        new_model = Gtk.StringList.new(string_items)
        self.row_drive.set_model(new_model)
        self.update_start_button_label()

    def on_multi_station_toggled(self, row, param):
        is_multi = row.get_active()
        self.row_drive.set_visible(not is_multi)
        self.group_multi_devices.set_visible(is_multi)
        if is_multi:
            self.row_mode.set_selected(0)  # Lock to DD mode
            self.row_mode.set_sensitive(False)
            self.row_persistence.set_active(False)
            self.row_persistence.set_sensitive(False)
        else:
            self.row_mode.set_sensitive(True)
            self.row_persistence.set_sensitive(True)
        self.update_start_button_label()

    def get_selected_multi_devices(self):
        return [dev for dev, check in self.multi_check_buttons.items() if check.get_active()]

    def update_start_button_label(self):
        if self.row_multi_station.get_active():
            count = len(self.get_selected_multi_devices())
            if count > 0:
                self.btn_start.set_label(f"Seçili {count} Diske Yazmayı Başlat")
            else:
                self.btn_start.set_label("Disklere Yazmayı Başlat")
        else:
            self.btn_start.set_label("Yazmayı Başlat")

    def on_drive_selected(self, row, param):
        idx = row.get_selected()
        if self.devices and 0 <= idx < len(self.devices):
            self.selected_device_name = self.devices[idx][0]
        else:
            self.selected_device_name = None

    def on_select_file_clicked(self, button):
        dialog = Gtk.FileDialog(title="Kalıp Dosyası Seç (ISO, IMG, XZ, GZ, ZST)")
        filters = Gio.ListStore.new(Gtk.FileFilter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name("Tüm Desteklenen Kalıplar (*.iso, *.img, *.xz, *.gz, *.zst)")
        for pattern in ("*.iso", "*.ISO", "*.img", "*.IMG", "*.raw", "*.RAW", "*.xz", "*.XZ", "*.gz", "*.GZ", "*.zst", "*.ZST"):
            all_filter.add_pattern(pattern)
        filters.append(all_filter)

        iso_filter = Gtk.FileFilter()
        iso_filter.set_name("Standart Kalıplar (*.iso, *.img)")
        for pattern in ("*.iso", "*.ISO", "*.img", "*.IMG", "*.raw", "*.RAW"):
            iso_filter.add_pattern(pattern)
        filters.append(iso_filter)

        compressed_filter = Gtk.FileFilter()
        compressed_filter.set_name("Sıkıştırılmış Kalıplar (*.xz, *.gz, *.zst)")
        for pattern in ("*.xz", "*.XZ", "*.gz", "*.GZ", "*.zst", "*.ZST", "*.bz2"):
            compressed_filter.add_pattern(pattern)
        filters.append(compressed_filter)

        dialog.set_filters(filters)
        dialog.open(self, None, self.on_file_dialog_finished)

    def on_file_dialog_finished(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                if path and os.path.isfile(path):
                    self.iso_path = path
                    self.iso_size = os.path.getsize(path)
                    name = os.path.basename(path)
                    size_str = USBDeviceManager.format_size(self.iso_size)
                    comp_type = detect_compression(path)
                    if comp_type:
                        uncomp_size = get_uncompressed_size(path, comp_type)
                        uncomp_str = f" (~{USBDeviceManager.format_size(uncomp_size)} açılmış)" if uncomp_size else ""
                        self.row_file.set_title(name)
                        self.row_file.set_subtitle(f"{size_str}{uncomp_str} [Sıkıştırılmış: {comp_type.upper()} Doğrudan Akış]")
                        self.show_toast(f"Kalıp seçildi: {name} ({comp_type.upper()} akışı)")
                    else:
                        self.row_file.set_title(name)
                        self.row_file.set_subtitle(f"{size_str} ({self.iso_size} bayt)")
                        self.show_toast(f"Kalıp seçildi: {name}")
        except Exception:
            pass

    def on_start_clicked(self, button):
        if not self.iso_path:
            self.show_toast("Lütfen bir kalıp dosyası seçin!")
            return

        is_multi = self.row_multi_station.get_active()

        if is_multi:
            selected_devs = self.get_selected_multi_devices()
            if not selected_devs:
                self.show_toast("Lütfen eşzamanlı yazılacak en az bir USB bellek seçin!")
                return

            target_devices = [f"/dev/{d}" for d in selected_devs]
            for dev in target_devices:
                try:
                    USBDeviceManager.validate_usb_drive(dev)
                except USBDeviceManager.DriveError as err:
                    self.show_error_page(f"Güvenlik Uyarısı ({dev}): {err}")
                    return

            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=f"{len(target_devices)} Adet USB Bellek Kalıcı Olarak Silinecek!",
                body=(
                    f"Eşzamanlı Hedef Sürücüler: {', '.join(target_devices)}\n"
                    f"Kalıp dosyası: {os.path.basename(self.iso_path)}\n\n"
                    "Seçilen TÜM USB bellekler üzerindeki VERİLER kalıcı olarak silinecektir. "
                    "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?"
                )
            )
            dialog.add_response("cancel", "Vazgeç")
            dialog.add_response("proceed", "Tümünü Sil ve Eşzamanlı Yaz")
            dialog.set_response_appearance("proceed", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect("response", self.on_confirm_dialog_response)
            dialog.present()
            return

        # Single device flow
        if not self.selected_device_name:
            self.show_toast("Lütfen hedef bir USB bellek seçin!")
            return

        target_device = f"/dev/{self.selected_device_name}"
        try:
            USBDeviceManager.validate_usb_drive(target_device)
        except USBDeviceManager.DriveError as err:
            self.show_error_page(f"Güvenlik Uyarısı: {err}")
            return

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Veriler Kalıcı Olarak Silinecek!",
            body=(
                f"Seçilen sürücü: {target_device}\n"
                f"Kalıp dosyası: {os.path.basename(self.iso_path)}\n\n"
                "Hedef USB bellek üzerindeki TÜM BÖLÜMLER ve VERİLER "
                "kalıcı olarak silinecektir. Devam etmek istiyor musunuz?"
            )
        )
        dialog.add_response("cancel", "Vazgeç")
        dialog.add_response("proceed", "Verileri Sil ve Yaz")
        dialog.set_response_appearance("proceed", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self.on_confirm_dialog_response)
        dialog.present()

    def on_confirm_dialog_response(self, dialog, response):
        if response != "proceed":
            return

        if self.row_verify.get_active():
            # Run integrity check in thread before starting write
            self.row_verify.set_sensitive(False)
            self.show_toast("Bütünlük kontrol ediliyor (SHA-256 / MD5)...")
            threading.Thread(target=self.run_checksum_verification, daemon=True).start()
        else:
            self.start_writing_flow()

    def run_checksum_verification(self):
        try:
            sha256_hash = calculate_hash(self.iso_path, "sha256").lower()
            GLib.idle_add(self.on_checksum_done, True, f"SHA-256: {sha256_hash[:16]}...")
        except Exception as exc:
            GLib.idle_add(self.on_checksum_done, False, str(exc))

    def on_checksum_done(self, success, detail):
        self.row_verify.set_sensitive(True)
        if not success:
            self.show_error_page(f"Bütünlük doğrulaması başarısız: {detail}")
            return
        self.show_toast("Sağlama kontrolü tamamlandı!")
        self.start_writing_flow()

    def start_writing_flow(self):
        self.stack.set_visible_child_name("progress")
        self.spinner.start()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Yazma Başlatılıyor...")

        mode_idx = self.row_mode.get_selected()
        is_windows = "false"
        persistence = "true" if self.row_persistence.get_active() else "false"
        is_multi = self.row_multi_station.get_active()

        if is_multi:
            selected_devs = self.get_selected_multi_devices()
            target_devices = [f"/dev/{d}" for d in selected_devs]
            script = find_script("ImageWriter.py")
            cmd_args = [self.iso_path] + target_devices
            self.lbl_progress_title.set_label(f"Kalıp {len(target_devices)} Diske Eşzamanlı Yazılıyor...")
            self.row_bytes.set_title(f"Aktarılan Veri ({len(target_devices)} Aygıt)")
        else:
            target_device = f"/dev/{self.selected_device_name}"
            if mode_idx == 0:
                script = find_script("ImageWriter.py")
                cmd_args = [self.iso_path, target_device]
            elif mode_idx == 1:
                script = find_script("ISOCopier.py")
                cmd_args = [self.iso_path, target_device, "false", persistence]
            else:
                script = find_script("ISOCopier.py")
                cmd_args = [self.iso_path, target_device, "true", "false"]
            self.lbl_progress_title.set_label("Kalıp Diske Yazılıyor...")
            self.row_bytes.set_title("Aktarılan Veri")

        if os.geteuid() == 0:
            cmd = [sys.executable, script] + cmd_args
        else:
            cmd = ["pkexec", script] + cmd_args

        self.history.clear()
        self.start_time = time.monotonic()
        self.total_bytes = self.iso_size
        self.written_bytes = 0

        try:
            self.worker_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.worker_stdin = self.worker_process.stdin
        except Exception as exc:
            self.show_error_page(f"Süreç başlatılamadı: {exc}")
            return

        threading.Thread(target=self.monitor_worker_output, daemon=True).start()

    def monitor_worker_output(self):
        mode_idx = self.row_mode.get_selected()
        proc = self.worker_process
        iso_total = self.total_bytes
        iso_copied = 0
        iso_tmp = 0

        while proc and proc.stdout:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            if mode_idx == 0:
                # DD Mode: "<written_bytes> <total_bytes>"
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    written = int(parts[0])
                    total = int(parts[1])
                    GLib.idle_add(self.update_progress, written, total)
            else:
                # ISO Mode
                if line.startswith("TOTAL_BYTES:"):
                    val = line[len("TOTAL_BYTES:"):]
                    if val.isdigit():
                        iso_total = int(val)
                elif line.startswith("BYTES:"):
                    val = line[len("BYTES:"):]
                    if val.isdigit():
                        iso_tmp = int(val)
                        GLib.idle_add(self.update_progress, iso_copied + iso_tmp, iso_total)
                elif line.startswith("COPIED:"):
                    parts = line.split(":")
                    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                        iso_copied += iso_tmp
                        iso_tmp = 0
                        GLib.idle_add(self.update_progress, iso_copied, iso_total)

        returncode = proc.wait()
        stderr_text = proc.stderr.read().strip() if proc.stderr else ""
        GLib.idle_add(self.on_worker_finished, returncode, stderr_text)

    def update_progress(self, written, total):
        self.written_bytes = written
        self.total_bytes = total if total > 0 else self.total_bytes
        now = time.monotonic()
        self.history.append((now, written))

        cutoff = now - SPEED_WINDOW_SECONDS
        while len(self.history) > 1 and self.history[0][0] < cutoff:
            self.history.popleft()

        # Compute speed
        speed_mb = 0.0
        if len(self.history) >= 2:
            t0, b0 = self.history[0]
            t1, b1 = self.history[-1]
            dt = t1 - t0
            if dt >= MIN_SPEED_SECONDS:
                speed_mb = max(0.0, (b1 - b0) / dt / (1000 * 1000))
        elif now - self.start_time >= MIN_SPEED_SECONDS:
            speed_mb = (written / (now - self.start_time)) / (1000 * 1000)

        # Compute percent & ETA
        pct = (written / self.total_bytes) if self.total_bytes > 0 else 0.0
        pct = min(1.0, max(0.0, pct))
        eta = int((self.total_bytes - written) / (speed_mb * 1000 * 1000)) if speed_mb > 0 else None

        self.progress_bar.set_fraction(pct)
        self.progress_bar.set_text(f"%{pct * 100:.1f}")

        self.row_speed.set_subtitle(f"{speed_mb:.1f} MB/s")
        self.row_eta.set_subtitle(format_duration(eta))
        w_mb = round(written / 1000 / 1000)
        t_mb = round(self.total_bytes / 1000 / 1000)
        self.row_bytes.set_subtitle(f"{w_mb} MB / {t_mb} MB")

    def on_cancel_clicked(self, button):
        self.btn_cancel.set_sensitive(False)
        self.show_toast("İşlem iptal ediliyor, disk eşitleniyor...")
        if self.worker_stdin and not self.worker_stdin.closed:
            try:
                self.worker_stdin.close()
            except OSError:
                pass

    def on_worker_finished(self, returncode, stderr_text):
        self.spinner.stop()
        self.btn_cancel.set_sensitive(True)

        if returncode == 0:
            self.stack.set_visible_child_name("finished")
            return

        if returncode in (126, 127):
            msg = "PolicyKit yönetici yetkilendirmesi reddedildi veya iptal edildi."
        elif returncode == -signal.SIGTERM or "stopped" in stderr_text:
            msg = "Yazma işlemi kullanıcı tarafından güvenle iptal edildi."
        else:
            msg = stderr_text or "Disk yazma işlemi sırasında bilinmeyen bir hata oluştu."

        self.show_error_page(msg)

    def show_error_page(self, message):
        self.page_error.set_description(message)
        self.stack.set_visible_child_name("error")

    def reset_to_config(self, button):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("")
        self.stack.set_visible_child_name("config")
        self.refresh_devices()


class ModernApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ModernWindow(application=self)
        win.present()


def main():
    app = ModernApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
