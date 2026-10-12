# Pars Image Writer — Kurulum ve Derleme Kılavuzu (INSTALL.md)

Bu doküman, **Pars Image Writer** uygulamasının farklı GNU/Linux dağıtımlarında kaynak koddan çalıştırılması, sistem paketlerinin kurulması ve dağıtım paketlerinin (.deb vb.) derlenmesi adımlarını açıklar.

---

## 1. Sistem Gereksinimleri

### Asgari Donanım
- **İşlemci**: x86_64, aarch64 veya armhf mimarisi.
- **Bellek (RAM)**: Minimum 512 MB (1 GB önerilir).
- **Depolama**: Uygulama için ~50 MB boş alan.
- **Arayüz**: GTK+ 3 destekleyen herhangi bir pencere yöneticisi / masaüstü ortamı (GNOME, XFCE, KDE Plasma, Cinnamon, MATE).

### Çekirdek ve Sistem Gereksinimleri
- Linux Çekirdeği 4.15 veya üzeri (NTFS yazımı için `ntfs3` modülü veya `ntfs-3g` kullanıcısı).
- Systemd / Udev ve PolicyKit (polkit-1) servisleri etkin olmalıdır.

---

## 2. Paket Bağımlılıkları

### Çalışma Zamanı (Runtime) Bağımlılıkları
Uygulamanın çalışması için aşağıdaki paketlerin sistemde kurulu olması şarttır:

| Paket Adı (Debian / Ubuntu / Pars) | Açıklama |
|---|---|
| `python3` (>= 3.6) | Temel programlama dili ortamı |
| `python3-gi` | Python GObject Introspection kütüphanesi |
| `gir1.2-gtk-3.0` | GTK+ 3 grafik kütüphanesi |
| `gir1.2-glib-2.0` | GLib / GIO sistem kütüphanesi |
| `python3-requests` | HTTP istemcisi (çevrimiçi hash doğrulaması için) |
| `python3-pyudev` | Python udev aygıt izleme kütüphanesi |
| `parted` | Disk bölümleme aracı |
| `dosfstools` | FAT32 dosya sistemi oluşturucu (`mkfs.vfat`) |
| `ntfs-3g` | NTFS dosya sistemi desteği (`mkfs.ntfs`) |
| `pv` | Pipe viewer (veri aktarım hız ve ilerleme takibi) |
| `eject` | Yazma sonrası USB diski güvenle çıkarma aracı |
| `udev` | Donanım olay yöneticisi |
| `policykit-1` veya `polkitd` | Root yetkilendirmesi (`pkexec`) |

### İsteğe Bağlı (Opsiyonel) Bağımlılıklar
- `grub-pc-bin` ve `grub-efi-amd64-bin`: ISO Modunda (GNU/Linux) önyüklenebilir disk hazırlamak için gereklidir.

---

## 3. Dağıtımlara Göre Kurulum Adımları

### 3.1. Debian, Ubuntu, Pars ve Linux Mint

Gerekli bağımlılıkları yükleyin:
```bash
sudo apt update
sudo apt install -y \
    gir1.2-glib-2.0 \
    gir1.2-gtk-3.0 \
    python3-gi \
    python3-requests \
    python3-pyudev \
    parted \
    dosfstools \
    ntfs-3g \
    pv \
    eject \
    udev \
    policykit-1 \
    grub-pc-bin \
    grub-efi-amd64-bin
```

### 3.2. Arch Linux ve Manjaro

```bash
sudo pacman -Syu --needed \
    python \
    python-gobject \
    gtk3 \
    python-requests \
    python-pyudev \
    parted \
    dosfstools \
    ntfs-3g \
    pv \
    polkit \
    grub
```

### 3.3. Fedora ve Red Hat Enterprise Linux (RHEL)

```bash
sudo dnf install -y \
    python3 \
    python3-gobject \
    gtk3 \
    python3-requests \
    python3-pyudev \
    parted \
    dosfstools \
    ntfs-3g \
    pv \
    polkit \
    grub2-pc-modules \
    grub2-efi-x64-modules
```

---

## 4. Kaynak Koddan Çalıştırma

Geliştirme veya test amacıyla uygulamayı derlemeden doğrudan çalıştırabilirsiniz:

1. Depoyu yerel makinenize klonlayın:
   ```bash
   git clone https://github.com/pars/pars-image-writer.git
   cd pars-image-writer
   ```

2. Uygulama arayüzünü başlatın:
   ```bash
   python3 src/Main.py
   ```

3. Belirli bir ISO dosyasını doğrudan açarak başlatmak için:
   ```bash
   python3 src/Main.py /home/kullanici/Downloads/pars-os-23.iso
   ```

---

## 5. Sistem Çapında Kurulum (`setup.py` ile)

Uygulamanın sistem genelinde (`/usr/bin/`, `/usr/share/` vb.) kurulması için `setup.py` kullanılabilir:

```bash
# Dil çevirilerini (.mo) derleyip sisteme kurar:
sudo python3 setup.py install --prefix=/usr --install-layout=deb
```

Bu işlem şu dosyaları ilgili sistem dizinlerine yerleştirir:
- Çalıştırılabilir betik: `/usr/bin/pars-image-writer`
- Masaüstü kısayolu: `/usr/share/applications/tr.org.pars.image-writer.desktop`
- Polkit Yetki Kuralı: `/usr/share/polkit-1/actions/tr.org.pars.pkexec.pars-image-writer.policy`
- Kaynak kod ve arayüz: `/usr/share/pars/pars-image-writer/`
- İkonlar: `/usr/share/icons/hicolor/scalable/apps/`
- Dil Çevirileri: `/usr/share/locale/*/LC_MESSAGES/`

---

## 6. Debian (.deb) Paketi Oluşturma

Projeyi resmi bir Debian/Pars paketi olarak derlemek için `git-buildpackage` ve `devscripts` araçları kullanılır:

1. Gerekli derleme araçlarını yükleyin:
   ```bash
   sudo apt install -y devscripts git-buildpackage debhelper dh-python
   ```

2. Paket derleme bağımlılıklarını otomatik yükleyin:
   ```bash
   sudo mk-build-deps -ir
   ```

3. Paketi derleyin:
   ```bash
   gbp buildpackage --git-export-dir=/tmp/build/pars-image-writer -us -uc
   ```

4. Üretilen `.deb` paketini kurun:
   ```bash
   sudo dpkg -i /tmp/build/pars-image-writer/pars-image-writer_*.deb
   # Eksik bağımlılık olursa tamamlamak için:
   sudo apt install -f
   ```

---

## 7. Kurulum Sonrası Kontrol ve Sorun Giderme

### Polkit Yetkilendirme Testi
Uygulama çalışırken root parolası istemiyorsa veya yetkilendirme hatası veriyorsa Polkit kuralının yerinde olduğunu doğrulayın:
```bash
ls -la /usr/share/polkit-1/actions/*image-writer.policy
```

### udev Kuralları Kontrolü
USB bellek takıldığında algılanmıyorsa sistem udev daemon'unun çalıştığından emin olun:
```bash
systemctl status systemd-udevd
```
