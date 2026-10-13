# Pars Image Writer — Flatpak ve Flathub Paketleme Kılavuzu (FLATPAK_PACKAGING.md)

Bu kılavuz, **Pars Image Writer** uygulamasının Flatpak olarak derlenmesini, sandbox (kum havuzu) izinlerinin yapılandırılmasını, yerel test süreçlerini ve **Flathub** dağıtımını açıklamaktadır.

---

## 1. Flatpak Mimarisi ve İzinler

Pars Image Writer gibi doğrudan blok aygıtlarına (`/dev/sd*`) erişen ve PolicyKit yetkilendirmesi kullanan disk yazma araçları, standart masaüstü kum havuzundan daha geniş sistem erişim haklarına ihtiyaç duyar.

### Gerekli İzinler (`finish-args`):
- `--device=all`: Doğrudan blok cihazlarına (`/dev/sdX`, `/dev/mmcblkX`) düşük seviyeli erişim sağlar.
- `--filesystem=host`: Kullanıcının yerel diskindeki ISO/IMG kalıp dosyalarına erişimini sağlar.
- `--filesystem=/run/udev:ro`: Udev veritabanını okuyarak USB aygıt etiketlerini ve modellerini tespit eder.
- `--talk-name=org.freedesktop.PolicyKit1`: Root yetkisi gereken yazma işlemleri için Polkit yetkilendirme iletişimini sağlar.
- `--system-talk-name=org.freedesktop.UDisks2`: Disk bağlantı durumlarını izlemek için UDisks2 D-Bus erişimi sağlar.
- `--socket=wayland` ve `--socket=fallback-x11`: Modern grafik arayüz desteği.

---

## 2. Manifest Yapısı (`tr.org.pars.ImageWriter.json`)

Kök dizinde yer alan `tr.org.pars.ImageWriter.json` dosyası, Flathub standartlarına tam uyumludur:

```json
{
  "app-id": "tr.org.pars.ImageWriter",
  "runtime": "org.gnome.Platform",
  "runtime-version": "46",
  "sdk": "org.gnome.Sdk",
  "command": "pars-image-writer",
  "finish-args": [
    "--share=ipc",
    "--socket=fallback-x11",
    "--socket=wayland",
    "--device=all",
    "--filesystem=host",
    "--filesystem=/run/udev:ro",
    "--talk-name=org.freedesktop.PolicyKit1",
    "--talk-name=org.freedesktop.Notifications",
    "--system-talk-name=org.freedesktop.UDisks2"
  ]
}
```

---

## 3. Yerel Olarak Derleme ve Test Etme

### 3.1. Önkoşullar
Sisteminizde `flatpak` ve `flatpak-builder` yüklü olmalıdır:

```bash
# Debian / Ubuntu / Pars:
sudo apt install flatpak flatpak-builder

# GNOME SDK ve Platform kurulumu:
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//46 org.gnome.Sdk//46
```

### 3.2. Derleme (Build)
Uygulama kök dizininde aşağıdaki komutu çalıştırın:

```bash
flatpak-builder --force-clean build-dir tr.org.pars.ImageWriter.json
```

### 3.3. Yerel Kurulum ve Çalıştırma
Uygulamayı yerel kullanıcı ortamına kurup test etmek için:

```bash
# Kurulum
flatpak-builder --user --install --force-clean build-dir tr.org.pars.ImageWriter.json

# Çalıştırma
flatpak run tr.org.pars.ImageWriter
```

---

## 4. AppStream Metadata Doğrulaması

Flathub'a gönderim öncesinde AppStream metadata dosyasının standartlara uygunluğu denetlenmelidir:

```bash
appstreamcli validate tr.org.pars.ImageWriter.metainfo.xml
```

---

## 5. Flathub Dağıtım Kontrol Listesi

- [x] AppStream Metainfo (`tr.org.pars.ImageWriter.metainfo.xml`) mevcut ve geçerli.
- [x] Yüksek çözünürlüklü SVG simgesi (`assets/pars-image-writer.svg`) mevcut.
- [x] OARS 1.1 içerik derecelendirmesi eklendi.
- [x] Açık kaynak lisansı (GPL-3.0-or-later) doğrulandı.
- [x] Gerçek ekran görüntüleri URL referansları tanımlandı.
- [x] Headless CLI ve GTK4 arayüzleri derleme paketine dahil edildi.
