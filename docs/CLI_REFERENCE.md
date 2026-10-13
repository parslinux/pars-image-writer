# Pars Image Writer — Komut Satırı Başvuru Rehberi (CLI_REFERENCE.md)

Bu doküman, **Pars Image Writer** uygulamasının terminal ortamında parametreli kullanımını, mevcut komut satırı yeteneklerini ve headless (arayüzsüz) otomasyon kılavuzunu içerir.

---

## 1. Temel Komut Satırı Kullanımı

Uygulama komut satırından çağrıldığında parametre olarak doğrudan yazdırılacak kalıp dosyasını alabilir:

```bash
pars-image-writer [SEÇENEKLER] [KALIP_DOSYASI]
```

### Örnekler:
```bash
# Doğrudan ISO seçilerek arayüzün açılması
pars-image-writer ~/Downloads/pars-23.0-x86_64.iso

# IMG kalıbı ile başlatma
pars-image-writer /opt/images/raspberrypi.img
```

---

## 2. Gelişmiş Headless CLI Mimarisi (`pars-image-writer-cli`)

Sunucu ortamlarında veya otomatik kurulum betiklerinde arayüzsüz (headless) çalıştırma için geliştirilen CLI sözdizimi:

```bash
pars-image-writer-cli --file <yol> --device <aygıtlar...> [seçenekler]
```

### Desteklenen Parametreler

| Parametre | Kısa Yol | Açıklama |
|---|---|---|
| `--file <YOL>` | `-f` | Yazdırılacak `.iso`, `.img`, `.raw`, `.xz`, `.gz`, `.zst` dosyasının mutlak yolu. |
| `--device <AYGIT...>` | `-d`, `--devices` | Hedef USB blok aygıtı veya eşzamanlı çoklu aygıtlar (örn. `/dev/sdb` veya `/dev/sdb /dev/sdc`). |
| `--mode <MOD>` | `-m` | Yazma modu: `dd` (varsayılan), `iso`, `windows`. |
| `--verify` | `-c` | Yazma öncesi hash bütünlüğünü denetle (SHA-256, SHA-512 veya MD5). |
| `--checksum <ÖZET>` | | Doğrulanacak beklenen sağlama özeti (MD5, SHA-256 veya SHA-512). |
| `--algo <ALGO>` | | Sağlama algoritması: `sha256` (varsayılan), `sha512`, `md5`. |
| `--persistence` | `-p` | GNU/Linux ISO modunda Live USB kalıcı depolama (persistence) bölümü oluştur. |
| `--yes` | `-y` | Onay sorgusunu atla (otomasyon ve headless betikler için). |
| `--json` | `-j` | İlerleme durumunu JSON akışı olarak stdout'a bas. |
| `--list` | `-l` | Sistemdeki bağlı USB aygıtlarını listele ve çık. |
| `--version` | `-v` | Sürüm bilgisini göster ve çık. |
| `--help` | `-h` | Yardım metnini göster ve çık. |

### Örnek Kullanımlar:
```bash
# 1. Standart tek diske yazdırma
pars-image-writer-cli -f pars-linux.iso -d /dev/sdb

# 2. Çoklu eşzamanlı USB yazma istasyonu modu (Broadcast multi-write)
pars-image-writer-cli -f pars-linux.iso -d /dev/sdb /dev/sdc /dev/sdd -y

# 3. Zstandard veya XZ sıkıştırılmış kalıbı doğrudan açarak diske yazma (Streaming decompress)
pars-image-writer-cli -f fedora-silverblue.raw.xz -d /dev/sdb

# 4. SHA-256 doğrulamalı ve JSON olay akışlı otomasyon çalıştırması
pars-image-writer-cli -f ubuntu.iso -d /dev/sdb -c --algo sha256 -y -j
```

---

## 3. JSON İlerleme Akışı Formatı (`--json`)

Otomasyon sistemleri ve web tabanlı yönetim panelleri için stdout üzerinden tek satırlık JSON akışı:

```json
{"event": "start", "file": "pars.iso.xz", "devices": ["sdb", "sdc"], "total_bytes": 4294967296, "mode": "dd", "compression": "xz", "multi_write": true}
{"event": "progress", "written_bytes": 1073741824, "total_bytes": 4294967296, "percent": 25.0, "speed_mb": 45.2, "eta_seconds": 71, "devices": ["sdb", "sdc"]}
{"event": "progress", "written_bytes": 2147483648, "total_bytes": 4294967296, "percent": 50.0, "speed_mb": 46.1, "eta_seconds": 46, "devices": ["sdb", "sdc"]}
{"event": "completed", "status": "success", "elapsed_seconds": 93}
```

---

## 4. Çıkış Kodları (Exit Codes)

| Kod | Anlamı | Açıklama |
|---|---|---|
| `0` | **BAŞARILI** | Kalıp USB diske hatasız yazıldı ve disk güvenle çıkarıldı. |
| `1` | **GİRİŞ/ÇIKIŞ HATASI** | Disk yazma sırasında donanımsal I/O veya dosya sistemi hatası oluştu. |
| `2` | **GEÇERSİZ ARGÜMAN** | Eksik dosya yolu, bulunamayan imaj veya hatalı komut satırı parametresi. |
| `3` | **GÜVENLİK ENGELİ** | Hedef aygıt bir USB disk değil veya sistem mount noktasını içeriyor. |
| `126` | **POLKIT REDDİ** | Kullanıcı PolicyKit kimlik doğrulama diyalogunu kapattı veya reddetti. |
| `130` | **İPTAL EDİLDİ** | İşlem kullanıcı tarafından (`SIGINT` / `Ctrl+C`) güvenle durduruldu. |

---

## 5. Betik Entegrasyon Örneği (Bash)

```bash
#!/bin/bash
set -euo pipefail

IMAGE="/tmp/firmware.iso"
TARGET="/dev/sdc"

echo "Yazma işlemi başlatılıyor: $IMAGE -> $TARGET"

if sudo python3 src/ImageWriter.py "$IMAGE" "$TARGET"; then
    echo "Disk başarıyla hazırlandı!"
    exit 0
else
    echo "Yazma başarısız oldu!" >&2
    exit 1
fi
```
