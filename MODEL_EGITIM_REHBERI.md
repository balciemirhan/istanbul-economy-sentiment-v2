# 🧠 İSTANBUL METRE - BERTurk DUYGU ANALİZİ MODEL EĞİTİM REHBERİ

Bu kılavuz, yerel bilgisayarınızda (local) gerçekleştireceğimiz **3-Sınıflı BERTurk Duygu Analizi Model İnce Ayar (Fine-Tuning)** eğitiminin hangi temel model, hangi veri setleri ve hangi teknik parametrelerle yapılacağını anlatan kapsamlı teknik başvuru kaynağıdır.

---

## 1. 🤖 Hangi Temel Modeli Kullanıyoruz?

Eğitimde temel model (base model) olarak Alman Yapay Zeka Araştırma Merkezi (DFKI) tarafından geliştirilen ve Türkçe NLP topluluğunun altın standardı olan **BERTurk** modelini kullanıyoruz:

*   **Model Adı:** `dbmdz/bert-base-turkish-128k-cased`
*   **Mimari:** BERT-Base (Bidirectional Encoder Representations from Transformers)
*   **Kelime Haznesi (Vocabulary Size):** **128.000 Benzersiz Kelime / Alt-kelime token'ı.**
*   **Neden En İyisi?** 
    *   **Devasa Türkçe Kelime Haznesi (128k):** Standart Türkçe modeller (genelde 32k) İstanbul argosu, sosyal medya kısaltmaları, sektörel terimler ve ek almış kelimeleri (örn: *trafiğindeyiz*, *zamlandı*, *ulaşamadım*) tam göremez ve böler. BERTurk 128k, bu kelimeleri tek parça halinde anlayarak anlamsal bütünlüğü korur.
    *   **Harf Duyarlılığı (Cased):** Özel isimleri, büyük harfle yazılmış sitemleri/bağırmaları ve markaları çok daha hassas ayırt eder.
    *   **İki Yönlü Anlam Takibi:** Cümleyi sadece soldan sağa değil, sağdan sola da analiz ederek sosyal medyadaki sarkastik (alaycı/iğneleyici) anlatımları mükemmel çözer.

---

## 2. 📦 Hangi Veriler ile Eğiteceğiz?

Eğitim veri setimiz, yapay zeka ile üretilmiş ve matematiksel olarak kusursuz dengelenmiş **5.017 adet Türkçe tweet** içeren **`text,label,reason_5k.txt`** veri kümesidir.

### A. 📊 Sınıf Dağılımları (Class Distributions)
Eğitim setimizdeki 3 ana sınıfın dağılımı birbirine neredeyse tamamen eşittir. Bu, modelin bir sınıfı (örneğin negatifleri) ezberleyip diğerlerini göz ardı etmesini (overfitting/bias) engeller:

| Sınıf Kodu | Sınıf Anlamı | Dağılım Adedi | Yüzdelik Oranı |
| :---: | :--- | :---: | :---: |
| **Sınıf 0** | 🔴 **NEGATİF / İSYAN / SARKASTİK** (Trafik çilesi, hayat pahalılığı, zamlar vb.) | 1.685 adet | %33.58 |
| **Sınıf 1** | 🟡 **NÖTR / RESMİ / HABER** (Yol durumları, belediye duyuruları, vize haberleri vb.) | 1.680 adet | %33.49 |
| **Sınıf 2** | 🟢 **POZİTİF / MEMNUNİYET** (Ulaşım rahatlığı, güzel hava, başarılı belediye işleri vb.) | 1.652 adet | %32.93 |
| **TOPLAM** | 🚀 **Dengeli Veri Kümesi** | **5.017 adet** | **%100.00** |

### B. 🎯 12-Hücreli Matematiksel Kategori Matrisi
Tweetler, İstanbul Ekonomi Analizi'nin ihtiyaç duyduğu 4 ana sektör ve 3 duygu durumunun kesişiminden oluşan 12 hücreli bir matrise göre dağıtılmıştır:

1.  **Makro Ekonomi:** Hayat pahalılığı, kira fiyatları, asgari ücret memnuniyetsizlikleri veya resmi faiz haberleri.
2.  **Ulaşım & Lojistik:** Taksi şoförleriyle yaşanan tartışmalar, metro sefer güncellemeleri, vapur keyfi veya trafik yoğunluğu şikayetleri.
3.  **Gayrimenkul & İnşaat:** Deprem güçlendirme projeleri, fahiş ev kiraları, yeni konut projeleri veya tapu duyuruları.
4.  **Ticaret & Perakende:** İhracat/ithalat rakamları, esnaf şikayetleri, indirim kampanyaları veya market fiyatı denetimleri.

---

## 3. ⚙️ İnce Ayar (Fine-Tuning) Teknik Detayları ve Kod Yapısı

Eğitimi yönetecek olan [train_bert_3class.py](file:///c:/SoftWares/Python/python_project/istanbulmetre_cardiffnlp/scripts/train_bert_3class.py) scripti, Hugging Face `Trainer` kütüphanesini kullanarak en modern derin öğrenme tekniklerini uygular. 

### A. Donanım Tanılama (GPU & VRAM)
Kodumuz çalışmaya başladığında bilgisayarınızda bir NVIDIA GPU (CUDA yardımıyla) olup olmadığını kontrol eder. Eğer varsa eğitim tamamen ekran kartı belleği (VRAM) üzerinde son derece hızlı gerçekleşir. GPU yoksa CPU'ya güvenli şekilde düşer (fallback).

### B. Kayıp Fonksiyonu ve Sınıf Ağırlıkları (Weighted Loss)
Verilerimiz dengeli olsa da, modelin eğitim esnasında daha kararlı öğrenebilmesi için Cross Entropy kayıp fonksiyonuna **Sınıf Ağırlıkları (Class Weights)** uygulanır. Ağırlık formülü şöyledir:
$$\text{Sınıf Ağırlığı} = \frac{\text{Toplam Örnek Sayısı}}{3 \times \text{Sınıftaki Örnek Sayısı}}$$

### C. Hiperparametreler (Hyperparameters)
Eğitim ayarlarımız, modelin aşırı öğrenmeye (overfitting) düşmeden en yüksek zekaya ulaşması için hassas ayarlanmıştır:

```python
training_args = TrainingArguments(
    output_dir="./bert-128k-istanbul-sentiment", # Kullanıcının tercih ettiği özel çıktı klasörü
    learning_rate=2e-5,            # Öğrenme hızı (Yavaş ve sağlam adımlarla öğrenme)
    per_device_train_batch_size=16,# Her adımda GPU belleğine beslenecek tweet sayısı
    per_device_eval_batch_size=16, # Değerlendirme paket boyutu
    num_train_epochs=3,            # Toplam epoch sayısı (3 Epoch altın orandır, ezberi önler)
    weight_decay=0.01,             # Ezber bozucu regülarizasyon (L2 Regularization)
    warmup_ratio=0.1,              # 🌡️ Isınma turu (%10'luk kısımda öğrenme oranını yavaşça artırır)
    evaluation_strategy="epoch",   # Her epoch sonunda doğruluğu ölç
    save_strategy="epoch",         # Her epoch sonunda modeli diske kaydet
    load_best_model_at_end=True,   # Eğitim bittiğinde en yüksek Makro F1 skorlu checkpoint'i otomatik yükle
    metric_for_best_model="macro_f1", # Başarıyı ölçtüğümüz temel metrik (Makro F1-Skor)
    greater_is_better=True,
    logging_steps=10,              # Her 10 adımda bir ekrana ilerleme durumunu yazdır
    report_to="none",
    disable_tqdm=True,             # Terminalde karmaşayı önlemek için standart HF barını kapat
    push_to_hub=hf_token_exists    # Hugging Face oturumu varsa doğrudan HF Hub'a yollar
)
```

### D. 📈 Terminal Takip Sistemi: PremiumProgressCallback
Eğitimi terminalden anlık olarak, tertemiz bir görsel şölen eşliğinde takip etmeniz için geliştirdiğimiz özel takip kod bloğu:

```python
class PremiumProgressCallback(TrainerCallback):
    def on_train_begin(self, args, state, control, **kwargs):
        print("\n" + "═"*75)
        print("🟢  İNCE AYAR EĞİTİMİ (FINE-TUNING) BAŞLATILDI!  🟢")
        print("    * Eğitim süresince kayıp (loss) değerleri 10 adımda bir yazdırılacaktır.")
        print("    * Her epoch sonunda doğrulama kümesi ile performans test edilecektir.")
        print("═"*75 + "\n", flush=True)

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            loss = logs.get("loss")
            learning_rate = logs.get("learning_rate")
            epoch = logs.get("epoch")
            if loss is not None:
                print(f"📈 [Epoch {epoch:.2f} / {args.num_train_epochs}] "
                      f"Adım (Step): {state.global_step:<4} | "
                      f"Eğitim Kaybı (Train Loss): {loss:.4f} | "
                      f"Öğrenme Hızı: {learning_rate:.2e}", flush=True)

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics:
            val_loss = metrics.get("eval_loss", 0.0)
            val_acc = metrics.get("eval_accuracy", 0.0)
            val_f1 = metrics.get("eval_macro_f1", 0.0)
            neg_f1 = metrics.get("eval_negatif_f1", 0.0)
            neu_f1 = metrics.get("eval_notr_f1", 0.0)
            pos_f1 = metrics.get("eval_pozitif_f1", 0.0)
            epoch = metrics.get("eval_epoch", 0.0)
            
            print("\n" + "─"*75)
            print(f"📊  [EPOCH {epoch:.0f} SONU DEĞERLENDİRME SONUÇLARI]")
            print(f"    * Doğrulama Kaybı (Val Loss)      : {val_loss:.4f}")
            print(f"    * Genel Doğruluk (Accuracy)       : {val_acc*100:.2f}%")
            print(f"    * Genel Makro F1-Skor             : {val_f1:.4f}")
            print("    " + "-"*50)
            print(f"    🔴 Sınıf 0 (Negatif) F1-Skor      : {neg_f1:.4f}")
            print(f"    🟡 Sınıf 1 (Nötr) F1-Skor         : {neu_f1:.4f}")
            print(f"    🟢 Sınıf 2 (Pozitif) F1-Skor      : {pos_f1:.4f}")
            print("─"*75 + "\n", flush=True)
```

---

## 4. 🚀 Eğitimi Yerelde Başlatmak İçin Hazır mıyız?

Tüm yapılandırma testleri başarıyla tamamlandı. Eğitim öncesi sisteminizin GPU gücünü kontrol ettikten sonra terminalinize şu komutu yazarak süreci anlık izleyebilirsiniz:

```bash
python scripts/train_bert_3class.py
```

> [!TIP]
> **Eğitim Bittikten Sonra Ne Yapacağız?**  
> Eğitim tamamlandığında, en başarılı model `./fine_tuned_bert` klasörüne otomatik olarak kaydedilecektir. Sonrasında modellerin başarımını test etmek için `python scripts/compare_base_vs_finetuned.py` komutunu çalıştırarak, eski eğitimsiz ham model ile yeni ince ayarlı yerel zekamızın tahmin farklarını canlı olarak test edebiliriz!
