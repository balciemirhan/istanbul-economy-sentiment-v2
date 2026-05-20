# 📊 İstanbul Ekonomi Analizi (X/Twitter Sentiment Tracker)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/Transformers-HuggingFace-orange?style=for-the-badge" alt="Transformers">
  <img src="https://img.shields.io/badge/Flask-Flask--CORS-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-Database-blue?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
</p>

 Bu proje; İstanbul'un ekonomik nabzını X (Twitter) üzerinden tutan, halkın ulaşım, perakende, gayrimenkul ve makroekonomi konularındaki duygu durumunu analiz eden tam otomatik bir NLP boru hattıdır (Pipeline). Özel olarak 5.000 adet tweet ile eğitilmiş **(Fine-Tuned) 128k BERTurk** yapay zeka modelini merkezine alır ve sonuçları dinamik bir web arayüzünde (Dashboard) sunar.

---

## 🚀 Önemli Geliştirme Notu (v2 Upgrade)

Bu proje, daha önceki **[balciemirhan/istanbul-economy-sentiment](https://github.com/balciemirhan/istanbul-economy-sentiment)** çalışmasının **ikinci ve çok daha gelişmiş versiyonudur**.

*   **Eski Sürüm (v1):** Genel amaçlı hazır **Savaş BERT** (`savasy/bert-base-turkish-sentiment-cased`) modelini kullanmaktaydı ve doğruluk oranı daha kısıtlıydı.
*   **Bu Sürüm (v2 - Yeni):** Savaş BERT modelini tamamen devre dışı bırakarak; bu projenin özel 5.000+ satırlık tweet veri setiyle bizzat ince ayar (Fine-Tuning) yapılmış **128k BERTurk** modelini (`Emirhan41/bert-base-turkish-128k-istanbul-sentiment`) kullanmaktadır. Bu sayede yerel argo, ironi, sarkazm ve İstanbul ekonomi gündemine dair hassas anlamlandırma başarısı olağanüstü düzeye çıkarılmıştır!

---

## ✨ Öne Çıkan Özellikler (Özet)

*   **Çift-Katmanlı NLP Filtresi:** Metin temizliği, argo/küfür filtrelemesi ve büyük harf normalizasyonu.
*   **İroni ve Sarkazm Dedektörü:** Ünlem, emoji ve sarkastik ifadelerle ("uçuyoruz", "kıskanıyorlar") hatalı pozitif etiketleri negatife çevirme.
*   **Özel Override Kuralları:** Trafik şikayetleri ve protesto kelimelerinde otomatik negatif duygu kararı.
*   **Semantik Kopya Koruması (Deduplication):** `%75 semantik benzerlik` eşiğiyle spam/bot tweetlerini engelleme.
*   **Akıllı X API Kota Koruyucu:** Düşük adetli aramalarda günleri birleştirerek API kota israfını önleme.

---

## 🛠️ Adım Adım Kurulum ve Çalıştırma Rehberi

Bu bölüm, projeyi bilgisayarınızda sıfırdan kurup çalıştırmanız için gereken tüm adımları **en temel seviyeden** başlayarak anlatmaktadır.

### 1. Projeyi Bilgisayarınıza İndirin (Git Clone)
Bilgisayarınızda PowerShell (Windows) veya Terminal (Mac/Linux) uygulamasını açın ve projeyi GitHub'dan klonlayarak klasörün içine girin:
```bash
git clone https://github.com/balciemirhan/istanbul-economy-sentiment.git
cd istanbul-economy-sentiment
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktifleştirin
Projenin bağımlılıklarının bilgisayarınızdaki diğer Python projeleriyle çakışmaması için temiz bir sanal ortam (`venv`) kuruyoruz:

*   **Windows için (PowerShell):**
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
*   **Windows için (CMD - Komut İstemi):**
    ```cmd
    python -m venv venv
    call venv\Scripts\activate.bat
    ```
*   **macOS / Linux için:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
> [!NOTE]
> Sanal ortam başarıyla aktif olduğunda terminal satırınızın sol başında `(venv)` ibaresi belirecektir.

### 3. Gerekli Kütüphaneleri (Paketleri) Yükleyin
Sanal ortamınız aktifken aşağıdaki komutla tüm gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

#### 📦 Kurulan Paketler ve İşlevleri
Aşağıdaki paketler sistemin çalışması için arka planda kurulur:

| Paket Grubu | Paket Adı | Ne İşe Yarar? |
| :--- | :--- | :--- |
| **NLP & AI** | `transformers` | Yapay zeka duygu analizi modelini yükler ve çalıştırır. |
| | `torch` | Modeli çalıştıran PyTorch derin öğrenme motorudur. |
| | `sentencepiece` & `tiktoken` | Metinleri modelin anlayacağı sayısal ifadelere (token) böler. |
| **Deduplication** | `thefuzz` & `python-Levenshtein` | Tweetleri karşılaştırarak benzerlik oranını (%75 eşik) ölçer, spamleri eler. |
| **Database** | `sqlalchemy` | SQLite veritabanı ile Python kodları arasında güvenli köprü (ORM) kurar. |
| **Web API & UI** | `flask` & `flask-cors` | Dashboard arayüzünün backend API sunucusunu çalıştırır. |
| **Veri & Raporlama** | `pandas` & `openpyxl` | Excel raporları oluşturmayı ve veri okumayı sağlar. |
| **Yardımcılar** | `python-dotenv` | Gizli API anahtarlarını `.env` dosyasından güvenle okur. |

---

## 🤗 Akıllı ve Otomatik Model Kurulumu (Hugging Face)

Bu proje, İstanbul ekonomi ve ulaşım gündemine özel olarak eğitilmiş, **%99.60 doğrulama başarısı** ve **0.9960 Macro-F1 skoruna** sahip üstün yetenekli **128k BERTurk** yapay zeka modelini kullanır:
👉 **[Emirhan41/bert-base-turkish-128k-istanbul-sentiment](https://huggingface.co/Emirhan41/bert-base-turkish-128k-istanbul-sentiment)**

### ⚡ Sıfır Kurulum (Zero-Configuration) Kolaylığı
Modeli kullanmak veya indirmek için hiçbir manuel işlem yapmanıza gerek yoktur! Projeyi çalıştırdığınızda akıllı model yönetim mekanizması devreye girer:

1. **İlk Çalıştırmada Otomatik İndirme:** Sistem ilk kez başlatıldığında, Hugging Face Hub üzerinden **~737 MB** boyutundaki özel eğitilmiş modeli arka planda otomatik olarak indirmeye başlar. İnternet hızınıza bağlı olarak bu işlem **1-3 dakika** sürebilir.
2. **Yerel Önbellek (Cache) Desteği:** İndirilen model dosyaları bilgisayarınızın standart kullanıcı dizininde güvenli bir şekilde saklanır:
   * **Windows:** `C:\Users\<Kullanıcı_Adı>\.cache\huggingface\hub\`
   * **macOS / Linux:** `~/.cache/huggingface/hub/`
3. **Anında Başlatma:** Model bir kere indirildikten sonra sonraki çalıştırmaların tamamında doğrudan yerel diskten saniyeler içinde yüklenir ve internet bağlantısı gerektirmez.

> [!NOTE]
> Proje kodu içerisinde yerel geliştiriciler için opsiyonel `./fine_tuned_bert` klasör desteği de aktif tutulmuştur. Eğer model yerel klasörde bulunursa internete hiç çıkılmadan doğrudan oradan okunur.

---

## 🚀 Sistemi Çalıştırma Adımları

Sanal ortam aktif edildikten ve kütüphaneler kurulduktan sonra aşağıdaki adımları sırasıyla uygulayarak sistemi başlatın:

### 1. `.env` Dosyasını Yapılandırın
Projenin ana dizininde `.env` adında bir dosya oluşturun (veya varsa düzenleyin) ve içerisine kendi API anahtarlarınızı yazın:
```env
# X (Twitter) Developer API Kimlik Bilgileri
X_BEARER_TOKEN="BURAYA_TWITTER_BEARER_TOKEN_YAZIN"
X_API_KEY="BURAYA_API_KEY_YAZIN"
X_API_SECRET="BURAYA_API_SECRET_YAZIN"

# Yapay Zeka İçgörüleri İçin Gemini API Anahtarı
GEMINI_API_KEY="BURAYA_GEMINI_API_KEY_YAZIN"
```
> [!WARNING]
> `.env` dosyası şifre ve API anahtarlarınızı barındırdığından kesinlikle GitHub'a push edilmemelidir. Projedeki `.gitignore` dosyası bunu otomatik olarak engellemektedir.

### 2. Veritabanını Hazırlayın ve İlklendirin (Otomatik Demo Verisi Dahil!)
Hiçbir API anahtarınız veya veriniz olmasa bile sistemi anında test edebilmeniz için proje içerisinde **hazır analiz edilmiş 260 tweetlik bir demo veritabanı (`istanbul_ekonomi_demo.db`)** hazır olarak sunulmuştur. 

Aşağıdaki komutu çalıştırdığınızda sistem bu hazır verileri otomatik olarak algılayıp `istanbul_ekonomi.db` adıyla kopyalayacak ve veritabanını saniyeler içinde kullanıma hazır hale getirecektir:
```bash
python -c "from database.db_manager import init_db; init_db()"
```

*(Eğer sıfırdan boş bir veritabanı kurmak isterseniz, `istanbul_ekonomi_demo.db` dosyasını silmeniz veya adını değiştirmeniz yeterlidir. Ardından yukarıdaki komut boş veritabanını oluşturacak ve `python scripts/process_excel_tweets.py` komutuyla kendi Excel verilerinizi aktarabileceksiniz.)*

### 4. Web Arayüzünü (Dashboard) ve Sunucuyu Başlatın
Tüm hazırlıklar tamamlandıktan sonra Flask web sunucusunu ayağa kaldırmak için şu komutu yazın:
```bash
python dashboard/api/app.py
```

Sunucu başarıyla başladığında terminalde şu şekilde bir çıktı göreceksiniz:
```text
* Running on http://127.0.0.1:5000
* Model yükleniyor: (Bu işlem ilk seferde vakit alabilir)...
* Duygu analizi modeli başarıyla yüklendi.
```

### 5. Tarayıcınızda Arayüzü Açın
Tarayıcınızı (Chrome, Edge, Safari vb.) açın ve aşağıdaki adrese gidin:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

Artık canlı verileri çekebilir, duygu analiz sonuçlarını grafiklerle görebilir ve tek tıkla Excel formatında profesyonel raporlar indirebilirsiniz!
