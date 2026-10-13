# Pars Image Writer — Çatallama Beyannamesi (FORK.md)

Bu belge; **Pars Image Writer** projesinin kökenini, çatallanma (fork) gerekçelerini, gerçekleştirilen mimari dönüşümleri ve açık kaynak lisans uyum beyanını detaylandırmaktadır.

---

## 📌 1. Projenin Kökeni (Upstream Origin)

**Pars Image Writer**, başlangıçta TÜBİTAK/ULAKBİM bünyesinde geliştirilen açık kaynaklı `pardus-image-writer` yazılımından türetilmiştir (fork edilmiştir). 

* **Orijinal Lisans:** GNU General Public License v3.0 (GPL-3.0)
* **Mevcut Lisans:** GNU General Public License v3.0 (GPL-3.0)
* **Geliştirici & Bakım:** Pars Linux Geliştirici Topluluğu ([dev@pars.org.tr](mailto:dev@pars.org.tr))
* **Depo Adresi:** [https://github.com/parslinux/pars-image-writer](https://github.com/parslinux/pars-image-writer)

GPL-3.0 lisansının getirdiği özgür yazılım etiği ve yasal haklar çerçevesinde; orijinal projenin ilk geliştiricilerine teşekkür eder, kaynak kodun özgürce değiştirilme ve geliştirilme hakkını sürdürürüz.

---

## 🎯 2. Neden Fork Edildi? (Motivasyon ve Amaçlar)

Orijinal yazılım temel seviyede ISO ve IMG kalıplarını tek bir USB belleğe `dd` komutuyla yazabilen bir GTK3 uygulamasıydı. Ancak modern Linux ekosisteminin (2026+) gereksinimleri doğrultusunda şu eksiklikler ortaya çıkmıştı:

1. **Eski ve Tekdüze Arayüz Mimarisi:**
   * Yalnızca eski GTK3 Glade yapısına bağlıydı.
   * Modern Libadwaita / GTK4 veya Wayland standartlarını desteklemiyordu.
   * Başsız (headless) sunucular, gömülü sistemler veya CI/CD boru hatları için bir Uçbirim (CLI) arayüzü bulunmuyordu.

2. **Sıkıştırılmış İmaj Desteğinin Bulunmaması:**
   * Modern dağıtımlar (Zstandard `.zst`, XZ `.xz`, Gzip `.gz`, Bzip2 `.bz2`) ile sıkıştırılmış kalıplar yayınlamaktadır. Orijinal kod tabanı bu kalıpları diske önceden çıkarmadan (RAM ve disk alanı tüketmeden) doğrudan USB'ye yazamıyordu.

3. **Çoklu Yazma İstasyonu (Multi-Target) Eksikliği:**
   * Aynı anda birden fazla USB belleğe (örneğin okul, laboratuvar veya sunucu kurulumlarında) eşzamanlı yazma kabiliyeti yoktu.

4. **Yetersiz Disk Güvenliği Filtreleri:**
   * Dahili sistem disklerinin (`/`, `/boot`, NVMe, LUKS şifreli kapsayıcılar, LVM ve swap alanları) kazara seçilip üzerine yazılmasını engelleyen katı ve çok katmanlı bir çekirdek filtre motoru yoktu.

5. **Telif ve Görsel Bağımsızlık İhtiyacı:**
   * Varlıklar (SVG ikonlar ve logolar) eski projeye bağımlıydı. Pars Linux'un bağımsız görsel kimliği için %100 telifsiz, özgün ve GNOME HIG uyumlu varlıklar gerekiyordu.

---

## 🚀 3. Gerçekleştirilen Başlıca Değişimler ve İnovasyonlar

| Özellik / Bileşen | Orijinal Upstream Hali | Pars Image Writer (v1.0.0+) |
| :--- | :--- | :--- |
| **Kullanıcı Arayüzü** | Yalnızca GTK3 | **GTK3 + Modern GTK4 / Libadwaita + Bağımsız CLI** |
| **Komut Satırı (CLI)** | Yok | **`pars-image-writer-cli` (JSON akışlı, progress barlı)** |
| **Desteklenen Formatlar** | `.iso`, `.img` | **`.iso`, `.img`, `.raw`, `.zst`, `.xz`, `.gz`, `.bz2`** |
| **Veri Borulama (Streaming)**| Yok (Ham dosya `dd`) | **Canlı akış açma (Streaming decompress — 0 disk/RAM israfı)** |
| **Hedef Yazma Kapasitesi** | 1 USB Aygıtı | **Sınırsız Çoklu USB Yazma İstasyonu (Broadcast)** |
| **Disk Güvenlik Motoru** | Temel kontrol | **5 Kademeli Çekirdek Güvenlik Filtresi (NVMe/LUKS/LVM koruması)** |
| **Bütünlük Doğrulama** | Manuel | **Otomatik SHA-256 ve MD5 sağlama toplamı hesaplama** |
| **Görsel Varlıklar** | Eski logolar | **%100 Telifsiz, GNOME HIG uyumlu özgün vektörler (SVG)** |
| **Evrensel Paketleme** | Yalnızca `.deb` | **Flatpak Manifest + AppStream Metainfo + Debian Packaging** |

---

## 📈 4. Kod Ayrışması ve İstatistikler

* **Kod Tabanı Büyümesi:** Python çekirdeği **2.095 satırdan 4.119 satıra (+%96,6)** çıkarıldı.
* **Yeni Kod Oranı:** Mevcut kod tabanının **%55,0'ı sıfırdan yazılan yeni modüllerdir** (`CLI.py`, `ModernWindow.py`, streaming motoru vb.).
* **Eski Kodların Durumu:** Kalan eski modüllerin **%100'ü** Python 3.8+ modern sözdizimine (f-strings, type annotations, `pathlib.Path`, udev optimizasyonları) dönüştürüldü.
* **Görseller:** 4 SVG görselinin **%100'ü** sıfırdan vektör kodlarıyla çizildi.
* **Ad ve Marka Ayrışması:** Kod tabanı, paket yapılandırmaları, D-Bus servisleri ve masaüstü dosyalarındaki tüm eski dağıtım kalıntıları tamamen temizlenerek Pars Linux ekosistemine uyarlandı.

---

## 📜 5. Lisans ve Açık Kaynak Taahhüdü

Bu proje, GNU Genel Kamu Lisansı Sürüm 3 (GPL-3.0-or-later) şartları altında lisanslanmıştır. Kaynak kodları tamamen açıktır, kopyalanabilir, değiştirilebilir ve yeniden dağıtılabilir.

Herhangi bir soru, öneri veya hata bildirimi için:
* **Hata Takibi & Sorunlar:** [https://github.com/parslinux/pars-image-writer/issues](https://github.com/parslinux/pars-image-writer/issues)
* **İletişim:** [dev@pars.org.tr](mailto:dev@pars.org.tr)
