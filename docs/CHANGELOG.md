# Pars Image Writer — Değişiklik Günlüğü (CHANGELOG.md)

Bu belgede **Pars Image Writer** projesinin tüm sürüm geçmişi, hata düzeltmeleri ve yeni özellikleri kayıt altına alınmıştır.

Biçim: [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) standardına uygundur.

---

## [1.0.0-dev] - 2026-10-12
### Eklendi
- **Pars Image Writer Marka ve Kimlik Dönüşümü**: Uygulama mimarisi Pars ekosistemine entegre edildi.
- **Kapsamlı Dokümantasyon Paketi**: `docs/` dizini altında 17 adet standartlaştırılmış teknik, hukuki, mimari ve operasyonel kılavuz oluşturuldu.
- **Gelişmiş AI ve Geliştirici Desteği**: Kök dizin `.claudeignore` ve `CLAUDE.md` geliştirici kılavuzu eklendi.
- **Özel Yansıma ve Sunucu Desteği**: `SELF_HOSTING_GUIDE.md` ile kurum içi yerel ayna sunucusu mimarisi belgelendi.
- **Bağımsız CLI Tasarımı**: Headless kullanım için komut satırı referansı (`CLI_REFERENCE.md`) hazırlandı.

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
