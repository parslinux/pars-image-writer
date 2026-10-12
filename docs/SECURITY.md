# Pars Image Writer — Güvenlik Politikası ve Mimarisi (SECURITY.md)

Bu doküman, **Pars Image Writer** uygulamasının güvenlik modelini, tehdit analizini ve güvenlik açığı bildirim politikasını içerir.

---

## 1. Güvenlik Modeli ve Tehdit Analizi

Pars Image Writer, disklere düşük seviyeli yazım yapabilmek için root yetkilerine ihtiyaç duyar. Bu nedenle mimarinin her katmanı olası ayrıcalık yükseltme (privilege escalation) ve kötü niyetli istismarları önleyecek biçimde tasarlanmıştır.

### 1.1. Yetki Düşürme Güvencesi (`Utils.open_as_caller`)
- **Tehdit**: Kötü niyetli bir kullanıcı veya arayüz manipülasyonu, normalde okuma yetkisi olmayan bir sistem dosyasını (örneğin `/etc/shadow` veya başka bir kullanıcının özel SSH anahtarlarını) girdi olarak seçip USB diske yazdırabilir.
- **Önlem**: Root olarak çalışan yazma motorları, girdi dosyasını açmadan önce `PKEXEC_UID` ortam değişkeni üzerinden yetkilerini geçici olarak çağıran kullanıcının gerçek UID/GID'sine düşürür (`open_as_caller`). Eğer çağıran kullanıcı o dosyayı doğrudan okuyamıyorsa, root süreci de dosyayı açmayı reddeder.

### 1.2. Kabuk Enjeksiyonunu (Shell Injection) Önleme
- **Tehdit**: Boşluk veya tırnak işaretleri içeren dosya yolları (`"; rm -rf / ;"`) üzerinden rastgele kod çalıştırma.
- **Önlem**: Kod tabanında kesinlikle `shell=True` ile komut çalıştırılmaz. Tüm harici araçlar (`parted`, `mkfs`, `mount`, `udevadm`, `grub-install`) argüman listesi (`["parted", drive, "mkpart", ...]`) olarak doğrudan çekirdeğe iletilir.

### 1.3. İzolasyonlu ISO Bağlama (`MOUNT_OPTIONS`)
- **Tehdit**: Kullanıcının seçtiği zararlı bir ISO dosyası içinde setuid-root ikilikler veya aygıt düğümleri (device nodes) bulunabilir.
- **Önlem**: ISO kalıpları kopyalama amacıyla sisteme bağlanırken mutlaka şu bayraklarla bağlanır:
  ```python
  MOUNT_OPTIONS = "nosuid,nodev,noexec"
  ```
  Bu sayede ISO içindeki hiçbir dosya çalıştırılamaz (`noexec`) ve yetki yükseltemez (`nosuid`).

### 1.4. İzole Geçici Bağlama Alanı (`0700` İzni)
- Geçici bağlama dizini (`/run/pars-image-writer`), `0700` dosya izinleriyle yalnızca root kullanıcısına özel oluşturulur. Sistemdeki diğer yerel kullanıcılar kopyalama sırasında bu dizine erişemez.

### 1.5. Güvenli İptal ve Sinyal Hijack Koruması
- Eskiden kullanılan `kill` polkit kuralı kaldırılmıştır. Kullanıcı iptal ettiğinde GUI `stdin` borusunu kapatır; root süreci bunu kendi içinde algılayarak diski tutarlı bir durumda bırakıp temiz bir şekilde çıkar.

---

## 2. Desteklenen Sürümler

Aşağıdaki sürümler aktif olarak güvenlik güncellemeleri almaktadır:

| Sürüm Serisi | Destek Durumu |
|---|---|
| `1.0.x` | ✅ Aktif Güvenlik Desteği |
| `0.9.x` | ✅ Kritik Güvenlik Düzeltmeleri |
| `< 0.9.0` | ❌ Destek Sona Erdi (Eski sürümler güncellenmelidir) |

---

## 3. Güvenlik Açığı Bildirimi (Vulnerability Disclosure)

Eğer Pars Image Writer kodunda veya bağımlılıklarında bir güvenlik zafiyeti tespit ederseniz:

1. **Lütfen GitHub Issues üzerinde herkese açık konu açmayınız.**
2. Detaylı teknik açıklamayı, kavram kanıtı (PoC) kodunu veya adımları **`guvenlik@pars.org.tr`** adresine e-posta ile iletiniz.
3. Bildiriminiz en geç **48 saat** içinde incelenerek yanıtlanacak ve gerekli güvenlik yaması 7 gün içinde yayınlanacaktır.
