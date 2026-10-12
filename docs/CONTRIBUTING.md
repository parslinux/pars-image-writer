# Pars Image Writer — Katkıda Bulunma Rehberi (CONTRIBUTING.md)

Pars Image Writer projesine katkıda bulunmak istediğiniz için teşekkür ederiz! Açık kaynak topluluğunun gücüne inanıyor ve her türlü hata bildirimini, özellik önerisini, çeviriyi ve kod katkısını memnuniyetle karşılıyoruz.

---

## 1. Katkı Türleri

- 🐛 **Hata Bildirimi (Bug Reports)**: Karşılaştığınız beklenmeyen durumları veya çökmeleri GitHub Issues üzerinden ayrıntılı bildirin.
- 💡 **Özellik Önerileri (Feature Requests)**: Uygulamayı daha işlevsel hale getirecek yeni fikirlerinizi paylaşın.
- 🌐 **Çeviri Katkıları**: Uygulamayı yeni dillere çevirin veya mevcut çevirileri iyileştirin (bkz: [TRANSLATION_GUIDE.md](TRANSLATION_GUIDE.md)).
- 📝 **Dokümantasyon**: Rehberleri güncelleyin, eksik veya anlaşılmayan kısımları netleştirin.
- 💻 **Kod Katkısı**: Hataları düzeltin veya planlanan yeni özellikleri kodlayın.

---

## 2. Geliştirme İş Akışı (Git Workflow)

1. Projeyi GitHub üzerinde **Fork** edin.
2. Yerel geliştirme ortamınıza klonlayın:
   ```bash
   git clone https://github.com/<kullanici-adiniz>/pars-image-writer.git
   cd pars-image-writer
   ```
3. Yeni bir özellik veya hata için dal (branch) açın:
   ```bash
   git checkout -b feat/coklu-hash-destegi
   # veya
   git checkout -b fix/usb-algilama-hatasi
   ```
4. Kod değişikliklerinizi yapın ve yerel olarak test edin (bkz: [TESTING.md](TESTING.md)).
5. Değişiklikleri standart kurallara uygun commit edin:
   ```bash
   git commit -m "feat: SHA-256 doğrulama desteği eklendi"
   ```
6. Dalınızı GitHub'a gönderin (push):
   ```bash
   git push origin feat/coklu-hash-destegi
   ```
7. Depo üzerinde ana dala doğru bir **Pull Request (PR)** oluşturun.

---

## 3. Commit Mesajı Standartları (Conventional Commits)

Commit mesajlarında standart ön ekler kullanılmalıdır:

- `feat:` Yeni bir özellik eklendiğinde.
- `fix:` Bir hata giderildiğinde.
- `docs:` Yalnızca dokümantasyon değişikliği yapıldığında.
- `style:` Kod işleyişini etkilemeyen biçimlendirme düzeltmelerinde (boşluk, noktalama).
- `refactor:` Ne hata düzelten ne özellik ekleyen kod düzenlemelerinde.
- `test:` Test senaryoları eklendiğinde veya güncellendiğinde.

---

## 4. Kodlama Standartları

- Kodlar **PEP 8** standartlarına uygun olmalıdır.
- PR göndermeden önce biçimlendirme ve lint araçlarını çalıştırın:
  ```bash
  black --line-length 100 src/
  flake8 src/ --max-line-length=100
  ```
- Gereksiz dış kütüphane bağımlılığı eklemekten kaçının; standart kütüphane ve GObject API'lerini tercih edin.
- Güvenlik ve ayrıcalık modelini (UID düşürme, disk koruması) kesinlikle zayıflatmayın.
