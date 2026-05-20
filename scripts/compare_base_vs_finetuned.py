import sys
import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

base_model_name = "dbmdz/bert-base-turkish-128k-cased"
fine_tuned_name = "./fine_tuned_bert"

device = 0 if torch.cuda.is_available() else -1

print("--- Modeller Yükleniyor (BERTurk 128k) ---")
try:
    # Load tokenizer and models
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    base_model = AutoModelForSequenceClassification.from_pretrained(base_model_name, num_labels=3)
    base_analyzer = pipeline("sentiment-analysis", model=base_model, tokenizer=tokenizer, device=device)
except Exception as e:
    print(f"Base model yüklenirken hata oluştu: {e}")
    sys.exit(1)

if not os.path.exists(fine_tuned_name):
    print(f"Uyarı: İnce ayarlı model '{fine_tuned_name}' henüz eğitilmemiş!")
    print("Lütfen önce eğitimi tamamlayın. Şimdilik sadece Base Model tahminlerini test edebilirsiniz.")
    fine_tuned_analyzer = None
else:
    try:
        ft_tokenizer = AutoTokenizer.from_pretrained(fine_tuned_name)
        ft_model = AutoModelForSequenceClassification.from_pretrained(fine_tuned_name, num_labels=3)
        fine_tuned_analyzer = pipeline("sentiment-analysis", model=ft_model, tokenizer=ft_tokenizer, device=device)
    except Exception as e:
        print(f"İnce ayarlı model yüklenirken hata oluştu: {e}")
        fine_tuned_analyzer = None

# Human readable label mapping
LABEL_MAP = {
    "LABEL_0": "0: NEGATİF/İSYAN/SARKASTİK",
    "LABEL_1": "1: NÖTR/RESMİ/HABER",
    "LABEL_2": "2: POZİTİF/MEMNUNİYET"
}

test_texts = [
    "İstanbul trafiği artık dayanılmaz bir hal aldı, yollarda çürüdük resmen! #trafik #istanbul",
    "Mazota yine zam gelmiş, şahlanıyoruz maşallah uçuyoruz ülkece :)",
    "İstanbul Büyükşehir Belediyesi toplu taşıma sefer saatlerinde güncelleme yaptı.",
    "Borsa İstanbul güne hafif düşüşle başladı, döviz kurları stabil seyrediyor.",
    "Sonunda aradığımız gibi bir daire bulduk İstanbul'da, her şey çok güzel gidiyor 😊"
]

print("\n--- Karşılaştırmalı Test Sonuçları ---")
for text in test_texts:
    print(f"Metin: {text}")
    
    # Base Model Prediction
    base_res = base_analyzer(text, truncation=True, max_length=128)[0]
    base_label = LABEL_MAP.get(base_res['label'], base_res['label'])
    print(f"  Base Model (Eğitimsiz)   : Label={base_label}, Score={base_res['score']:.4f}")
    
    # Fine-Tuned Model Prediction
    if fine_tuned_analyzer:
        ft_res = fine_tuned_analyzer(text, truncation=True, max_length=128)[0]
        ft_label = LABEL_MAP.get(ft_res['label'], ft_res['label'])
        print(f"  Fine-Tuned (İnce Ayarlı): Label={ft_label}, Score={ft_res['score']:.4f}")
    else:
        print("  Fine-Tuned (İnce Ayarlı): [Henüz Eğitilmedi]")
        
    print("-" * 70)
