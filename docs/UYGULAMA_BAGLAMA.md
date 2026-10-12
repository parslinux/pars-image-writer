# Pars Image Writer — Masaüstü ve Sistem Uygulama Bağlama Kılavuzu (UYGULAMA_BAGLAMA.md)

Bu doküman, **Pars Image Writer** uygulamasının Linux masaüstü ortamlarına (GNOME, KDE Plasma, XFCE, Cinnamon, MATE), dosya yöneticilerine ve sistem servislerine nasıl bağlandığını (integration / binding) açıklamaktadır.

---

## 1. Masaüstü Kısayolu ve Menü Entegrasyonu (.desktop)

Uygulamanın sistem menüsünde görünmesini ve arama çubuğunda bulunmasını sağlayan XDG standart dosya:
`/usr/share/applications/tr.org.pars.image-writer.desktop`

```ini
[Desktop Entry]
Name=Pars Image Writer
Name[tr]=Pars Disk Kalıbı Yazıcı
GenericName=Image Writer
GenericName[tr]=Disk Kalıbı Yazıcı
Comment=Writes ISO and IMG files to USB disks
Comment[tr]=ISO ve IMG Kalıplarını USB Belleklere Yazar
Exec=pars-image-writer %f
Icon=pars-image-writer
Terminal=false
Type=Application
Categories=System;X-Pars-Apps;Utility;
MimeType=application/x-cd-image;application/x-raw-disk-image;
StartupNotify=true
Keywords=image;iso;img;writer;disk;usb;burn;pars;piw;kalip;yazici;
```

### Önemli Alanlar:
- `Exec=pars-image-writer %f`: Dosya yöneticisinden bir ISO dosyası tıklandığında veya sürüklendiğinde dosya yolunu uygulamaya `%f` parametresiyle aktarır.
- `MimeType=...`: Dosya yöneticisi sağ tık menüsünde "Bununla Aç" seçeneğini bağlar.
- `Icon=pars-image-writer`: Sistem ikon temasından ilgili simgeyi çeker.

---

## 2. Dosya Yöneticilerinde Sağ Tık Menüsü Bağlama (MIME Type)

Kullanıcıların bir `.iso` veya `.img` dosyasına sağ tıkladığında "Pars Disk Kalıbı Yazıcı ile Aç" seçeneğini görebilmesi için MIME veritabanı güncellenir:

```bash
# MIME ilişkisini kullanıcı bazında veya sistem genelinde güncelle:
sudo update-desktop-database /usr/share/applications
```

### Desteklenen Dosya Yöneticileri:
- **Nautilus (GNOME)**: Doğrudan `MimeType` tanımıyla çalışır.
- **Thunar (XFCE)**: Özel Eylem (Custom Action) eklemek istenirse:
  - Komut: `pars-image-writer %f`
  - Dosya Deseni: `*.iso;*.img`
- **Dolphin (KDE Plasma)**: Servis menüsü (`ServiceMenus`) veya varsayılan uygulama ayarları üzerinden otomatik bağlanır.

---

## 3. PolicyKit (Polkit) Yetkilendirme Bağlantısı

Uygulama arayüzü normal kullanıcı haklarıyla açılırken, diske yazma işlemi için root hakları gerekir. Bu işlem PolicyKit eylemleri ile bağlanır:

`/usr/share/polkit-1/actions/tr.org.pars.pkexec.pars-image-writer.policy`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <vendor>Pars Developers</vendor>
  <vendor_url>https://pars.org.tr/</vendor_url>

  <!-- DD Ham Yazma Modu -->
  <action id="tr.org.pars.pkexec.pars-image-writer-dd-mode">
    <description>Run Pars Image Writer DD Mode</description>
    <message>Authentication is required to run Pars Image Writer</message>
    <message xml:lang="tr">Pars Disk Kalıbı Yazıcı için yetkilendirme gerekiyor</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/share/pars/pars-image-writer/src/ImageWriter.py</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>

  <!-- ISO Bölümleme Modu -->
  <action id="tr.org.pars.pkexec.pars-image-writer-iso-mode">
    <description>Run Pars Image Writer ISO Mode</description>
    <message>Authentication is required to run Pars Image Writer</message>
    <message xml:lang="tr">Pars Disk Kalıbı Yazıcı için yetkilendirme gerekiyor</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/share/pars/pars-image-writer/src/ISOCopier.py</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
```

---

## 4. İkon Teması Bağlantısı (Hicolor Icon Theme)

Uygulamanın farklı masaüstü çözünürlüklerinde keskin ve net görünmesi için ölçeklenebilir vektör simgesi (`.svg`) sisteme kaydedilir:

```bash
# Simgelerin kopyalanacağı yol:
/usr/share/icons/hicolor/scalable/apps/pars-image-writer.svg

# İkon önbelleğini güncelle:
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor
```

---

## 5. Sistem Bildirimleri (Desktop Notifications)

Yazma işlemi tamamlandığında veya hata oluştuğunda Freedesktop Notification spesifikasyonu üzerinden masaüstü kabuğuna (GNOME Shell, KDE KNotification) bildirim fırlatılır:

```python
notification = Gio.Notification.new(_("Writing process is finished."))
notification.set_body(os.path.basename(self.iso_file_path) + " | " + _("You can eject the USB disk."))
notification.set_icon(Gio.ThemedIcon(name="pars-image-writer"))
self.application.send_notification(self.application.get_application_id(), notification)
```
