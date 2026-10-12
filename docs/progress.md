# Pars Image Writer — Geliştirme İlerleme Raporu (progress.md)

Bu belge, **Pars Image Writer** projesinin geliştirme aşamalarını, tamamlanan görevleri, mevcut durumu ve gelecek hedeflerini dinamik olarak izlemektedir.

---

## 1. Genel İlerleme Özeti

- **Proje Durumu**: Aktif Geliştirme (Faz 1 ve Faz 2 Tamamlandı)
- **Geçerli Sürüm**: `1.0.0`
- **Dokümantasyon Tamamlanma Oranı**: %100
- **Kod Dönüşüm Tamamlanma Oranı**: %100

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
- [x] `docs/` klasörü altında 17 adet standart kılavuz dosyası oluşturuldu.

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

---

## 3. Gelecek Yol Haritası (Roadmap)

### [ ] Faz 3: Bağımsız Headless CLI Desteği
- [ ] Grafik arayüzü olmadan terminalden çalışan `pars-image-writer-cli` aracının geliştirilmesi.
- [ ] Otomatik betiklerde kullanılmak üzere `--json` formatında ilerleme çıktısı desteği.

### [ ] Faz 4: Çoklu Sağlama (Checksum) & Modern UI
- [ ] Yalnızca MD5 değil; SHA-256 ve SHA-512 sağlama desteği.
- [ ] GTK4 ve Libadwaita tabanlı modern ve responsive arayüz prototipi.
- [ ] Kalıcılık (persistence) bölümü desteği (Live USB üzerinde veri saklama).
