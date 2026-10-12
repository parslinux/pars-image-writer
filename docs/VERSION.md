# Pars Image Writer — Sürüm Politikası ve Yayın Döngüsü (VERSION.md)

Bu doküman, **Pars Image Writer** projesinin sürüm numaralandırma şemasını, sürüm yaşam döngüsünü ve yeni sürüm yayınlama adımlarını açıklar.

---

## 1. Sürüm Numaralandırma Şeması (SemVer 2.0.0)

Proje, [Semantic Versioning 2.0.0](https://semver.org/) kurallarını uygular:

$$\text{Sürüm Biçimi: } \mathbf{MAJOR.MINOR.PATCH}$$

- **MAJOR (Ana Sürüm)**: Geriye dönük uyumsuz büyük mimari değişiklikler (örneğin GTK3'ten GTK4'e geçiş veya IPC protokolünün tamamen değişmesi).
- **MINOR (Alt Sürüm)**: Geriye dönük uyumlu yeni özellikler (örneğin yeni bir yazma modu eklenmesi, SHA-256 desteği, yeni dil çevirileri).
- **PATCH (Yama Sürümü)**: Geriye dönük uyumlu hata düzeltmeleri ve güvenlik yamaları.

### Ön Sürüm Etiketleri:
- `1.0.0-alpha.1`: Dahili test ve mimari doğrulama sürümü.
- `1.0.0-beta.1`: Topluluk testlerine açık aday sürüm.
- `1.0.0-rc.1`: Yayın adayı (Release Candidate).

---

## 2. Kod Tabanında Sürüm Senkronizasyonu

Pars Image Writer'da sürümün tekil doğruluk kaynağı (Single Source of Truth) **`debian/changelog`** dosyasıdır:

1. **`debian/changelog`**: İlk satırındaki sürüm numarası esas alınır:
   ```debian
   pars-image-writer (1.0.0) unstable; urgency=medium
   ```
2. **`setup.py`**: Kurulum sırasında `debian/changelog` dosyasından sürümü otomatik okur ve `src/__version__` dosyasına yazar.
3. **`src/MainWindow.py`**: Hakkında (About) penceresini açarken `src/__version__` dosyasını okuyarak kullanıcıya sunar.

---

## 3. Yeni Sürüm Yayınlama Kontrol Listesi (Release Checklist)

Yeni bir sürüm yayınlamadan önce aşağıdaki adımlar sırasıyla tamamlanmalıdır:

- [ ] **1. Testler ve Kod Doğrulaması**:
  - `black` ve `flake8` kontrollerinden başarıyla geçildiğinden emin olun.
  - [TESTING.md](TESTING.md) kılavuzundaki sanal disk testlerini çalıştırın.
- [ ] **2. Çevirilerin Güncellenmesi**:
  - `./update-translations.sh` betiğini çalıştırın ve yeni metinlerin `.po` dosyalarına aktarıldığını doğrulayın.
- [ ] **3. Belgelerin Güncellenmesi**:
  - [CHANGELOG.md](CHANGELOG.md) dosyasına yeni sürüm başlığını ve değişiklik maddelerini ekleyin.
  - `debian/changelog` dosyasına yeni sürüm kaydını girin.
- [ ] **4. Git Etiketleme (Tagging)**:
  ```bash
  git add .
  git commit -m "chore(release): version 1.0.0"
  git tag -a v1.0.0 -m "Release version 1.0.0"
  git push origin master --tags
  ```
- [ ] **5. Debian Paketi Derleme**:
  ```bash
  gbp buildpackage -us -uc
  ```
- [ ] **6. GitHub Release**:
  - GitHub üzerinde yeni sürüm oluşturun, derlenen `.deb` paketlerini ve `SHA256SUMS` sağlama dosyasını release varlıklarına ekleyin.
