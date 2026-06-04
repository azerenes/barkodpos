<picture>
  <source
    srcset="https://raw.githubusercontent.com/your-username/BarkodPOS/main/docs/banner-dark.png" media="(prefers-color-scheme: dark)" />
  <img alt="BarkodPOS Banner" src="https://raw.githubusercontent.com/your-username/BarkodPOS/main/docs/banner-light.png" />
</picture>

# 🏪 BarkodPOS — Profesyonel Perakende Satış ve Stok Yönetim Sistemi

> **Tamamen Türkçe, tamamen offline, tek tıkla çalışır.**  
> Perakende mağazanız için POS (satış noktası), stok takibi, raporlama, cari yönetim ve daha fazlası tek bir uygulamada.

![Platform](https://img.shields.io/badge/Windows-10%2B-0078D6?logo=windows)  
![Durum](https://img.shields.io/badge/durum-kararlı-brightgreen)  
![Sürüm](https://img.shields.io/badge/sürüm-v1.0.0-blue)

---

## ✨ Öne Çıkan Özellikler

| Modül | Ne İşe Yarar |
|-------|-------------|
| **🛒 POS Satış** | Barkod okut, ürün seç, hızlı satış yap. Nakit, Kart, Veresiye — 3 ödeme tipi. |
| **📦 Stok Yönetimi** | Ürün ekle, düzenle, stok gir/çık yap, CSV'den toplu yükle. Düzine/Set birim desteği. |
| **🏷️ Barkod Etiketi** | Tek veya toplu barkod etiketi bas. |
| **👥 Müşteri Takibi** | Müşteri kartı, borç/alacak, veresiye satış yönetimi. |
| **📊 Raporlama** | Günlük/haftalık/aylık satış raporları, Kâr-Zarar analizi, grafiklerle görselleştirme. |
| **🧾 Fiş / Fatura** | Termal tarzda yazdırılabilir fiş. QR kodlu. E-posta ile gönderme. |
| **💵 Kasa Yönetimi** | Günlük kasa özeti: nakit, kart, veresiye, gider dağılımı. |
| **🔄 Transfer** | Şubeler arası stok transferi. |
| **🏭 Tedarikçi Yönetimi** | Tedarikçi ekle/düzenle, tedarikçiye bağlı ürünleri gör. |
| **📉 Gider Takibi** | Kategorize edilmiş gider kaydı ve raporlaması. |
| **🏢 Çoklu Şube** | Şube bazlı kullanıcı ve stok yönetimi. |
| **👤 Personel Yönetimi** | Personel ekle/düzenle, rol bazlı erişim (Yönetici/Personel). |
| **⚙️ Ayarlar** | Firma bilgileri, KDV oranı, para birimi, düşük stok uyarısı, SMTP e-posta, yedekleme. |
| **🔄 Otomatik Güncelleme** | GitHub Releases üzerinden tek tıkla güncelleme. |
| **💾 Otomatik Yedekleme** | Her gün veritabanı yedeklenir. |

---

## 🚀 Hızlı Başlangıç

```bash
cd C:\BarkodPOS
.\BarkodPOS.exe
```

1. Uygulamayı çalıştırın → Tarayıcı otomatik açılır
2. Açılışta personel seçin
3. Satışa başlayın!

> **İnternet bağlantısı gerektirmez.** Tüm veriler bilgisayarınızda saklanır.  
> **Kurulum gerektirmez.** Tek .exe dosyası, çalıştır ve kullan.

---

## 🖥️ Sistem Gereksinimleri

| Bileşen | Gereksinim |
|---------|-----------|
| **İşletim Sistemi** | Windows 10 / 11 (64-bit) |
| **İşlemci** | 1.5 GHz veya üzeri |
| **RAM** | 2 GB (önerilen: 4 GB) |
| **Depolama** | 500 MB boş alan |
| **Ekran** | 1280×720 veya üzeri |

---

## 🗺️ Yol Haritası — Gelecek Özellikler

Aşağıdaki özellikler sırayla eklenecektir:

### 🔜 1. Aşama — Temel İyileştirmeler
- [ ] **ESC/POS Termal Yazıcı Desteği** — Doğrudan termal yazıcıya fiş basımı
- [ ] **Hızlı Satış (İsimsiz Ürün)** — Barkodsuz ürünleri anlık fiyat girerek satma
- [ ] **Kısayol Tuşları** — F1-F12 ile hızlı işlemler

### 🔜 2. Aşama — Stok & Muhasebe
- [ ] **Stok Sayım Modülü** — Sayım başlat, farkı raporla, envanter güncelle
- [ ] **Alış Faturası Kaydı** — Tedarikçiden alınan fatura bilgilerini kaydetme
- [ ] **Fiyat Değişiklik Geçmişi** — Ürün fiyatlarındaki tüm değişikliklerin log'u

### 🔜 3. Aşama — Kasa & Cari
- [ ] **Kasa Açılış/Kapanış** — Günlük kasa sayımı, açılış bakiyesi
- [ ] **Müşteri Hesap Ekstresi** — Müşteri bazında tüm hareket dökümü
- [ ] **Çoklu Fiyat (Toptan/Perakende)** — Aynı ürün için farklı fiyat kademeleri

### 🔜 4. Aşama — Gelişmiş Özellikler
- [ ] **Reçete / Set Ürünler** — İçindekilerden oluşan paket ürün tanımlama
- [ ] **Karanlık Mod (Dark Mode)** — Göz yormayan arayüz teması
- [ ] **Yedekten Geri Yükleme** — Geçmiş yedeklerden veritabanı kurtarma
- [ ] **Çoklu Döviz Desteği** — $ / € / ₺ ile satış ve raporlama

---

## 📸 Ekran Görüntüleri

> *(Ekran görüntüleri eklenecek — docs/screenshots/ klasörüne konulacak)*

| POS Satış | Stok Yönetimi | Raporlar |
|-----------|--------------|----------|
| *(resim)* | *(resim)* | *(resim)* |

---

## ❓ Sık Sorulan Sorular

**S: Veritabanım nerede saklanıyor?**  
C: `BarkodPOS.exe`'nin yanında `instance/barkodpos.db` olarak saklanır. Taşımak isterseniz tüm `instance/` klasörünü kopyalamanız yeterlidir.

**S: İnternet olmadan çalışır mı?**  
C: Evet. Tüm JS/CSS kütüphaneleri uygulama içine gömülüdür. Sıfır internet bağımlılığı.

**S: Yedek nasıl alırım?**  
C: Ayarlar → Yedekleme bölümünden manuel yedek alabilirsiniz. Ayrıca her gün otomatik yedek alınır.

**S: Güncelleme nasıl çalışır?**  
C: Ayarlar → Güncelleme bölümünden "Kontrol Et"e tıklayın. Yeni sürüm varsa tek tıkla güncelleyin. Uygulama kendini yeniler.

**S: Şubeler arası veri paylaşımı?**  
C: Şu an için her şube kendi bilgisayarında çalışır. Merkezi sunucu versiyonu yol haritasında.

---

## 📝 Sürüm Geçmişi

| Sürüm | Tarih | Değişiklikler |
|-------|-------|--------------|
| v1.0.0 | 2025 | İlk kararlı sürüm. POS, stok, müşteri, rapor, kasa, gider, tedarikçi, transfer, personel yönetimi. Otomatik güncelleme. |

---

## 📄 Lisans

Özel kullanım içindir. Tüm hakları saklıdır.

---

## 💬 Destek & İletişim

Sorun, öneri veya özellik talebi için:

- 📧 E-posta: *(destek e-posta adresi)*
- 🐛 GitHub Issues: [github.com/your-username/BarkodPOS/issues](https://github.com/your-username/BarkodPOS/issues)

---

<p align="center">
  <strong>BarkodPOS</strong> — <em>İşinizi kolaylaştırmak için tasarlandı.</em><br>
  <sub>Made with ❤️ in Turkey 🇹🇷</sub>
</p>

---

## 🔧 Geliştirici Bilgisi

Bu repo aşağıdaki yapıyı kullanır:

```
barkodpos/
├── app/                    # Flask uygulaması
│   ├── routes/             # Blueprint route'lar
│   ├── templates/          # Jinja2 şablonları
│   ├── static/             # Statik dosyalar (CSS/JS/local libs)
│   ├── __init__.py         # Flask app factory
│   ├── models.py           # SQLAlchemy modelleri
│   ├── auth_helper.py      # Session tabanlı auth
│   └── update_helper.py    # Güncelleme sistemi
├── dist/BarkodPOS/         # Derlenmiş exe ve çalışma dosyaları
├── desktop_app.py          # PyQt5 masaüstü giriş noktası
├── build.bat               # PyInstaller derleme betiği
├── run.py                  # Flask development sunucusu
├── config.py               # Yapılandırma
├── updater.bat             # Güncelleme betiği (runtime oluşur)
└── requirements.txt        # Python bağımlılıkları
```

**Teknolojiler:** Python Flask • SQLite • PyQt5 + QWebEngineView • Bootstrap 5 • Chart.js • QRCode.js  
**Derleme:** PyInstaller + UPX (~165 MB sıkıştırılmış tek exe)
