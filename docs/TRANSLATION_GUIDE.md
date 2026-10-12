# Pars Image Writer — Çeviri ve Yerelleştirme Kılavuzu (TRANSLATION_GUIDE.md)

Bu doküman, **Pars Image Writer** uygulamasının çok dilli yapısını, gettext altyapısını ve yeni bir dil çevirisinin nasıl ekleneceğini detaylandırmaktadır.

---

## 1. Gettext Mimarisi ve Dizin Yapısı

Pars Image Writer, standart **GNU gettext** altyapısını kullanır:

- **Şablon Dosyası**: `po/pars-image-writer.pot` — Kod ve arayüzdeki tüm translatable dizgilerin ana şablonudur.
- **Dil Dosyaları**:
  - `po/tr.po`: Türkçe çeviriler.
  - `po/es.po`: İspanyolca çeviriler.
  - `po/pt.po`: Portekizce çeviriler.
- **Derlenmiş İkilikler**: Kurulum esnasında `setup.py` tarafından üretilip `/usr/share/locale/<dil>/LC_MESSAGES/*.mo` konumuna kurulan ikili dosyalardır.

---

## 2. Python ve Glade Kodunda Çeviri Kuralları

### Python Kodlarında:
Tüm kullanıcıya dönük metinler `_()` fonksiyonu ile işaretlenmelidir:

```python
from locale import gettext as _

# Doğru Kullanım:
self.show_message(_("Writing process is finished."))

# Dinamik değişkenlerde formatlama:
self.lbl_details.set_label(_("{} MB/s speed").format(speed))
```

### Glade (`ui/MainWindow.glade`) Arayüzünde:
Arayüz bileşenlerinde etiketlerin çevrilebilmesi için `translatable="yes"` özelliği bulunmalıdır:

```xml
<object class="GtkLabel" id="lbl_title">
  <property name="visible">True</property>
  <property name="label" translatable="yes">Pars Image Writer</property>
</object>
```

---

## 3. Dizgileri Güncelleme (`update-translations.sh`)

Kaynak koda veya Glade arayüzüne yeni bir metin eklendiğinde şablon ve mevcut çeviri dosyalarını güncellemek için kök dizindeki betiği çalıştırın:

```bash
./update-translations.sh
```

Bu betik:
1. `src/*.py` ve `ui/MainWindow.glade` dosyalarını tarayarak yeni dizgileri `.pot` dosyasına çıkarır (`xgettext`).
2. Mevcut `.po` dosyalarını güncel şablonla harmanlar (`msgmerge`).

---

## 4. Yeni Bir Dil Ekleme Adımları

Örnek: **Azerbaycan Türkçesi (`az`)** veya **Almanca (`de`)** eklemek için:

1. `po/` dizini altında yeni bir `.po` dosyası oluşturun:
   ```bash
   msginit --input=po/pars-image-writer.pot --locale=az --output=po/az.po
   ```

2. `po/az.po` dosyasını Poedit veya herhangi bir metin düzenleyici ile açarak çevirileri tamamlayın:
   ```po
   msgid "Select ISO or IMG File"
   msgstr "ISO və ya IMG Faylını Seçin"

   msgid "Writing process is finished."
   msgstr "Yazma prosesi başa çatdı."
   ```

3. Çeviriyi yerel olarak derleyip test edin:
   ```bash
   mkdir -p po/az/LC_MESSAGES
   msgfmt po/az.po -o po/az/LC_MESSAGES/pars-image-writer.mo
   ```

4. Uygulamayı ilgili dil ortamında başlatarak doğrulayın:
   ```bash
   LANGUAGE=az python3 src/Main.py
   ```

---

## 5. Çeviri Katkısı Gönderme

Yeni veya güncellenmiş `.po` dosyanızı GitHub üzerinden Pull Request (PR) olarak gönderebilirsiniz. Katkınız için teşekkür ederiz!
