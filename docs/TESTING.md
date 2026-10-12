# Pars Image Writer — Test ve Doğrulama Kılavuzu (TESTING.md)

Disk yazma araçları doğrudan blok aygıtlarıyla (`/dev/sdX`) çalıştığından, geliştirme aşamasında yapılacak en küçük bir hata veri kaybına yol açabilir. Bu nedenle **Pars Image Writer**, gerçek donanım diski gerektirmeyen izole ve güvenli test yöntemleri üzerine kurgulanmıştır.

---

## 1. Güvenli Test Mimarisi: Sanal Disk Simülasyonu

Gerçek bir USB diski feda etmeden ve ana işletim sisteminizi riske atmadan test yapmanın en güvenli yolu **Linux Çekirdeği `scsi_debug` modülü** veya **Loopback aygıtları (`losetup`)** kullanmaktır.

### 1.1. `scsi_debug` ile Gerçekçi USB Disk Simülasyonu (Önerilen)

`scsi_debug` çekirdek modülü, sistemde tak-çıkar USB depolama birimi gibi davranan sanal bir SCSI aygıtı oluşturur:

```bash
# 4 GB boyutunda sanal bir USB sürücü oluştur:
sudo modprobe scsi_debug dev_type=0 dev_size_mb=4096

# dmesg çıktısından oluşturulan aygıtı (örneğin /dev/sdd) öğrenin:
dmesg | tail -n 10

# Test bittikten sonra sanal aygıtı kaldır:
sudo rmmod scsi_debug
```

### 1.2. Dosya Tabanlı Loopback (`losetup`) ile Test

Küçük test kalıpları için sanal bir imaj dosyası oluşturup loop cihazı olarak bağlayabilirsiniz:

```bash
# 1. 2GB boş bir imaj dosyası üret
truncate -s 2G /tmp/test_usb.raw

# 2. Döngü aygıtı olarak bağla
sudo losetup -fP /tmp/test_usb.raw

# 3. Hangi loop aygıtı olduğunu öğren (örnek: /dev/loop0)
losetup -a
```

---

## 2. Yazma Motorlarının Birim Testleri

### 2.1. Test Kalıbı (Dummy ISO) Üretimi
Gerçek bir 4GB dağıtım ISO'su yerine testlerde saniyeler içinde oluşturulan kukla (dummy) imajlar kullanılır:

```bash
# 500 MB boyutunda rastgele veri içeren test ISO'su:
dd if=/dev/urandom of=/tmp/dummy.iso bs=1M count=500
```

### 2.2. `ImageWriter.py` (DD Modu) Manuel Doğrulama
```bash
# Root yetkisiyle sanal cihaza yazımı başlat:
sudo python3 src/ImageWriter.py /tmp/dummy.iso /dev/sdd

# Çıktı formatının doğrulanması:
# 0 524288000
# ...
# 524288000 524288000
```

Yazılan verinin doğruluğunu `cmp` veya `sha256sum` ile kıyaslayın:
```bash
cmp -n 524288000 /tmp/dummy.iso /dev/sdd && echo "Bayt doğrulaması BAŞARILI!"
```

---

## 3. QEMU ile Sanal Makinede Önyükleme (Boot) Doğrulaması

Yazılan USB diskin gerçekten önyüklenebilir (bootable) olup olmadığını doğrulamak için QEMU sanal makinesi kullanılır:

### BIOS Modunda Test:
```bash
sudo qemu-system-x86_64 -m 2048 -drive file=/dev/sdd,format=raw
```

### UEFI Modunda Test (OVMF ile):
```bash
sudo apt install -y ovmf
sudo qemu-system-x86_64 -m 2048 \
    -bios /usr/share/ovmf/OVMF.fd \
    -drive file=/dev/sdd,format=raw
```

Eğer GRUB menüsü veya işletim sistemi kurulum ekranı açılıyorsa yazma işlemi %100 başarılıdır.

---

## 4. Statik Kod Analizi ve Lint Kontrolleri

Geliştirilen her yeni özelliğin kod kalitesi standart araçlarla denetlenmelidir:

```bash
# 1. Kod Biçimi (Black)
black --check --line-length 100 src/

# 2. Hata ve Standart Denetimi (Flake8)
flake8 src/ --max-line-length=100 --ignore=E203,W503

# 3. Tip Güvenliği (Mypy)
mypy src/Main.py src/MainWindow.py
```
