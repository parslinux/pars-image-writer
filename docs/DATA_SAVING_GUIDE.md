# Pars Image Writer — Veri Güvenliği ve Disk Koruma Kılavuzu (DATA_SAVING_GUIDE.md)

Bu kılavuz, **Pars Image Writer** uygulamasının yanlış disk seçimlerini önlemek, veri kayıplarını engellemek ve donanım düzeyinde yazma bütünlüğünü sağlamak için uyguladığı güvenlik katmanlarını ve kullanıcılara yönelik en iyi uygulamaları ele almaktadır.

---

## 1. Veri Kaybını Önleyen 5 Kademeli Güvenlik Kalkanı

Bir disk yazma aracında en büyük felaket, kullanıcının ana işletim sisteminin kurulu olduğu dahili sabit diski veya harici yedekleme diskini hedef olarak seçmesidir. Pars Image Writer, bunu engellemek için **5 bağımsız çekirdek düzeyinde doğrulama** uygular:

```
[Kullanıcı Hedef Diski Seçer]
         │
         ▼
[1. Basamak] Yol Doğrulaması (Yalnızca /dev/sd* izinli, sembolik bağlar yasak)
         │  (Başarılı)
         ▼
[2. Basamak] Veriyolu Denetimi (/sys/block/*/device yolu 'usb' içermeli; NVMe/SATA yasak)
         │  (Başarılı)
         ▼
[3. Basamak] Kritik Mount Koruması (/, /boot, /home, /var vb. sistem bağları yasak)
         │  (Başarılı)
         ▼
[4. Basamak] Aktif Takas (Swap) Koruması (/proc/swaps taranır, aktif swap yasak)
         │  (Başarılı)
         ▼
[5. Basamak] Device-Mapper Koruması (LVM, LUKS, RAID bağımlılıkları taranır)
         │  (Başarılı)
         ▼
[ÖZEL ERİŞİM KİLİDİ: O_EXCL ile Aygıtı Donanımsal Kilitle] ──► [GÜVENLİ YAZMA]
```

### 1. Yol Doğrulaması (`get_block_name`)
- Yalnızca doğrudan `/dev/sdX` sözdizimini kabul eder.
- `..` içeren manipülatif dizin yolları (`/dev/../dev/sda`) veya geçici sembolik linkler baştan reddedilir.

### 2. Yalnızca Çıkarılabilir USB Diskler (`find_usb_block_names`)
- Hedef aygıtın `/sys/block/<name>` konumu incelenir.
- Gerçek donanım yolu USB veri yolu üzerinden geçmiyorsa (örneğin dahili NVMe SSD veya anakarta bağlı SATA sabit disk), aygıt arayüzde dahi listelenmez ve doğrudan reddedilir.

### 3. Kritik Bağlantı Noktaları Koruması (`CRITICAL_MOUNT_POINTS`)
- Hedef disk veya herhangi bir alt bölümü işletim sisteminin hayati dizinlerine (`/`, `/boot`, `/home`, `/etc`, `/var`, `/usr`) bağlıysa işlem derhal durdurulur:
  ```python
  CRITICAL_MOUNT_POINTS = (
      "/", "/boot", "/boot/efi", "/efi", "/etc", "/home",
      "/opt", "/srv", "/tmp", "/usr", "/usr/local", "/var", "/var/log"
  )
  ```

### 4. Aktif Takas Alanı (Swap) Denetimi (`get_swap_devices`)
- Takas alanları `/proc/self/mounts` tablosunda görünmez. Pars Image Writer, `/proc/swaps` dosyasını ayrıştırarak hedef diskin bölümlerinden birinin bellek takas alanı olarak kullanılıp kullanılmadığını denetler.

### 5. Katmanlı Depolama (LVM, LUKS, RAID) Denetimi
- Hedef disk veya bölümleri `/sys/block/<name>/holders/` altında bir device-mapper katmanının (şifreli LUKS birimi veya LVM mantıksal birimi) parçasıysa diskin üzerine yazılması engellenir.

---

## 2. Düşük Seviyeli Donanım Yazma Güvenceleri

Yazma işlemi başladığında verinin gerçekten USB çipine yazıldığını garantilemek için şu çekirdek bayrakları kullanılır:

- **`O_EXCL` (Exclusive Lock)**: Diskin başka bir uygulama veya masaüstü otomatik bağlayıcısı tarafından kullanılmasını çekirdek düzeyinde kilitler.
- **`O_DSYNC` (Direct Synchronous Writes)**: Veri RAM önbelleğine yazılıp işlem "bitti" gibi gösterilmez. Her 4 MiB veri bloğu ancak USB belleğin flaş hücrelerine ulaştığında sonraki bloğa geçilir.
- **`sync` ve `fsync()`**: Yazma tamamlandığında işletim sisteminin tüm disk tamponları çekirdek tarafından diske boşaltılır.
- **Otomatik `eject`**: İşlem bitiminde USB aygıtı donanımsal olarak güvenle çıkarılır (unmount & power off standby).

---

## 3. Kullanıcılar İçin En İyi Güvenlik Tavsiyeleri

1. **Model ve Boyutu Doğrulayın**: Yazma onay ekranında diskin model adını (örneğin `SanDisk Ultra [32GB]`) ve sürücü yolunu (`/dev/sdb`) dikkatle inceleyin.
2. **Yedeklerinizi Alın**: USB diski seçmeden önce içinde kalmasını istediğiniz kişisel belgelerinizi bilgisayarınıza kopyalayın.
3. **Diski Erken Çıkarmayın**: İlerleme çubuğu %100 olsa dahi "Bitti, diski çıkarabilirsiniz" bildirimini görmeden USB belleği fiziksel olarak yerinden çekmeyin.
