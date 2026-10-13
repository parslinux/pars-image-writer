# Pars Image Writer — Değişiklik Günlüğü (CHANGELOG.md)

Bu belgede **Pars Image Writer** projesinin tüm sürüm geçmişi, hata düzeltmeleri ve yeni özellikleri kayıt altına alınmıştır.

Biçim: [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) standardına uygundur.

---

## [1.0.0] - 2026-10-13
### Eklendi
- **Çoklu Eşzamanlı USB Yazma İstasyonu Modu (Broadcast Multi-Write)**: Kalıp dosyasını aynı anda birden fazla USB belleğe eşzamanlı yazma desteği (`ImageWriter.py`, `CLI.py`, `ModernWindow.py`).
- **Doğrudan Akış Açma (Streaming Decompression)**: Zstandard (`.zst`), XZ (`.xz`), Gzip (`.gz`) ve Bzip2 (`.bz2`) sıkıştırılmış kalıplarını geçici disk alanı kullanmadan doğrudan RAM'den açarak diske yazma (`Utils.py`, `ImageWriter.py`, `CLI.py`).
- **Flathub / Flatpak Desteği**: Standart Flatpak manifestosu (`tr.org.pars.ImageWriter.json`), AppStream metadata (`tr.org.pars.ImageWriter.metainfo.xml`) ve paketleme kılavuzu (`docs/FLATPAK_PACKAGING.md`).
- **Bağımsız Headless CLI Geliştirmeleri**: Çoklu hedef aygıt desteği (`-d /dev/sdb /dev/sdc`), anlık disk sayısı göstergesi ve sıkıştırılmış format algılama.
- **GTK4 / Libadwaita Çoklu İstasyon Arayüzü**: Eşzamanlı disk seçim paneli ve canlı sıkıştırma rozetleri.
- **Çoklu Sağlama ve Kalıcılık**: SHA-256, SHA-512, MD5 sağlama desteği ve GNU/Linux Live USB kalıcı depolama (persistence) bölümü.
- **Pars Image Writer Marka ve Kimlik Dönüşümü**: Uygulama mimarisi Pars ekosistemine entegre edildi.
- **Kapsamlı Dokümantasyon Paketi**: `docs/` dizini altında 18 adet standartlaştırılmış teknik, hukuki, mimari ve operasyonel kılavuz oluşturuldu.
- **Mimari Güçlendirme & Hata Yalıtımı**:
  - `copy_dir_with_dd.sh` içerisinde `pv` aracı yokluğunda çökmeyi önleyen saf `dd` fallback desteği eklendi.
  - `ISOCopier.py` için erken GRUB bağımlılık denetimi (`check_grub_prerequisites`) ve universal MMC/NVMe bölüm adlandırması (`get_partition_path`) entegre edildi.
  - ISO (`udf`/`iso9660`) ve USB NTFS (`ntfs3`/`ntfs-3g`/`ntfs`) için çok kademeli montaj kurtarma mimarisi getirildi.
  - Masaüstü indeksleyicilerinin kilitlerini aşmak için `umount -l` (lazy unmount) temizleme mekanizması uygulandı.
  - Çoklu yazma istasyonunda tekil aygıt G/Ç hatalarına karşı aygıt başına hata yalıtımı (fault isolation) sağlandı.
  - `USBDeviceManager.py` çıkarılabilir SD/MMC kartlarını ve harici NVMe kasalarını destekleyecek şekilde genişletildi.
- **Telifsiz Özgün Logo ve Görsel Seti Tasarımı**:
  - `pars-image-writer.svg`, `main.svg`, `iso.svg` ve `disk.svg` simgeleri üçüncü parti miras bağımlılıklardan arındırılarak Pars kimliğine uygun, %100 telifsiz, yüksek çözünürlüklü vektör SVG olarak baştan tasarlandı.
- **Miras Kod Modernizasyonu (Python 3.8+ / 3.10+)**:
  - `Main.py`, `MainWindow.py`, `ISOCopier.py`, `ImageWriter.py`, `USBDeviceManager.py` ve `Utils.py` dosyalarındaki eski `str.format()` ve `%` biçimlendirmeleri modern f-string yapılarına dönüştürüldü.
  - Tip ipuçları (type hints), `pathlib.Path` ve modern `os.path.join` yolları uygulandı.
  - GTK 3.10+ uyumluluğu için kullanım dışı (deprecated) `Gtk.STOCK_*` butonları modern gettext etiketleriyle güncellendi.
  - `Main.py` masaüstü sağ-tık "Birlikte Aç" mekanizması tüm yeni sıkıştırılmış kalıp formatlarını (`.zst`, `.xz`, `.gz`, `.raw`, `.bz2`) tanıyacak şekilde modernize edildi.

---

## [0.9.0] - 2026-08-05
### Güvenlik
- **Güvenlik Açıklarının Kapatılması**: Root süreçlerinde rastgele dosya açılmasını önlemek amacıyla `open_as_caller()` mekanizması devreye alındı.
- **Kritik Bağlantı Noktaları Güvencesi**: Kök dizin (`/`), `/boot`, `/home` vb. sistem bölümlerine yazım engellendi.
- **Güvenli İptal Modeli**: Yetkisiz root kill sinyali yerine `stdin` borusu (pipe) üzerinden güvenli ve disk bütünlüğünü bozmayan sonlandırma mekanizması geliştirildi.

### Eklendi
- **Dinamik Kalan Süre ve Hız Göstergesi**: Son 5 saniyelik kayan pencere (sliding window) algoritmasıyla kararlı `MB/s` ve kalan süre hesaplaması eklendi.
- **Genel Kod İyileştirmesi**: Python 3 modern pratikleri ve tip güvenliği geliştirmeleri yapıldı.

---

## [0.8.3] - 2026-08-04
### Düzeltildi
- Dosya doğrudan açıldığında oluşan `self.usb_device` tanımsızlık hatası giderildi.
- `ImageWriter` hedef sürücüsü yalnızca doğrulanmış USB blok cihazlarıyla sınırlandırıldı.

---

## [0.8.2] - 2025-11-23
### Değiştirildi
- Uygulama simgesi ve ekran görüntüleri güncellendi.
- Eksik `emblem-ok-symbolic` simgesi eklendi.

---

## [0.8.1] - 2024-11-28
### Değiştirildi
- Telif hakları ve lisans bildirimleri güncellendi.

---

## [0.8.0] - 2024-07-16
### Eklendi
- Windows ISO desteği `ISOCopier.py` içerisine entegre edildi.
- İspanyolca (es) dil çevirisi eklendi.
- GRUB paketleri için yazılım merkezi entegrasyonu sağlandı.

### Kaldırıldı
- `rsync` bağımlılığı kaldırıldı, `copy_dir_with_dd.sh` ve `pv` boru hattına geçildi.

---

## [0.7.0] - 2024-02-21
### Geliştirildi
- ISO kopyalama ilerleme çubuğu kullanıcı dostu formata dönüştürüldü.
- Ayrıcalık isteme diyalogları yerini GTK Stack sayfalarına bıraktı.
- Kod tabanı PEP 8 standartlarında `snake_case` fonksiyon isimlendirmeleriyle yeniden biçimlendirildi.

---

## [0.6.0] - 2023-08-20
### Eklendi
- Masaüstü dosyasına `X-Pars-Apps` kategorileri ve arama anahtar kelimeleri eklendi.
- Arayüz boşlukları ve modern simgeler güncellendi.

---

## [0.5.0] - 2023-04-28
### Eklendi
- Portekizce (pt) dil çevirisi eklendi.
- Kodda koruyucu koşullar (guard clauses) kullanılarak iç içe geçmiş `if` blokları sadeleştirildi.
- Otomatik çeviri güncelleme betiği (`update-translations.sh`) eklendi.

---

## [0.4.0] - 2022-07-20
### Eklendi
- İlk Windows ISO modu deneysel desteği.
- Çoklu dil gettext entegrasyonu tamamlandı.

---

## [0.3.0] - 2021-03-02
### Eklendi
- ISO Yazma Modu (`ISOCopier.py`) ile hibrit BIOS & UEFI GRUB desteği.
- PolicyKit üzerinden `ISOCopier` için ayrıcalık kuralı eklendi.
- Windows ISO'ları için Rufus açık kaynaklı `uefi-ntfs.img` desteği dahil edildi.

---

## [0.2.0] - 2020-07-24
### Eklendi
- Çevrimiçi MD5 kontrol mekanizması.
- `pyudev` ile dinamik USB tak-çıkar izleme.
- Yazma bittiğinde sistem bildirimi (Notification) gönderme.
- Güvenli USB çıkarma (`eject`).

---

## [0.1.0] - 2020-06-19
### Eklendi
- İlk açık kaynak sürüm yayınlandı.
- Python 3 + GTK 3 temel arayüzü ve ham DD kopyalama desteği.
