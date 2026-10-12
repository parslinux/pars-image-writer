# Pars Image Writer — Claude & AI Ajan Geliştirici Kılavuzu (CLAUDE.md)

Bu kılavuz; Claude, Gemini ve diğer otonom AI kodlama asistanlarının **Pars Image Writer** kod tabanında güvenli, tutarlı ve etkili çalışabilmesi için özel olarak hazırlanmıştır.

---

## 1. Kod Tabanı Genel Özeti

Pars Image Writer, Python 3 ve GTK+ 3 (PyGObject) ile geliştirilmiş, Polkit ve Udev entegrasyonuna sahip bir sistem aracıdır.

- **Ana Dizin**: `/src/`
  - `Main.py`: Uygulama yaşam döngüsü (`Gtk.Application`).
  - `MainWindow.py`: Grafik arayüz ve süreç orkestrasyonu.
  - `USBDeviceManager.py`: Udev dinleme ve kritik disk güvenlik filtreleri.
  - `ImageWriter.py`: Ham (DD) blok kopyalama motoru (Root - `pkexec`).
  - `ISOCopier.py`: Bölümleme, dosya kopyalama ve GRUB kurulum motoru (Root - `pkexec`).
  - `Utils.py`: Güvenli UID düşürme (`open_as_caller`), IPC ve sinyal kontrolü.
  - `copy_dir_with_dd.sh`: `find`, `pv` ve `dd` boru hattı.
- **Arayüz**: `/ui/MainWindow.glade` (Glade XML formatında).
- **Varlıklar**: `/assets/` (SVG simgeler ve `uefi-ntfs.img`).
- **Paketleme**: `/setup.py` ve `/debian/`.

---

## 2. Temel Geliştirme ve Çalıştırma Komutları

```bash
# Bağımlılıkları kontrol et / kur (Debian/Ubuntu/Pars)
sudo apt install -y python3-gi gir1.2-gtk-3.0 python3-requests python3-pyudev parted dosfstools ntfs-3g pv eject

# Uygulamayı kaynak koddan doğrudan çalıştır
python3 src/Main.py

# Belirli bir ISO ile başlat
python3 src/Main.py /path/to/test.iso

# Dil dosyalarını güncelle ve derle
./update-translations.sh
python3 setup.py build

# Kod biçimlendirme ve lint kontrolü
black --line-length 100 src/
flake8 src/

# Debian paketini derle
gbp buildpackage -us -uc
```

---

## 3. Kodlama Standartları ve İlkeleri

1. **PEP 8 Uyumluluğu**: Tüm Python kodları PEP 8 standartlarına uygun, `snake_case` fonksiyon/değişken adları ve 4 boşluk girintileme kullanmalıdır.
2. **Kritik Güvenlik Kuralı**:
   - `ImageWriter.py` ve `ISOCopier.py` root yetkisiyle çalıştığı için dışarıdan gelen hiçbir dosya yolu ya da disk parametresine doğrudan güvenilmez.
   - Dosya okuma işlemleri her zaman `Utils.open_as_caller()` ile çağrıcı kullanıcının haklarına düşürülerek yapılmalıdır.
   - Asla `shell=True` ile `subprocess` çalıştırılmamalıdır; komutlar liste dizisi (`["cmd", "arg"]`) olarak verilmelidir.
3. **Diski Koruma Garantisi**:
   - Asla `/dev/sda` veya sistem disklerine otomatik yazım kodu eklenmemelidir.
   - Test senaryolarında mutlaka döngü aygıtları (`losetup`) veya RAM disk kullanılmalıdır.
4. **Çoklu Dil (Gettext)**:
   - Arayüzdeki tüm kullanıcıya açık metinler `_("Metin")` fonksiyonu ile sarmalanmalıdır.
   - Glade arayüzündeki etiketlerde `translatable="yes"` özelliği korunmalıdır.

---

## 4. İletişim ve Süreç İptali (IPC) Standartları

- Root motorları (`ImageWriter.py`, `ISOCopier.py`), GUI ile **yalnızca stdout** üzerindeki biçimlendirilmiş satırlar üzerinden konuşur.
- Tanısal veya hata mesajları kesinlikle **stderr**'e basılmalıdır (`Utils.log()`), aksi takdirde GUI ilerleme yüzdesini yanlış ayrıştırır.
- Kullanıcı iptal ettiğinde GUI `stdin` borusunu kapatır; motorlar `watch_stdin_for_cancel()` ile bunu yakalar ve diski `sync` ederek temiz biçimde sonlandırır.
