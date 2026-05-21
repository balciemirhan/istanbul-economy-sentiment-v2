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

## 📊 Model Karşılaştırma ve Performans Analizi (Savaş BERT vs. Yeni Fine-Tuned BERTurk)

Projenin v2 aşamasında yapılan en büyük iyileştirme, duygu analizi motorunun tamamen yenilenmesidir. Eski genel amaçlı **Savaş BERT** (`savasy/bert-base-turkish-sentiment-cased`) modeli ile yeni, 5.017 adet özel tweet ile ince ayar (fine-tuning) yapılmış yerel **128k BERTurk** (`Emirhan41/bert-base-turkish-128k-istanbul-sentiment`) modelinin karşılaştırmalı performans ve doğruluk analizi aşağıda detaylandırılmıştır.

### 1. 📈 İnce Ayarlı (Fine-Tuned) Modelin Eğitim Performansı
Modelimiz, yerel CPU/GPU kaynakları kullanılarak 3 epoch boyunca eğitilmiştir. Eğitim adımları ve doğrulama performansı metrikleri şu şekildedir:

| Epoch | Toplam Adım (Step) | Doğrulama Kaybı (Val Loss) | Genel Doğruluk (Val Accuracy) | Genel Makro F1-Skor | 🔴 Sınıf 0 F1 | 🟡 Sınıf 1 F1 | 🟢 Sınıf 2 F1 | Durum |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Epoch 1** | 283 | 0.0207 | %99.20 | 0.9920 | 0.9881 | 1.0000 | 0.9880 | Kararlı Başlangıç |
| **Epoch 2** | 566 | 0.0266 | %99.00 | 0.9900 | 0.9881 | 0.9970 | 0.9849 | Kararlı ve Dengeli |
| **Epoch 3** | **849** | **0.0142** | **%99.60** | **0.9960** | **0.9941** | **1.0000** | **0.9939** | 🏆 **En Başarılı Model (Seçilen)** |

> [!NOTE]
> **Epoch 3 Tercihi:** En düşük doğrulama kaybı (Val Loss: `0.0142`) ile en yüksek Makro F1-Skorunun (`0.9960`) kesiştiği an olan 3. Epoch, ezberleme (overfitting) riski taşımadan modelin en yüksek genelleme yeteneğine ulaştığı noktadır.

---

### 2. 🎯 Test Seti (260 Tweet) Üzerinde 1-to-1 Dağılım Karşılaştırması
Filtrelerden başarıyla geçmiş 260 adet gerçek/temiz tweetlik test seti üzerinde her iki modelin de tahmin dağılımları:

| Model | Pozitif Sayısı | Negatif Sayısı | Nötr Sayısı | Toplam Tweet |
| :--- | :---: | :---: | :---: | :---: |
| **Eski Savaş BERT (v1)** | 41 (%15.8) | 155 (%59.6) | 64 (%24.6) | 260 |
| **Yeni Fine-Tuned BERTurk (v2)** | **35 (%13.5)** | **141 (%54.2)** | **84 (%32.3)** | **260** |

*   **Karar Farklılığı:** İki model arasında 260 tweetin **82 adedinde (~%31.5)** uyuşmazlık tespit edilmiştir. Yeni modelimiz, eski modelin sığ kelime eşleştirmelerinden kaynaklanan hatalı tahminlerini düzeltmiştir.

#### 📊 Modeller Arası Performans ve Dağılım Grafikleri

Aşağıdaki grafikler iki modelin tahmin dağılımlarını ve sınıflandırma kararlarının geçiş matrisini (hangi duygunun nereye kaydığını) görselleştirmektedir:

<p align="center">
  <img src="reports/savas_vs_berturk_distribution.png" width="48%" alt="Modeller Arası Duygu Dağılım Grafiği" />
  <img src="reports/savas_vs_berturk_transitions.png" width="48%" alt="Sınıflandırma Karar Geçiş Matrisi (Heatmap)" />
</p>

---

### 3. 🧠 Sınıflandırma Karar Geçiş Analizi (Hata Düzeltme Yönleri)
Eski Savaş BERT ile Yeni BERTurk arasındaki **82 farklı kararın** detaylı dökümü:

1. **Savaş BERT'in `Negatif` Dediklerinden Dönenler:**
   * **25 Tweet ➔ `Nötr` Yapıldı:** Savaş BERT'in "enflasyon", "zorunlu", "darp" gibi kelimeleri görünce sığ bir panikle negatif etiketlediği resmi, hukuki ve duygusuz haber metinleri yeni modelimizce objektif haber diline uygun olarak nötrlendi.
   * **7 Tweet ➔ `Pozitif` Yapıldı:** *"Metro istiyoruz"* gibi yapıcı temenni/istekler ve taziye/dua içeren ifadeler doğru sınıfa taşındı.
2. **Savaş BERT'in `Nötr` Dediklerinden Dönenler:**
   * **9 Tweet ➔ `Negatif` Yapıldı:** Eski modelin algılayamadığı, sitem barındıran trafik ve yaşam kalitesi şikayetleri yeni modelce anında yakalandı.
   * **14 Tweet ➔ `Pozitif` Yapıldı:** Eski modelin kararsız kalıp nötre çektiği açık memnuniyet ifadeleri pozitife taşındı.
3. **Savaş BERT'in `Pozitif` Dediklerinden Dönenler:**
   * **9 Tweet ➔ `Negatif` Yapıldı:** Kelime avcılığına takılarak pozitif sanılan sitemkar ve ironik/sarkastik şikayetler negatif olarak düzeltildi.
   * **18 Tweet ➔ `Nötr` Yapıldı:** *"Otel açıldı"*, *"uçuşlar başladı"* gibi kuru turizm ve sektörel haberler nötrlendi.

---

### 🔍 Canlı Karşılaştırmalı Örnekler

İki modelin gerçek metinler üzerindeki performansı ve yeni modelin sarkazm/ironi anlama yeteneği:

| Örnek Metin | ❌ Eski Savaş BERT Tahmini | ✅ Yeni BERTurk Tahmini | Fark / Analiz |
| :--- | :---: | :---: | :--- |
| *"İstanbul trafiği artık dayanılmaz bir hal aldı, yollarda çürüdük resmen! #trafik #istanbul"* | `POZİTİF` (Güven: `0.53`) | `NEGATİF` (Güven: **`0.9996`**) | Ham model kelimeleri ayırt edemezken, yeni modelimiz **%99.96** güvenle negatif sınıfı yakalamıştır. |
| *"Mazota yine zam gelmiş, şahlanıyoruz maşallah uçuyoruz ülkece :)"* | `POZİTİF` (Güven: `0.52`) | `NEGATİF` (Güven: **`0.9997`**) | Yeni modelimiz "şahlanıyoruz", "uçuyoruz" ifadelerinin ardındaki **derin ironiyi (sarkasım) ve sitemi** mükemmel çözerek negatif etiketlemiştir. |
| *"İstanbul Büyükşehir Belediyesi toplu taşıma sefer saatlerinde güncelleme yaptı."* | `POZİTİF` (Güven: `0.45`) | `NÖTR` (Güven: **`0.9999`**) | Duygu içermeyen salt bilgilendirici resmi duyuruyu modelimiz neredeyse **%100** güvenle nötr sınıfa yerleştirmiştir. |
| *"Sonunda aradığımız gibi bir daire bulduk İstanbul'da, her şey çok güzel gidiyor 😊"* | `POZİTİF` (Güven: `0.49`) | `POZİTİF` (Güven: **`0.9998`**) | Pozitif memnuniyeti yüksek güvenle doğru şekilde etiketlemiştir. |
| *"İstanbul Deft. 13.10.2025 t. 1305618 s. özelge... mezkur Kanun hükümleri çerçevesinde enflasyon düzeltmesi yapılması zorunlu olup..."* | `NEGATİF` (Güven: `0.92`) | `NÖTR` (Güven: **`0.9984`**) | Savaş BERT "enflasyon" ve "zorunlu" kelimelerini görünce panikle negatif etiketlemiş, yeni model ise yasal bildirim olduğunu anlayarak nötrlemiştir. |
| *"Sayın İstanbul Büyükşehir Belediyesi, BEYLİKDÜZÜ’NE METRO İSTİYORUZ..."* | `NEGATİF` (Güven: `0.94`) | `POZİTİF` (Güven: **`0.9729`**) | Eski model talep/istek içeren cümleyi şikayet sanıp negatif derken, yeni modelimiz geleceğe yönelik yapıcı istekleri pozitif algılamıştır. |

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
git clone https://github.com/balciemirhan/istanbul-economy-sentiment-v2.git
cd istanbul-economy-sentiment-v2
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

### 3. Web Arayüzünü (Dashboard) ve Sunucuyu Başlatın
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

### 4. Tarayıcınızda Arayüzü Açın
Tarayıcınızı (Chrome, Edge, Safari vb.) açın ve aşağıdaki adrese gidin:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

Artık canlı verileri çekebilir, duygu analiz sonuçlarını grafiklerle görebilir ve tek tıkla Excel formatında profesyonel raporlar indirebilirsiniz!
