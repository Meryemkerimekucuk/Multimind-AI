# 🧠 Multimind AI

**Metin üretimi, görsel oluşturma, dosya analizi ve yapay zekâ destekli araçları tek bir platformda bir araya getiren çok yönlü bir AI asistanı.**

Multimind AI, Python ve Streamlit kullanılarak geliştirilen, farklı yapay zekâ yeteneklerine tek bir arayüz üzerinden erişilmesini sağlayan interaktif bir uygulamadır. Kullanıcıların metin üretme, içerik düzenleme, görsel oluşturma, dosya analiz etme ve sesleri metne dönüştürme gibi işlemleri tek bir platform üzerinden gerçekleştirmesini amaçlar.

## ✨ Özellikler

- 💬 **AI Sohbet:** Yapay zekâ ile interaktif sohbet etme.
- ✍️ **Metin Oluşturma:** Verilen promptlara göre özgün içerikler üretme.
- 📝 **Metin Özetleme:** Uzun metinleri anlamlı ve kısa özetlere dönüştürme.
- 🔄 **Metin İyileştirme ve Yeniden Yazma:** Mevcut metinleri düzenleme, geliştirme ve farklı biçimlerde yeniden oluşturma.
- 🌍 **Çeviri:** Metinleri farklı dillere çevirme.
- 🎨 **Görsel Oluşturma:** Metin açıklamalarından yapay zekâ ile görseller üretme.
- 🖼️ **Görsel Analizi:** Yüklenen görsellerin yapay zekâ ile analiz edilmesi.
- 📂 **Dosya Analizi:** Desteklenen dosyaları yükleyerek içerikleri üzerinde analiz yapma.
- 🎙️ **Ses Transkripsiyonu:** Ses kayıtlarını metne dönüştürme.
- 💾 **Sohbet Geçmişi:** Önceki konuşmaları saklama ve yönetme.
- 👤 **Kullanıcı Yönetimi:** Kullanıcı kaydı, giriş yapma ve misafir kullanıcı desteği.

## 🛠️ Kullanılan Teknolojiler

| Teknoloji | Kullanım Amacı |
|---|---|
| Python | Uygulamanın temel programlama dili |
| Streamlit | Web arayüzü ve interaktif uygulama geliştirme |
| Google Gemini API | Metin üretimi, sohbet ve yapay zekâ işlemleri |
| Cloudflare Workers AI | Yapay zekâ destekli görsel üretimi |
| SQLite | Kullanıcı ve sohbet verilerinin saklanması |
| Pandas | Veri işleme |
| Python-dotenv | Ortam değişkenlerinin yönetimi |

## 📁 Proje Yapısı

```text
Multimind-AI/
│
├── app.py
├── database.py
├── requirements.txt
├── .env.example
├── .gitignore
│
├── services/
│   ├── gemini_service.py
│   ├── image_service.py
│   └── file_service.py
│
├── user_data/
├── uploads/
└── generated_images/
```

## 🚀 Kurulum

### 1. Repoyu klonlayın

```bash
git clone https://github.com/Meryemkerimekucuk/Multimind-AI.git
```

### 2. Proje klasörüne gidin

```bash
cd Multimind-AI
```

### 3. Sanal ortam oluşturun

```bash
python -m venv venv
```

Sanal ortamı aktifleştirin:

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### 4. Gerekli bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

### 5. Ortam değişkenlerini yapılandırın

Proje ana dizininde `.env` dosyası oluşturun ve API bilgilerinizi ekleyin:

```env
GOOGLE_API_KEY=google_api_anahtariniz

CLOUDFLARE_ACCOUNT_ID=cloudflare_hesap_id
CLOUDFLARE_API_TOKEN=cloudflare_api_token
```

Değerleri kendi API bilgilerinizle değiştirin.

### 6. Uygulamayı çalıştırın

```bash
streamlit run app.py
```

Uygulama varsayılan olarak tarayıcınızda aşağıdaki adres üzerinden açılır:

```text
http://localhost:8501
```

## 🔐 API Yapılandırması

Multimind AI, yapay zekâ servislerine erişmek için API anahtarlarına ihtiyaç duyar.

| Değişken | Açıklama |
|---|---|
| `GOOGLE_API_KEY` | Google Gemini API anahtarı |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare hesap kimliği |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API erişim anahtarı |

API anahtarlarınızı `.env` dosyasında saklayın. Hassas bilgilerinizi GitHub üzerinde paylaşmayın.

## 🎯 Projenin Amacı

Multimind AI, farklı yapay zekâ yeteneklerini tek bir platformda bir araya getirerek kullanıcıların birden fazla uygulama arasında geçiş yapmadan AI araçlarından yararlanmasını sağlamayı amaçlar.

Bu proje kapsamında yapay zekâ API'lerinin uygulamalara entegrasyonu, interaktif arayüz geliştirme, kullanıcı oturumlarının yönetimi ve AI destekli uygulamaların geliştirilmesi üzerine çalışılmıştır.

## 🔮 Geliştirme Planları

- Yeni yapay zekâ özelliklerinin eklenmesi
- Multimodal AI yeteneklerinin geliştirilmesi
- Kullanıcı deneyiminin ve arayüzün iyileştirilmesi
- Sohbet yönetiminin geliştirilmesi
- Dosya işleme yeteneklerinin genişletilmesi

## 👩🏻‍💻 Geliştirici

**Meryem Kerime Küçük**

Yönetim Bilişim Sistemleri Mezunu | Yapay Zekâ ve Veri Bilimi Meraklısı

[GitHub Profilim](https://github.com/Meryemkerimekucuk)

---

⭐ Projeyi incelemek için repository'yi ziyaret edebilirsiniz!
