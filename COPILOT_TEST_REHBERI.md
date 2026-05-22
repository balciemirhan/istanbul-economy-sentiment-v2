# 🚀 İstanbul Ekonomi AI Co-Pilot Test ve Mimari Rehberi

## 💡 İstanbul Co-Pilot Sistemi Nedir ve Nasıl Çalışır?

İstanbul Co-Pilot, **İstanbul Ekonomi ve Kamuoyu Analizi** veritabanındaki (SQLite) tweetleri, kullanıcı şikayetlerini ve duygu analizi verilerini akıllı bir şekilde analiz eden, belediye yöneticilerine ve veri analistlerine karar desteği sağlayan **akıllı bir AI Ajan (AI Agent) sistemidir.**

Sistem hibrit bir mimariye sahiptir ve şu şekilde çalışır:

1.  **Duygu Analizi (Python & BERT):** Projenin temel NLP modeli, bizzat 5.000+ tweet ile ince ayar (fine-tune) yapılmış **128k BERTurk** modelinin yerel versiyonunu ([fine_tuned_bert](file:///c:/SoftWares/Python/python_project/istanbulmetre_cardiffnlp_copilot/fine_tuned_bert)) kullanır. Tweetleri analiz ederek duygu durumlarını (`negatif`, `pozitif`, `nötr`) ve kategorilerini sınıflandırır ve veritabanına kaydeder.
2.  **Dashboard Arayüzü (Python Flask - Port 5000):** Kullanıcının verileri görsel olarak gördüğü, grafiklerin listelendiği ve Co-Pilot sohbet penceresinin yer aldığı premium kullanıcı arayüzüdür.
3.  **Co-Pilot Zekası (Java Spring Boot + LangChain4j - Port 8080):** Kullanıcı sohbet penceresinden bir soru sorduğunda, istek Java servisine iletilir. Java servisi LangChain4j ve Google Gemini API'yi kullanarak kullanıcının talebini yorumlar, gerekirse SQL veritabanından dinamik sorgular yapar veya grafik verisi üreterek cevabı zenginleştirir.

---

## 🏗️ 1. Mimari Tasarım ve LangChain4j Altyapısı

Java backend servisi, [LangChain4j](https://github.com/langchain4j/langchain4j) kütüphanesinin sağladığı deklaratif yapay zeka entegrasyonu üzerine kurulmuştur. Mimari temelde 3 ana sütundan oluşur:

```
  ┌──────────────────────────────────────────────────────────┐
  │                   SPRING BOOT CONTROLLER                 │
  │            (POST /api/copilot, GET /suggestions)         │
  └────────────────────────────┬─────────────────────────────┘
                               │ (Session Sync)
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 ISTANBUL COPILOT AGENT                   │
  │                   (@AiService / LLM)                     │
  └──────┬──────────────────────┬──────────────────────┬─────┘
         │                      │                      │
         ▼                      ▼                      ▼
  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
  │ CHAT MEMORY  │       │ DATABASE TOOL│       │  CHART TOOL  │
  │ (Window=15)  │       │(SQLite SELECT)│       │ (CSV Parser) │
  └──────────────┘       └──────────────┘       └──────────────┘
```

### A. AiServices (Bildirimsel Yapay Zeka Ajanı)
*   **Ajan Tanımı:** [IstanbulCopilotAgent.java](file:///c:/SoftWares/Python/python_project/istanbulmetre_cardiffnlp_copilot/istanbul-copilot-java/src/main/java/com/istanbulmetre/copilot/service/IstanbulCopilotAgent.java) interface'i, LangChain4j'nin `@AiService` anotasyonu ile işaretlenmiştir. Geliştirici olarak somut bir sınıf yazmak yerine sadece arayüz ve prompt tanımlanır; çalışma zamanında (runtime) LLM çağrıları, araç koordinasyonu ve hafıza yönetimi otomatik üstlenilir.
*   **System Instructions (@SystemMessage):** Co-Pilot'un uyması gereken 5 kritik kural (beşeri iletişim hassasiyeti, sıfır-sürtünmeli grafik çizimi, anti-hallucination veritabanı kuralları, 3 aşamalı acil aksiyon planları ve trend/anomali tespiti) sistem talimatlarında tanımlıdır.

### B. ChatMemory (Oturum Bazlı Bellek)
*   **Hafıza Sağlayıcısı (`ChatMemoryProvider`):** Her kullanıcı oturumu için son 15 mesajı hafızada tutan `MessageWindowChatMemory` yapısı yapılandırılmıştır.
*   **Oturum Senkronizasyonu:** Frontend'den gelen sohbet geçmişi (`history` payload'ı) her istekte Java `ChatMemory` nesnesi ile senkronize edilerek ajanın geçmiş bağlamı (context) kaybetmemesi güvenceye alınır.

### C. Gemini API Key Rotasyonu ve Hata Toleransı (Failover)
*   **Dinamik Yükleyici:** Sunucu başlarken `.env` dosyasını tarayarak API anahtarlarını okur.
*   **Key Rotasyonu:** Gemini API ücretsiz kullanım kotalarında sıkça karşılaşılan `429 Resource Exhausted (Quota Exceeded)` hatalarına karşı özel bir proxy sarmalayıcısı yazılmıştır. Havuzdaki 3 adet Gemini API anahtarı (`GEMINI_API_KEY=key1,key2,key3`) sırayla denenir. Bir anahtar hata verdiğinde, kesinti olmadan milisaniyeler içinde bir sonrakine geçiş yapılır.

---

## 🛠️ 2. Veritabanı ve Grafik Etkileşim Araçları (Toolkits)

Ajanın dış dünya ile etkileşime girmesini sağlayan iki ana araç seti ([DatabaseTools](file:///c:/SoftWares/Python/python_project/istanbulmetre_cardiffnlp_copilot/istanbul-copilot-java/src/main/java/com/istanbulmetre/copilot/tools/DatabaseTools.java) ve [ChartTools](file:///c:/SoftWares/Python/python_project/istanbulmetre_cardiffnlp_copilot/istanbul-copilot-java/src/main/java/com/istanbulmetre/copilot/tools/ChartTools.java)) Spring `@Component` olarak tanımlanıp ajana enjekte edilmiştir.

### A. Database Interaction Toolkit (`DatabaseTools.java`)
Ajanın SQLite veritabanına erişimini sağlayan ana araçtır.
*   **Sorgu Güvenliği (SELECT Enforcer):** Çalıştırılacak sorgunun en başına güvenlik kontrolü yerleştirilmiştir. Sorgu `SELECT` ifadesiyle başlamıyorsa veritabanına erişim engellenir ve ajana hata döndürülür.
*   **Dinamik Kolon Haritalaması:** Veritabanındaki gerçek tablo yapısı ile LLM'in ürettiği SQL sorguları arasındaki uyumsuzluğu gidermek için regex tabanlı bir dönüştürücü çalışır:
    *   `tweet_text` -> `text` (Gerçek kolon ismi)
    *   `irony` -> `is_ironic` (Gerçek kolon ismi)
*   **ThreadLocal Veri Yakalama:** Ajan veritabanını sorguladığında, dönen JSON sonucu sadece ajana verilmez; aynı zamanda HTTP Response gövdesine eklenmesi için `ThreadLocal<List<Map<String, Object>>>` deposuna kaydedilir. İstek bittiğinde temizlenir.

### B. Grafik Oluşturma Toolkit (`ChartTools.java`)
Kullanıcının grafik taleplerini yerine getiren araçtır.
*   **Gemini List Parametresi Çözümü (CSV Parser):** Gemini API'sinin katı JSON şeması doğrulaması, diziler (`List<String>`, `List<Integer>`) için `items` türü eksikliğinde `400 Bad Request` hatası vermekteydi. Bu engeli aşmak için araç metodu parametreleri düz metin (CSV) olarak tasarlanmıştır:
    *   `labelsCsv`: `"ulaşım, gıda, genel"`
    *   `dataCsv`: `"45, 12, 146"`
    *   Metot içinde bu CSV değerleri dinamik olarak bölünerek `List` nesnelerine dönüştürülür.
*   **ThreadLocal Grafik Verisi:** Çizilecek grafik tipi (bar, pie, line vb.), etiketler ve veriler `ThreadLocal<Map<String, Object>>` üzerinde depolanarak Controller katmanına taşınır ve frontend'in **Chart.js** ile çizim yapması sağlanır.

---

## 🚀 3. Hazırlık ve Sistemi Başlatma

Sistemde herhangi bir küresel Java veya Maven kurulumu yapmanıza **gerek yoktur**. Android Studio'nun yerleşik JDK 21 motorunu ve yerel Maven wrapper scriptimizi (`mvnw_local.cmd`) kullanan zero-friction altyapısı mevcuttur.

1.  **Flask Dashboard Sunucusunu Başlatın:**
    Terminalde proje kök dizininde şu komutu çalıştırın (Port 5000):
    ```powershell
    python dashboard/api/app.py
    ```
2.  **Java Co-Pilot Servisini Başlatın:**
    Ayrı bir terminal penceresinde `istanbul-copilot-java` klasörüne geçiş yapın ve yerel wrapper'ı tetikleyin (Port 8080):
    ```powershell
    cd istanbul-copilot-java
    .\mvnw_local.cmd spring-boot:run
    ```
3.  Tarayıcınızdan **[http://localhost:5000](http://localhost:5000)** adresine gidip sağ alt köşedeki **🤖 Co-Pilot** butonuna tıklayarak sohbet penceresini açın.

---

## 💎 4. Tüm Kullanım Senaryoları (Test Cases)

Aşağıdaki 9 ana senaryo, sistemin tüm yeteneklerini doğrulamak amacıyla tasarlanmıştır:

### 1️⃣ Canlı Veriye Dayalı Dinamik Öneriler (Suggestions)
*   **Amaç:** Co-Pilot ilk açıldığında veritabanı durumunu dinamik analiz edip öneriler hazırlamasını test etmek.
*   **Arka Plandaki İşleyiş:** Ajan çağrılmadan önce `CopilotSuggestionService` veritabanında en çok negatif bildirim biriken kategoriyi ve ironi içeren tweet sayılarını SQL sorgularıyla hesaplar.
*   **Test Yöntemi:** Sohbet penceresi ilk açıldığında **"💡 Önerilen Başlangıç Sorguları"** bölümündeki kartların canlı veriyle doldurulduğunu doğrulayın (Örn: *"En çok negatif bildirim Gayrimenkul kategorisinde..."*). Kartlardan birine tıklayıp otomatik gönderildiğini görün.

### 2️⃣ Sesli Sohbet ve Mikrofon Animasyonu (STT)
*   **Amaç:** Arayüzün ses tanıma durumlarını görsel olarak bildirmesini test etmek.
*   **Test Yöntemi:** Giriş alanındaki 🎤 (Mikrofon) butonuna basın. Çevresinde kırmızı yanıp sönen animasyon halkasının belirdiğini görün. Sesli olarak *"Merhaba"* deyin; sesin metne dönüşüp otomatik yollandığını izleyin.

### 3️⃣ Veritabanı Sorgulama ve Kolon Haritalama (Anti-Hallucination)
*   **Amaç:** Ajanın uydurma veri üretmek yerine SQLite veritabanına güvenli SELECT sorguları atmasını ve kolon isimlerini otomatik dönüştürmesini doğrulamak.
*   **Örnek Sorgular:**
    *   *"Ulaşımla ilgili en negatif 3 tweeti bana getirir misin?"*
    *   *"Sistemde sentimenti pozitif olan ve likes sayısı 10'dan fazla olan kayıtları listele."*
*   **Beklenen Sonuç:** Ajan arka planda `querySqliteDb` aracını tetikler, sorgudaki `tweet_text` terimini `text` olarak, `irony` terimini `is_ironic` olarak haritalandırır ve veritabanındaki **gerçek kayıtları** listeler.

### 4️⃣ Analitik Hesaplamalar ve Oran Sentezleme
*   **Amaç:** Ajanın veritabanından çektiği sayısal veriler üzerinde matematiksel oranlama yapabilme yeteneğini test etmek.
*   **Örnek Sorgular:**
    *   *"Kira ve barınma kategorisinde toplam kaç tweet var ve bunların yüzde kaçı negatif?"*
    *   *"Makro ekonomi kategorisindeki pozitif duygu oranımızın genel ortalamasını hesapla."*
*   **Beklenen Sonuç:** Ajan veritabanından ham sayıları çeker (`COUNT(*)` gruplamalarıyla), kendi bünyesinde bölme/oranlama işlemlerini gerçekleştirerek sonucu yüzde olarak sunar.

### 5️⃣ Sohbet Balonu İçinde Canlı Grafik Çizdirme (Zero-Friction Chart)
*   **Amaç:** Grafik taleplerinde asistanın uzun metinler yazmak yerine **SADECE** *"Grafiği yansıtıyorum"* diyerek sohbet balonunun içine interaktif **Chart.js** grafik kartı yerleştirmesini test etmek.
*   **Örnek Sorgular:**
    *   *"Kategorilere göre genel tweet sayılarını çubuk grafik (bar chart) olarak göster."*
    *   *"Ulaşım sentiment dağılımını bir pasta grafik (pie chart) olarak yansıt."*
*   **Beklenen Sonuç:** Ajan `generateChartJson` aracını çağırır. Dönen yanıt **SADECE** `"Grafiği yansıtıyorum"` metnidir. Arayüzün altına renk harmonisi premium olan interaktif Chart.js bileşeni enjekte edilir.

### 6️⃣ Yönetici Karar Destek Stratejileri (Timeline Cards)
*   **Amaç:** Karar alıcılar için hazırlanan 3 aşamalı eylem planlarının sohbet balonunda şık renkli kartlar olarak görselleştirilmesini test etmek.
*   **Örnek Sorgular:**
    *   *"İstanbul Büyükşehir Belediyesi yönetimi için ulaşımdaki negatif tweetlere yönelik 3 aşamalı eylem planı hazırlar mısın?"*
    *   *"Ekonomik zorluklar yaşayan esnaflar için belediyenin alabileceği Kısa, Orta ve Uzun vadeli karar destek planını çıkar."*
*   **Beklenen Sonuç:** Asistanın yanıtındaki Kısa, Orta ve Uzun vadeli başlıklar frontend JS motoru tarafından algılanır ve sırasıyla 🔴 **Kırmızı**, 🟡 **Sarı** ve 🟢 **Yeşil** renkli premium kartlar halinde timeline şeklinde listelenir.

### 7️⃣ Trend ve Anomali (Spike) Tespiti
*   **Amaç:** Zamana bağlı ani değişimleri ve anomali nedenlerini saptama yeteneğini doğrulamak.
*   **Örnek Sorgular:**
    *   *"Son çekilen verilerde negatif duygunun aniden sıçradığı (spike yaptığı) bir gün var mı, varsa arkasındaki katalizör nedir?"*
*   **Beklenen Sonuç:** Ajan verileri tarihe göre gruplayarak analiz eder, anomali gününü bulur ve o güne ait tweetlerin içeriklerini inceleyerek olayın arkasındaki somut tetikleyiciyi (örn: metro grevi haberi, zam dedikodusu vb.) açıklar.

### 8️⃣ İroni ve Sarkastik Tepki Analizi (Sarcasm Detector)
*   **Amaç:** İronik tweetlerin kamuoyu psikolojisindeki sosyo-ekonomik yansımalarını test etmek.
*   **Örnek Sorgular:**
    *   *"Sistemde ironi (is_ironic = 1) içeren tweetleri sorgula. Halk en çok hangi konuyu alaya almış?"*
*   **Beklenen Sonuç:** Ajan kinayeli (`is_ironic = 1`) kayıtları filtreler ve halkın öfke kusmak yerine alaycı ve sarkastik bir üslupla protesto ettiği konuları nedenleriyle özetler.

### 9️⃣ Kesintisiz Sohbet ve Hafıza Durum Takibi (Stateful Chat)
*   **Amaç:** ChatMemory yapısının önceki mesajların bağlamını (context) koruduğunu doğrulamak.
*   **Test Yöntemi:**
    1. Önce şunu sorun: *"Makro ekonomi kategorisinde en negatif 2 tweet hangisi?"*
    2. Gelen cevaptan sonra, konuyu tekrar belirtmeden şunu sorun: *"Peki bu tweetleri atan yazarların kullanıcı adları nedir?"*
*   **Beklenen Sonuç:** Asistan bir önceki soruyu ve çekilen verileri hafızasında tuttuğu için doğrudan o iki tweetin yazar kullanıcı adlarını doğru olarak cevaplayacaktır.

---

## 📈 Başarı Kriterleri Kontrol Listesi

Testleri yaparken arayüzde aşağıdaki detayların aktif olduğunu kontrol edin:
- [ ] Co-Pilot pencerelerinde arka plan **glassmorphic** (buzlu cam efekti) ve saydam mı?
- [ ] Mikrofon aktifken butonun etrafında **kırmızı pulse animasyonu** çalışıyor mu?
- [ ] Grafik çizdirildiğinde baloncuk içinde gerçek **Chart.js** grafiği render ediliyor mu?
- [ ] Eylem planlarında **🔴 Kısa, 🟡 Orta, 🟢 Uzun** vadeli kartlar renkli kutular halinde mi?
- [ ] Havuzdaki API anahtarlarından biri bloke edildiğinde sunucu çökmeden otomatik olarak diğerine geçiş yapıyor mu?
- [ ] Asistanın metinlerinde kalın yazılar (`**kalın**`) `<strong>` olarak, liste elemanları ise şık bullet list olarak render ediliyor mu?

İyi testler dileriz! Ajanınız her adımda size kılavuzluk etmek için hazır bekliyor. 🤖🚀
