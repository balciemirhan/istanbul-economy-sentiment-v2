import os
import sys
import numpy as np
import torch
import pandas as pd
import csv
from torch import nn
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    DataCollatorWithPadding,
    TrainerCallback
)
from datasets import Dataset

# Custom Premium Callback for visual terminal tracking
class PremiumProgressCallback(TrainerCallback):
    def __init__(self):
        super().__init__()

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
                max_steps = state.max_steps if state.max_steps else 1
                percent = (state.global_step / max_steps) * 100
                
                # Determine current Epoch integer
                current_epoch_int = int(epoch) + 1 if epoch < args.num_train_epochs else int(args.num_train_epochs)
                
                print(f"📈 [EPOCH {current_epoch_int}/{int(args.num_train_epochs)}] | "
                      f"Tamamlanma: %{percent:.1f} | "
                      f"Adım: {state.global_step}/{state.max_steps} | "
                      f"Kayıp (Loss): {loss:.4f} | "
                      f"Hız: {learning_rate:.2e}", flush=True)

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

    def on_train_end(self, args, state, control, **kwargs):
        print("\n" + "═"*75)
        print("✅  EĞİTİM TAMAMLANDI! En yüksek Makro F1-Skorlu model kaydediliyor...")
        print("═"*75 + "\n", flush=True)

# Reconfigure stdout/stderr to UTF-8 to prevent Windows encoding crashes
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Custom Trainer to handle Class Weights
class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")
        
        if self.class_weights is not None:
            weight_tensor = torch.tensor(self.class_weights, dtype=torch.float).to(model.device)
            loss_fct = nn.CrossEntropyLoss(weight=weight_tensor)
        else:
            loss_fct = nn.CrossEntropyLoss()
            
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    
    accuracy = np.mean(predictions == labels)
    
    # Calculate Macro F1
    unique_labels = [0, 1, 2]
    f1_scores = []
    
    for cls in unique_labels:
        tp = np.sum((predictions == cls) & (labels == cls))
        fp = np.sum((predictions == cls) & (labels != cls))
        fn = np.sum((predictions != cls) & (labels == cls))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        f1_scores.append(f1)
        
    macro_f1 = np.mean(f1_scores)
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "negatif_f1": f1_scores[0],
        "notr_f1": f1_scores[1],
        "pozitif_f1": f1_scores[2]
    }

def main():
    MODEL_NAME = "dbmdz/bert-base-turkish-128k-cased"
    TXT_PATH = "text,label,reason_5k.txt"
    MODEL_DIR = "./fine_tuned_bert"
    
    print("\n" + "="*75)
    print("🚀  İSTANBUL METRE - 3-SINIFLI BERTurk 128K DUYGU ANALİZİ MODEL EĞİTİMİ  🚀")
    print("="*75)
    
    # 💻 Donanım Tanılama ve Donanım Kartı Detayları
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"💻 Hedef Donanım : {str(device).upper()}")
    if device.type == "cuda":
        print(f"🎮 Ekran Kartı  : {torch.cuda.get_device_name(0)}")
        print(f"🔥 VRAM Kapasite: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("⚠️  UYARI: GPU bulunamadı, eğitim CPU üzerinden yavaş ilerleyecektir!")
    print("-"*75, flush=True)
    
    if not os.path.exists(TXT_PATH):
        # Fallback to default txt if 5k file is not generated yet
        print(f"⚠️  Uyarı: {TXT_PATH} bulunamadı, varsayılan 'text,label,reason.txt' kullanılıyor...")
        TXT_PATH = "text,label,reason.txt"
        
    if not os.path.exists(TXT_PATH):
        print(f"❌ Hata: Eğitim verisi bulunamadı: {TXT_PATH}")
        sys.exit(1)
        
    # 1. Veriyi Oku
    records = []
    with open(TXT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if not row or len(row) < 2:
                continue
            text = row[0].strip()
            label_str = row[1].strip()
            if text.lower() == "text" and label_str.lower() == "label":
                continue
            try:
                label = int(label_str)
                records.append({"text": text, "label": label})
            except ValueError:
                continue
                
    print(f"📦 Veri Yükleme: Toplam {len(records)} adet benzersiz tweet başarıyla okundu.")
    df = pd.DataFrame(records)
    
    # Sınıf Dağılımını Hesapla
    label_counts = df['label'].value_counts().to_dict()
    print("📊 Sınıf Dağılımı:")
    for lbl, cnt in sorted(label_counts.items()):
        name = "0: NEGATİF/İSYAN" if lbl == 0 else ("1: NÖTR/HABER" if lbl == 1 else "2: POZİTİF/MEMNUNİYET")
        print(f"   * Sınıf {name}: {cnt} adet")
        
    # Dengesizlikler için Class Weights hesapla
    total = len(df)
    class_weights = []
    for lbl in [0, 1, 2]:
        count = label_counts.get(lbl, 1)
        class_weights.append(total / (3.0 * count))
    print(f"⚖️  Dengeleyici Sınıf Ağırlıkları (Class Weights): {class_weights}")
    
    # 2. Train/Test Split
    train_df, val_df = train_test_split(df, test_size=0.1, random_state=42, stratify=df['label'])
    print(f"✂️  Veri Bölümleme: Eğitim Kümesi={len(train_df)} | Doğrulama Kümesi={len(val_df)}")
    print("-"*75, flush=True)
    
    # Convert to HuggingFace Dataset
    train_dataset = Dataset.from_pandas(train_df)
    val_dataset = Dataset.from_pandas(val_df)
    
    # 3. Tokenizer ve Model Yükleme
    print(f"🤖 Model ve Tokenizer Yükleniyor: {MODEL_NAME}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=3)
    
    def tokenize_function(examples):
        return tokenizer(examples['text'], truncation=True, max_length=128)
        
    train_tokenized = train_dataset.map(tokenize_function, batched=True)
    val_tokenized = val_dataset.map(tokenize_function, batched=True)
    
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    
    # 4. Eğitim Ayarları (Training Arguments)
    # EĞİTİM UYARISI: push_to_hub=True için huggingface-cli login yapılmış olması gerekmektedir.
    # Eğer oturum açık değilse veya token yoksa hata almamak için sistem otomatik olarak push_to_hub=False'a düşer.
    hf_token_exists = (
        os.getenv("HF_TOKEN") is not None or 
        os.path.exists(os.path.expanduser("~/.cache/huggingface/token")) or
        os.path.exists(os.path.expanduser("~/.huggingface/token"))
    )
    
    if not hf_token_exists:
        print("⚠️  UYARI: Hugging Face oturumu (token) bulunamadı. push_to_hub=True ayarı yerel eğitim için push_to_hub=False yapıldı.")
        print("💡 İpucu: Modeli HF Hub'a yollamak istiyorsanız lütfen terminalde 'huggingface-cli login' komutuyla giriş yapın.")
    
    training_args = TrainingArguments(
        output_dir="./bert-128k-istanbul-sentiment", # Kullanıcının tercih ettiği özel çıktı klasörü
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        weight_decay=0.01,
        warmup_steps=84,                    # 🌡️ Isınma adımı (warmup_ratio=0.1 karşılığı)
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_steps=10,
        report_to="none",
        disable_tqdm=True,  # Terminal karmaşasını önlemek ve özel çıktılarımızı görmek için tqdm devredışı
        push_to_hub=hf_token_exists          # Dinamik güvenlik kalkanı
    )
    
    # 5. Trainer Tanımlama
    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        class_weights=class_weights,
        callbacks=[PremiumProgressCallback()]  # Özel visual loglama takipçimiz
    )
    
    # 6. Eğitimi Başlat
    print("İnce ayar eğitimi (Fine-Tuning) başlatılıyor...")
    trainer.train()
    
    # 7. Modeli ve Tokenizer'ı Kaydet
    print(f"Eğitilen model kaydediliyor: {MODEL_DIR}")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    print("Eğitim başarıyla tamamlandı! Model hazır.")

if __name__ == "__main__":
    main()
