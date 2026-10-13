# Pars Image Writer — Geliştirme İlerleme Raporu (progress.md)

Bu belge, **Pars Image Writer** projesinin geliştirme aşamalarını, tamamlanan görevleri, mevcut durumu ve gelecek hedeflerini dinamik olarak izlemektedir.

---

## 1. Genel İlerleme Özeti

- **Proje Durumu**: Kararlı ve Tamamlanmış (Faz 0, 1, 2, 3, 4 ve Faz 5 Tamamlandı)
- **Geçerli Sürüm**: `1.0.0`
- **Dokümantasyon Tamamlanma Oranı**: %100 (18 Kılavuz Belgesi)
- **Kod Tabanı & Çoklu Arayüz Oranı**: %100 (GTK3, GTK4 & Headless CLI)
- **Dağıtım Hazırlığı**: %100 (Debian/Apt & Flathub/Flatpak)

---

## 2. Tamamlanan Aşamalar (Milestones)

### [x] Faz 0: Miras Kod ve Mimari İncelemesi
- [x] `src/Main.py` ve `src/MainWindow.py` arayüz ve kontrol döngüsü incelendi.
- [x] `src/ImageWriter.py` ve `src/ISOCopier.py` root yazma motorları analiz edildi.
- [x] `src/USBDeviceManager.py` disk güvenlik filtreleri ve kritik montaj korumaları doğrulandı.
- [x] Polkit yetki kuralları ve UID düşürme (`open_as_caller`) güvenlik katmanı incelendi.

### [x] Faz 1: Dokümantasyon ve Proje Kimliği Kurulumu
- [x] Kök dizin `.claudeignore` dosyası oluşturuldu.
- [x] Kök dizin `README.md` dosyası modern rozetler ve zengin içerikle güncellendi.
- [x] `docs/` klasörü altında 18 adet standart kılavuz dosyası oluşturuldu.

### [x] Faz 2: Kod Tabanı İsim ve Yapılandırma Entegrasyonu
- [x] `assets/pars-image-writer.svg` simgesi eklendi.
- [x] `pars-image-writer` çalıştırıcı betiği oluşturuldu.
- [x] `tr.org.pars.image-writer.desktop` masaüstü giriş dosyası oluşturuldu.
- [x] `tr.org.pars.pkexec.pars-image-writer.policy` PolicyKit yetkilendirme kuralı eklendi.
- [x] `src/Main.py` uygulama ID (`tr.org.pars.image-writer`) ve program adları güncellendi.
- [x] `src/MainWindow.py` uygulama adı, ikonlar, çeviri alanları ve çift uyumlu yazılım merkezi aracı entegre edildi.
- [x] `src/ISOCopier.py` çalışma dizini (`/run/pars-image-writer`) ve temizlik rutinleri güncellendi.
- [x] `ui/MainWindow.glade` başlık, etiket, telif ve simge referansları Pars Image Writer'a uyarlandı.
- [x] `setup.py` ikili gettext ve çift uyumlu paketleme desteğiyle güncellendi.
- [x] `debian/control` ve `debian/changelog` 1.0.0 sürümüne uyarlandı.
- [x] Çeviri şablonları (`.pot`) ve yerelleştirme dosyaları (`.po`) senkronize edildi.

### [x] Faz 3: Bağımsız Headless CLI Desteği
- [x] Grafik arayüzü olmadan terminalden çalışan `pars-image-writer-cli` aracının geliştirilmesi.
- [x] `src/CLI.py` saf Python modülü olarak mimariye eklendi (GTK/X11 bağımsız).
- [x] Otomatik betiklerde ve web panellerinde kullanılmak üzere `--json` formatında olay akışı desteği.
- [x] CLI_REFERENCE.md ile birebir uyumlu çıkış kodları (`0`, `1`, `2`, `3`, `126`, `130`).
- [x] Çekirdek düzeyinde 5 kademeli disk güvenliği filtresi CLI'ya bağlandı (EUID kontrolü & Polkit entegrasyonu).
- [x] Terminalde dinamik kayan pencere (sliding window) hızlı ANSI ilerleme çubuğu ve kalan süre (ETA).
- [x] `USBDeviceManager.py` udev kütüphanesi olmadan da çalışacak şekilde graceful fallback ile güçlendirildi.
- [x] `setup.py` kurulum yapılandırmasına `pars-image-writer-cli` ve `src/CLI.py` dahil edildi.

### [x] Faz 4: Çoklu Sağlama (Checksum), Kalıcılık & Modern UI
- [x] Yalnızca MD5 değil; SHA-256 ve SHA-512 sağlama desteği (`Utils.calculate_hash`, `MainWindow.py`, `CLI.py`).
- [x] Çevrimiçi `SHA256SUMS` / `MD5SUMS` ve yerel `.sha256` / `.sha512` / `.md5` dosyalarını otomatik algılama.
- [x] GNU/Linux Live USB için kalıcı veri saklama (Live Persistence) bölümü desteği (`ISOCopier.py`, `CLI.py`, `ModernWindow.py`).
- [x] GTK4 ve Libadwaita tabanlı modern, responsive arayüz uygulaması (`src/ModernWindow.py` ve `pars-image-writer-gtk4`).
- [x] GNOME HIG uyumlu AdwClamp, AdwActionRow, AdwComboRow, AdwStatusPage ve açık/koyu tema entegrasyonu.
- [x] `setup.py` kurulum yapılandırmasına GTK4 modern arayüz bileşenlerinin dahil edilmesi.

### [x] Faz 5: İleri Düzey Özellikler & Dağıtım
- [x] **Çoklu Eşzamanlı USB Yazma İstasyonu (Broadcast Multi-Write)**:
  - Tek bir kalıp dosyasını aynı anda birden fazla USB belleğe eşzamanlı ve güvenli yazma (`src/ImageWriter.py`).
  - Terminalden çoklu aygıt desteği: `pars-image-writer-cli -f image.iso -d /dev/sdb /dev/sdc`.
  - GTK4 / Libadwaita arayüzünde "Çoklu USB İstasyonu" açma anahtarı ve dinamik onay paneli (`src/ModernWindow.py`).
- [x] **Doğrudan Akış Açma (Streaming Decompression)**:
  - Zstandard (`.zst`), XZ (`.xz`), Gzip (`.gz`) ve Bzip2 (`.bz2`) formatındaki kalıpları diskte geçici alan kaplamadan doğrudan RAM'den açarak blok aygıtına yazma (`src/Utils.py`, `src/ImageWriter.py`).
  - Açılmamış kalıpların gerçek boyutunu başlık üzerinden anında tespit etme (`get_uncompressed_size`).
  - Hem CLI hem GTK3 hem de GTK4 arayüzlerine sıkıştırılmış format filtrelerinin ve bildirimlerinin entegrasyonu.
- [x] **Flathub / Flatpak Dağıtım Paketi**:
  - Standart Flatpak manifestosu (`tr.org.pars.ImageWriter.json`).
  - AppStream 0.14+ metadata spesifikasyonu (`tr.org.pars.ImageWriter.metainfo.xml`).
  - Flatpak derleme, kum havuzu izinleri ve Flathub yayın kılavuzu (`docs/FLATPAK_PACKAGING.md`).
  - `setup.py` kurulumuna `/usr/share/metainfo` hedefi eklendi.

### [x] Faz 5.5: Mimari Güçlendirme, Dayanıklılık & Hata Yalıtımı (Hardening & Robustness)
- [x] **Kopya Betiğinde Çökme Koruması (`src/copy_dir_with_dd.sh`)**:
  - `pv` aracı kurulu olmadığında `pipefail` hatasıyla çökmesi engellendi; saf `dd` ve dinamik bayt toplayıcısı fallback mekanizması eklendi.
- [x] **Evrensel Bölüm Adlandırma (`get_partition_path`)**:
  - `/dev/sdX1`, `/dev/mmcblk0p1` ve `/dev/nvme0n1p1` için `p` ayracını otomatik yöneten bölüm adlandırma desteği getirildi (`ISOCopier.py`).
- [x] **Erken GRUB Bağımlılık Denetimi (`check_grub_prerequisites`)**:
  - Disk bölüntü tablosunu sıfırlamadan önce `grub-install` ve `/usr/lib/grub/{target}/` varlığı doğrulanarak veri kaybı ve geç safha hataları önlendi.
- [x] **Çok Kademeli Montaj Kurtarma (Mount Cascade Fallback)**:
  - ISO dosyaları için `udf` <-> `iso9660` <-> otomatik algılama kademesi.
  - Hedef USB NTFS bölümleri için `ntfs3` -> `ntfs-3g` -> `ntfs` kademeli sürücü kurtarma mimarisi.
- [x] **Gevşek Çözme (Lazy Unmount `umount -l`) ile Kilitlenme Koruması**:
  - Masaüstü dosya yöneticileri veya dizin indeksleyicilerin neden olduğu `EBUSY` durumlarında `umount -l` ile temiz kaynak serbest bırakma garantisi.
- [x] **Çoklu Yazma İstasyonu Aygıt Başına Hata Yalıtımı (Per-Drive Fault Isolation)**:
  - Yayın akışında hedef disklerden biri çıkarıldığında veya G/Ç (I/O) hatası verdiğinde, diğer sağlıklı disklerin yazımı kesintiye uğramadan devam eder (`ImageWriter.py`).
- [x] **Genişletilmiş SD / MMC / Taşınabilir Depolama Desteği (`USBDeviceManager.py`)**:
  - `/sys/block/sd*`, `/sys/block/mmcblk*` ve `/sys/block/nvme*` aygıtlarını kapsayan, dahili sistem disklerini (eMMC, SATA, NVMe) katı kurallarla koruyan ve çıkarılabilir SD/USB kartları tanıyan aygıt tespit motoru.
- [x] **Özgün ve Telifsiz Vektör Logo Tasarımı (Royalty-Free Asset Redesign)**:
  - Miras Mintstick/Inkscape bağımlılıkları ve izleri temizlendi; %100 özgün, telifsiz ve modern SVG varlıkları tasarlandı:
    - `assets/pars-image-writer.svg`: Modern GNOME HIG uyumlu squircle, optik disk, veri huzmesi ve USB 3.2 ana uygulama simgesi.
    - `assets/main.svg`: GTK3 penceresi ve dokümantasyon için yüksek çözünürlüklü ISO -> Yazma Akışı -> USB başlık banner grafiği.
    - `assets/iso.svg`: Optik kalıp dosyası seçim butonu simgesi.
    - `assets/disk.svg`: USB bellek seçim butonu simgesi.
    - `src/ModernWindow.py` Hakkında penceresi ikon referansı güncellendi.
- [x] **Miras Kod Modernizasyonu (Python 3.8+ / 3.10+)**:
  - `Main.py`, `MainWindow.py`, `ISOCopier.py`, `ImageWriter.py`, `USBDeviceManager.py` ve `Utils.py` genelinde Python 2/eski Python 3 kalıntıları temizlendi.
  - Eski `str.format()` ve `%` biçimlendirmeleri okunabilir, hızlı modern f-string yapılarıyla güncellendi.
  - Tip güvenliği (typing), `pathlib.Path` ve `os.path.join` dosya yolu güvenliği uygulandı.
  - `MainWindow.py` içerisindeki kullanım dışı `Gtk.STOCK_*` butonları modern standart gettext butonlarıyla değiştirildi.
  - `Main.py` masaüstü dosya yöneticisi "Birlikte Aç" kuralı tüm sıkıştırılmış formatları tanıyacak şekilde güncellendi.
- [x] **Tam Dağıtım Bağımsızlığı & Çatallama Beyannamesi (`FORK.md`)**:
  - Kod tabanı, dokümantasyon ve örnek komutlardaki tüm miras dağıtım kalıntıları ve atıfları temizlendi (kod genelinde 0 referans).
  - Projenin kökenini, GPL-3.0 lisans uyumunu, mimari ayrışma ve gelişim tablosunu belgeleyen `docs/FORK.md` ve kök dizin `FORK.md` oluşturuldu.
  - `README.md` dokümantasyon haritasına bağlandı.
- [x] **Yepyeni HiDPI Ekran Görüntüleri & Arayüz Telif Etiketi Temizliği**:
  - `ui/MainWindow.glade` içerisindeki eski miras kurum etiketi `© Pars Developers` olarak güncellendi.
  - `screenshots/pars-image-writer-1.png` (Ana Ekran) ve `screenshots/pars-image-writer-2.png` (Canlı %65 Yazma İşlemi) 2x HiDPI çözünürlükte baştan üretildi; eski arayüz ekran görüntüleri tamamen kaldırıldı.

---

### [x] Faz 6: Bulut Kataloğu ve Ağ Tabanlı Dağıtım (Next-Gen Features)
- [x] **Bulut İmaj Kataloğu (`src/Catalog.py`)**:
  - Pars Linux (Desktop, Minimal), Debian, Ubuntu, Fedora, Arch ve Alpine içeren zengin bulut kalıp kataloğu.
  - Sabit diske veya belleğe indirme yapmadan, HTTP/HTTPS akışını anında USB'ye yazan canlı motor (`stream_download_and_write` — 0 disk/RAM israfı).
  - Canlı SHA-256 sağlama hesaplama ve donanımsal `O_DSYNC` blok eşitlemesi.
- [x] **PXE / UEFI HTTP Boot Ağ Kurulum Sunucusu (`src/NetbootServer.py`)**:
  - USB bellek takmaya gerek kalmadan, LAN üzerindeki bilgisayarları kurabilen gömülü mikro ağ sunucusu.
  - Dinamik iPXE zincirleme yapılandırması ve UEFI HTTP Boot için 206 Byte-Range akış desteği.
- [x] **CLI Uçbirim Entegrasyonu (`src/CLI.py`)**:
  - `--catalog` (`-C`): Bulut kataloğunu tablo veya JSON formatında listeleme.
  - `--cloud-write <ID>`: Kalıbı yerel diske indirmeden doğrudan USB'ye canlı yazma.
  - `--netboot` (`-N`): Seçili ISO için anında LAN kurulum sunucusu başlatma.
- [x] **Modern GTK4 Arayüz Entegrasyonu (`src/ModernWindow.py`)**:
  - Arayüze "Bulut Kataloğu..." butonu, filtreli arama penceresi ve tek tıkla canlı yazma entegrasyonu.
  - Başlık çubuğuna entegre "Ağ Kurulum Sunucusu (Netboot)" butonu ve canlı yayın penceresi.
- [x] **Paketleme & Kurulum**:
  - `setup.py` kurulumuna `Catalog.py` ve `NetbootServer.py` modülleri dahil edildi.

