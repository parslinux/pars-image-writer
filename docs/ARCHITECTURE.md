# Pars Image Writer — Sistem Mimarisi Belgesi (ARCHITECTURE.md)

Bu doküman, **Pars Image Writer** uygulamasının dahili yazılım mimarisini, bileşenler arası veri akışını, ayrıcalık ayrımı (privilege separation) güvenlik modelini ve düşük seviyeli disk I/O operasyonlarını detaylandırmaktadır.

---

## 1. Mimari Genel Bakış

Pars Image Writer; Python 3, GTK 3, Polkit (pkexec) ve Linux çekirdek altyapılarını (`sysfs`, `udev`, `block layer`) harmanlayan çok katmanlı bir masaüstü sistem aracıdır.

Uygulamanın temel felsefesi:
- **En Az Ayrıcalık Prensibi (Principle of Least Privilege)**: Kullanıcı arayüzü (GUI) sıradan kullanıcı haklarıyla çalışır. Sadece diske blok düzeyinde yazım yapan motorlar `pkexec` vasıtasıyla root haklarına yükseltilir.
- **Sıfır Güven (Zero Trust IPC)**: GUI katmanından root betiklerine iletilen her parametre (dosya yolu, aygıt adı) root tarafında baştan ve bağımsız olarak doğrulanır.
- **Donanımsal Bütünlük & Çekirdek Senkronizasyonu**: Sahte RAM tampon hızlarının önüne geçmek için doğrudan eşzamanlı I/O (`O_DSYNC`) kullanılır.

```
+-----------------------------------------------------------------------+
|                         KULLANICI ALANI (Kullanıcı UID)                |
|                                                                       |
|  [ Masaüstü Dosya Yöneticisi ] ----> [ src/Main.py (Gtk.Application) ] |
|                                                    |                  |
|                                                    v                  |
|                                         [ src/MainWindow.py ]         |
|                                          /       |       \            |
|       [ ui/MainWindow.glade ] <---------+        |        +-------->  |
|       (Arayüz Bileşenleri)                       |    [ USBDeviceMgr ]|
|                                                  |    (pyudev / sysfs)|
+--------------------------------------------------|--------------------+
                                                   |
                             pkexec (Polkit)       | stdin pipe / stdout
                                                   v
+-----------------------------------------------------------------------+
|                          KÖK ALANI (Root - UID 0)                     |
|                                                                       |
|             +-------------------------------------------+             |
|             |          Ortak Doğrulama & Utils         |             |
|             |  - USBDeviceManager.validate_usb_drive()  |             |
|             |  - Utils.open_as_caller() (Drop UID)      |             |
|             |  - Utils.watch_stdin_for_cancel()         |             |
|             +-------------------------------------------+             |
|                                  |                                    |
|                  +---------------+---------------+                    |
|                  |                               |                    |
|                  v                               v                    |
|        [ src/ImageWriter.py ]          [ src/ISOCopier.py ]           |
|        (Raw DD Block Engine)           (ISO Partition & GRUB)         |
|                  |                               |                    |
|                  |                     [ copy_dir_with_dd.sh ]        |
|                  |                     [ grub-install & UEFI ]        |
|                  v                               v                    |
|        +-------------------------------------------------+            |
|        |           Hedef Blok Aygıtı (/dev/sdX)          |            |
|        +-------------------------------------------------+            |
+-----------------------------------------------------------------------+
```

---

## 2. Bileşen Analizi

### 2.1. `src/Main.py` — Uygulama Giriş Noktası
- **Sorumluluk**: Uygulama yaşam döngüsünü yönetmek ve tekil örnek (single-instance) politikasını sürdürmek.
- **Teknoloji**: `gi.repository.Gtk.Application`, `Gio.ApplicationFlags.HANDLES_OPEN`.
- **İşleyiş**:
  - `application_id`: `tr.org.pars.image-writer`.
  - `do_open()` metoduyla dosya yöneticisinden sağ tıkla gelen `.iso` ve `.img` argümanlarını yakalar ve `MainWindow`'a aktarır.

### 2.2. `src/MainWindow.py` — Durum Makinesi ve UI Denetleyicisi
- **Sorumluluk**: Kullanıcı etkileşimi, aygıt listeleme, yazma modu seçimi, arka plan süreçlerinin başlatılması ve ilerleme takibi.
- **İlerleme Algoritması (Sliding Window)**:
  - `SPEED_WINDOW_SECONDS = 5.0` ve `MIN_SPEED_SECONDS = 1.0` sabitleriyle bir çift uçlu kuyruk (`deque`) tutar.
  - Anlık CPU/I/O patlamalarının hız göstergesini saptırmasını engellemek için son 5 saniyenin ortalama veri aktarım hızını hesaplar:
    $$\text{Hız} = \frac{\Delta \text{Yazılan Bayt}}{\Delta \text{Geçen Süre}}$$
- **İptal Mekanizması**:
  - GUI tarafı root sürecini `SIGKILL` veya `kill` ile sonlandırmaz (yetkisiz kullanıcı root'u öldüremez).
  - Bunun yerine GUI, oluşturduğu `stdin` borusunu (`close_writer_stdin()`) kapatır. Root sürecindeki `watch_stdin_for_cancel` thread'i `EOF` algılayarak diski `sync` eder ve güvenle çıkar.

### 2.3. `src/USBDeviceManager.py` — Donanım Algılama ve Koruma Kalkanı
- **Sorumluluk**: Takılan USB depolama birimlerini tespit etmek ve sistem disklerini korumak.
- **udev Dinleyicisi**: `MonitorObserver` arka plan iş parçacığıyla `block` alt sistemindeki `disk` olaylarını anlık dinler.
- **Güvenlik Filtreleri (`validate_usb_drive`)**:
  1. **Yol Doğrulaması**: Yalnızca `/dev/sd[a-z]` biçimindeki doğrudan blok cihazlarını kabul eder; sembolik bağlar veya göreceli yollar (`/dev/../sda`) reddedilir.
  2. **USB Veriyolu Kontrolü**: `/sys/block/<name>` dizininin gerçek yolunda `usb` terimi bulunmalıdır. NVMe (`/dev/nvme*`) ve dahili SATA diskler kesinlikle reddedilir.
  3. **Kritik Bağlantı Noktaları (Critical Mount Points)**: Disk veya herhangi bir bölümü aşağıdaki sistem dizinlerine bağlıysa işlem anında engellenir:
     ```python
     CRITICAL_MOUNT_POINTS = (
         "/", "/boot", "/boot/efi", "/efi", "/etc", "/home",
         "/opt", "/srv", "/tmp", "/usr", "/usr/local", "/var", "/var/log"
     )
     ```
  4. **Swap Kontrolü**: `/proc/swaps` taranır; diskin herhangi bir bölümü takas alanı olarak etkinse işlem reddedilir.
  5. **Device Mapper (LVM/LUKS/RAID)**: `/sys/block/<name>/holders/` dizininde aktif bağlayıcı varsa işlem engellenir.

### 2.4. `src/ImageWriter.py` — Ham DD Yazma Motoru
- **Sorumluluk**: Kalıp dosyasını bayt bayt hedef blok aygıtına (veya çoklu aygıtlara) yazmak.
- **Düşük Seviyeli Bayraklar**:
  - `O_WRONLY | O_EXCL | O_CLOEXEC | O_DSYNC`
  - `O_EXCL`: Diskin başka bir süreç tarafından tutulmadığını veya yeni bir bağlama yapılmadığını çekirdek düzeyinde kilitler.
  - `O_DSYNC`: Her `write()` çağrısının çekirdek disk önbelleğinde değil, doğrudan USB flaş denetleyicisinde tamamlanmasını zorunlu kılar.
- **Tampon Boyutu**: `BUFFER_SIZE = 4 * 1024 * 1024` (4 MiB).
- **Çoklu Eşzamanlı Yazma (Broadcast Multi-Write)**:
  - Tek bir kaynak okumasıyla (`read(BUFFER_SIZE)`), veriyi açılmış olan tüm hedef blok aygıtlarına (`drive_files`) döngü içinde eşzamanlı yazar.
  - Her disk yazımı bağımsız olarak senkronize edilir ve tüm sürücüler güvenle `eject` edilir.
- **Doğrudan Akış Açma (Streaming Decompression)**:
  - Zstandard (`.zst`), XZ (`.xz`), Gzip (`.gz`) ve Bzip2 (`.bz2`) formatındaki sıkıştırılmış kalıplar diskte geçici alan kaplamadan doğrudan RAM tamponu üzerinden decompress edilerek blok aygıtına yazılır.

### 2.5. `src/ISOCopier.py` — Bölümleme ve GRUB Önyükleyici Motoru
- **Sorumluluk**: Bölümlendirilmiş, dosya sistemi tabanlı önyüklenebilir USB hazırlamak.
- **Çalışma Adımları**:
  1. `parted` ile `msdos` (MBR) bölümleme tablosu yazılır.
  2. **GNU/Linux Modu**:
     - 1. Bölüm: FAT32 (`mkfs.vfat`), `boot` bayrağı aktif.
     - ISO içeriği `copy_dir_with_dd.sh` ile kopyalanır.
     - `grub-install --target=i386-pc` (BIOS) ve `grub-install --target=x86_64-efi --removable` (UEFI) çalıştırılır.
  3. **Windows Modu**:
     - 1. Bölüm: NTFS (`mkfs.ntfs`) — Windows kurulum dosyaları için.
     - 2. Bölüm: FAT32 UEFI — Rufus açık kaynak projesinden alınan `assets/uefi-ntfs.img` kalıbı `dd` ile yazılarak UEFI üzerinden NTFS sürücüsünü yükleyen aracı sürücü oluşturulur.
     - Windows `bootmgr` zinciri GRUB üzerinden yapılandırılır.

### 2.6. `src/Utils.py` — Ayrıcalık Yönetimi ve Süreç Güvenliği
- **`open_as_caller(path, flags)`**:
  - Root olarak çalışan betiğin, kullanıcının erişemeyeceği bir dosyayı (örneğin `/etc/shadow`) okuyup diske yazmasını önler.
  - `os.environ["PKEXEC_UID"]` üzerinden çağıran kullanıcının gerçek UID ve GID'sine geçici olarak düşer (`os.setresuid`, `os.setresgid`), dosyayı açar, dosya tanıtıcısını (`fd`) alır ve tekrar root haklarına döner.
- **`detect_compression(filepath)` & `open_decompressed_stream(raw_file, comp_type)`**:
  - Dosya magic byte'ları ve uzantıları üzerinden sıkıştırma türünü algılar.
  - Sıkıştırılmış dosya tanıtıcısını şeffaf bir ikili akışa (binary streaming reader) sararak RAM tasarruflu decompress hattı kurar.
- **`get_uncompressed_size(filepath, comp_type)`**:
  - Dosyayı tamamen açmadan dosya başlıklarından veya araçlarından (`xz -l`, `zstd -l`, gzip trailer) açılmış boyutunu tespit eder.

---

## 3. Süreçler Arası İletişim (IPC) Protokolü

Root alt süreçleri ile GUI arasındaki haberleşme standart akışlar (stdout/stderr) üzerinden metin tabanlı basit ve sağlam bir protokolle sağlanır:

### DD Modu stdout Protokolü
```text
<yazılan_bayt> <toplam_bayt>
Örnek:
104857600 4294967296
209715200 4294967296
```

### ISO Modu stdout Protokolü
```text
TOTAL_BYTES:<toplam_bayt>
BYTES:<anlık_aktarılan_bayt>
COPIED:<tamamlanan_dosya_sayısı>:<toplam_dosya_sayısı>
```

---

## 4. Güvenlik ve Tehdit Modeli Analizi

| Tehdit | Olası Sonuç | Mimari Önlem |
|---|---|---|
| Kötü niyetli ISO dosyası ile yetki yükseltme | Root yetkisinde rastgele dosya okuma | `Utils.open_as_caller()` ile UID çağıran kullanıcıya düşürülür. |
| Dahili sistem diskine yazma | İşletim sisteminin ve verilerin yok olması | `USBDeviceManager.validate_usb_drive()` çok katmanlı denetimi. |
| Monteli dosya sistemine yazma | Dosya sistemi bozulması | `unmount_drive()` ile tüm bölümler zorunlu `umount` edilir, `O_EXCL` ile kilitlenir. |
| Sahte progress / takılma | Kullanıcının erken diski çekmesi | `O_DSYNC` ve `fsync()` ile gerçek zamanlı donanım yazımı sağlanır. |
| Yetkisiz `kill` komutu istismarı | Sistem süreçlerini sonlandırma açığı | `stdin` borusu kapatılarak kooperatif iptal mekanizması kullanılır. |
