# Pars Image Writer — Bağış, Sponsorluk ve Finansal Sürdürülebilirlik (PAYMENT_INTEGRATION.md)

Bu doküman, açık kaynaklı **Pars Image Writer** projesinin uzun vadeli sürdürülebilirliğini sağlamak amacıyla topluluk bağışları, kurumsal sponsorluklar ve isteğe bağlı uygulama içi destek modellerini tanımlar.

---

## 1. Açık Kaynak Felsefesi ve Finansal Model

Pars Image Writer; **GNU GPLv3** lisanslı, %100 özgür ve açık kaynaklı bir yazılımdır.
- **Kesin İlke**: Temel yazılım işlevleri hiçbir zaman bir ödeme duvarı (paywall) arkasına alınamaz; reklam veya casus yazılım (adware/spyware) barındıramaz.
- **Finansmanın Amacı**:
  1. Yüksek hızlı küresel ISO yansıma ve depolama sunucularının maliyetlerini karşılamak.
  2. Farklı donanım mimarileri (x86_64, ARM64, RISC-V) ve USB 2.0/3.0/3.2/Type-C bellek test laboratuvarı kurmak.
  3. Güvenlik denetimleri ve kod imzalama (code-signing) sertifikası giderlerini finanse etmek.

---

## 2. Destek ve Bağış Kanalları

Projeyi desteklemek isteyen bireysel ve kurumsal kullanıcılar için entegre edilmiş resmi kanallar:

| Platform | Açıklama | Hedef Kitle |
|---|---|---|
| **GitHub Sponsors** | Komisyonsuz, aylık veya tek seferlik destek | Geliştiriciler ve Bireysel Kullanıcılar |
| **Open Collective** | Şeffaf faturalandırma ve bütçe yönetimi | Kurumlar ve Topluluklar |
| **LiberaPay** | Yinelenen mikro bağış platformu | Bireysel Özgür Yazılım Destekçileri |
| **Kripto Varlıklar** | Bitcoin (BTC), Ethereum (ETH), Monero (XMR) | Bağımsız ve Uluslararası Bağışçılar |

### Cüzdan ve Hesap Bilgileri (Örnek Yapılandırma)
- **GitHub Sponsors**: `https://github.com/sponsors/pars-project`
- **Open Collective**: `https://opencollective.com/pars-image-writer`
- **BTC**: `bc1qpars...imagewriter`
- **ETH**: `0xPars...ImageWriter`

---

## 3. Uygulama İçi Destek Butonu Tasarımı

Uygulama arayüzünde kullanıcıyı rahatsız etmeyecek şekilde bir "Projeyi Destekle" bağlantısı `About` (Hakkında) penceresinde veya menü çubuğunda konumlandırılabilir:

```python
# src/MainWindow.py içerisine entegre edilebilir fonksiyon:
def on_btn_donate_clicked(self, widget):
    import webbrowser
    webbrowser.open_new_tab("https://opencollective.com/pars-image-writer")
```

GTK Builder `ui/MainWindow.glade` içerisine eklenebilecek bağlantı düğmesi:
- Simge: `starred-symbolic` veya `emblem-favorite-symbolic`
- Etiket: `Projeyi Destekle / Support Project`

---

## 4. Kurumsal Destek ve Özel Geliştirme (Enterprise Support)

Büyük ölçekli kurumlar, üniversiteler veya donanım üreticileri için aşağıdaki ticari destek hizmetleri sunulabilir:

1. **Özel Markalama (Whitelabel)**: Kurum logosu, kurumsal renkler ve sadece kurum içi ISO'ları listeleyen özelleştirilmiş sürümler.
2. **Hizmet Seviyesi Anlaşması (SLA)**: Kritik hata düzeltmeleri ve yeni çekirdek sürümlerine anında uyumluluk garantisi.
3. **Özel Donanım Entegrasyonu**: Kiosk sistemleri, endüstriyel flaş yazıcılar ve çoklu eşzamanlı USB yazma istasyonları için özel sürücüler.

Detaylı kurumsal bilgi için: `destek@pars.org.tr`
