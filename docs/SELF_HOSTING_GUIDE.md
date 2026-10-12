# Pars Image Writer — Kendi Sunucunda Barındırma & Yansıma Kılavuzu (SELF_HOSTING_GUIDE.md)

Bu kılavuz; kurumlar, dağıtım geliştiricileri ve sistem yöneticileri için **Pars Image Writer** altyapısını kendi sunucularında barındırma (self-hosting), özel ISO yansıma (mirror) sunucuları kurma ve çevrimiçi doğrulama mekanizmalarını özelleştirme adımlarını detaylandırmaktadır.

---

## 1. Neden Kendi Sunucunuzda Barındırma?

Pars Image Writer, varsayılan olarak dağıtım ISO dosyalarının bütünlüğünü (`MD5` / `SHA256`) doğrulamak için bir web uç noktasına bağlanır. Aşağıdaki senaryolarda altyapının yerel olarak barındırılması gerekir:

1. **Kurumsal / İzole Ağlar (Air-Gapped)**: Dış internete kapalı askeri, finansal veya kamu ağlarında işletim sistemi kalıplarının yerel sunuculardan doğrulanması.
2. **Özel Dağıtım Geliştiricileri (Custom Distros)**: Kendi GNU/Linux dağıtımınızı geliştiriyorsanız kullanıcılarınızın sizin ISO'larınızı doğrulayabilmesi.
3. **Yüksek Hızlı Yerel Yansımalar (LAN Mirrors)**: Kurum içindeki yüzlerce bilgisayara yerel ağdan hızlı imaj sağlama.

---

## 2. ISO ve Hash Doğrulama Sunucusu Kurulumu

### 2.1. Nginx ile HTTP/TLS Statik Sunucu Yapılandırması

Bir Ubuntu/Debian sunucu üzerinde Nginx kurun:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

Örnek Nginx sanal konak (virtual host) yapılandırması (`/etc/nginx/sites-available/mirror.pars.org.tr`):

```nginx
server {
    listen 80;
    server_name mirror.pars.org.tr;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mirror.pars.org.tr;

    root /var/www/mirror/PARS;
    index index.html;

    ssl_certificate /etc/letsencrypt/live/mirror.pars.org.tr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mirror.pars.org.tr/privkey.pem;

    # Güvenlik başlıkları
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;

    location / {
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # Hash dosyalarının önbelleğe alınmasını sınırla
    location ~* (MD5SUMS|SHA256SUMS)$ {
        expires 1h;
        add_header Cache-Control "public, no-transform";
    }
}
```

---

## 3. Otomatik Hash Üretimi ve GPG İmzası

Her yeni ISO yayınında sağlama dosyalarını otomatik oluşturmak için sunucuda aşağıdaki betiği kullanın:

```bash
#!/bin/bash
# /var/www/mirror/generate-sums.sh
set -e

DIR="/var/www/mirror/PARS"
cd "$DIR"

echo "Hash dosyaları güncelleniyor..."

# MD5 ve SHA256 üretimi
md5sum *.iso > MD5SUMS
sha256sum *.iso > SHA256SUMS

# GPG İmzası (İsteğe bağlı ancak güvenlik için tavsiye edilir)
gpg --batch --yes --armor --detach-sign --output MD5SUMS.gpg MD5SUMS
gpg --batch --yes --armor --detach-sign --output SHA256SUMS.gpg SHA256SUMS

chmod 644 MD5SUMS SHA256SUMS
echo "Tamamlandı!"
```

Crontab ile periyodik kontrol:
```bash
0 * * * * /var/www/mirror/generate-sums.sh >/dev/null 2>&1
```

---

## 4. Pars Image Writer Uygulamasını Özel Sunucuya Yönlendirme

`src/MainWindow.py` içerisindeki doğrulama sabitini kendi sunucunuza uyarlayabilirsiniz:

```python
# Varsayılan:
MD5SUMS_URL = "https://indir.pars.org.tr/PARS/MD5SUMS"

# Özel Sunucunuz:
MD5SUMS_URL = "https://mirror.pars.org.tr/PARS/MD5SUMS"
REQUEST_TIMEOUT_SECONDS = 15
```

### Dinamik Yapılandırma Dosyası Desteği (Öneri)
Uygulamanın yeniden derlenmeden sunucu değiştirebilmesi için `/etc/pars-image-writer/config.ini` dosyası tanımlanabilir:

```ini
[Mirror]
url = https://mirror.pars.org.tr/PARS/MD5SUMS
fallback_url = https://yedek-mirror.pars.org.tr/MD5SUMS
timeout = 10
```

---

## 5. İzole Ağ (Offline / Air-Gapped) Kurulumu

İnternet bağlantısı olmayan kapalı ağlarda:

1. Kurulum bağımlılıkları `apt-offline` veya yerel APT yansıması (`apt-mirror`) üzerinden istemcilere aktarılır.
2. Pars Image Writer içerisindeki `Çevrimiçi Doğrula` seçeneği kapatılabilir veya yerel ağdaki bir IP adresine (`http://192.168.1.50/MD5SUMS`) yönlendirilebilir.
3. Çevrimdışı doğrulama için kullanıcının dosya yöneticisinden ISO dosyasının yanına yerleştirdiği `iso_adi.iso.sha256` veya `iso_adi.iso.md5` yerel dosyası okunabilir.
