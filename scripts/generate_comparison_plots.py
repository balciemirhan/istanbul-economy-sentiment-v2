import sys
import os
import pandas as pd
import torch
from transformers import pipeline
import matplotlib.pyplot as plt
import numpy as np

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Root dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.text_cleaner import clean_tweet_text, contains_profanity
from nlp.irony_detector import detect_irony, flip_sentiment
try:
    from thefuzz import fuzz
except ImportError:
    fuzz = None

# Sınıf kelimelerini belirle
pure_negative_keywords = [
    "protesto", "eylem", "yürüyoruz", "yoksulluk", "açlık", "geçinemiyoruz", "pahalılık", "istifa", 
    "isyan", "arızası", "rötar", "kaza yaptı", "kilitlendi", "çilesi", "pahalı", "belanızı", "belası", 
    "iş değil", "yerlerde", "rezalet", "soygun", "hırsızlık", "çıldırdım", "çıldırırsın"
]

def get_passed_tweets(excel_path):
    df = pd.read_excel(excel_path)
    seen_texts = []
    passed_tweets = []
    
    for i, row in df.iterrows():
        raw_text = str(row.get('text', ''))
        cleaned_text = clean_tweet_text(raw_text)
        
        # A. Uzunluk kontrolü
        if len(cleaned_text) < 15:
            continue
            
        # B. Küfür/kaba kelime kontrolü
        if contains_profanity(raw_text):
            continue
            
        # C. Semantik kopya / duplicate kontrolü
        is_duplicate = False
        if fuzz is not None:
            for past_text in seen_texts:
                if fuzz.token_set_ratio(cleaned_text, past_text) >= 75:
                    is_duplicate = True
                    break
        else:
            if any(cleaned_text[:50] == pt[:50] for pt in seen_texts):
                is_duplicate = True
                
        if is_duplicate:
            continue
            
        # Geçen tweeti ekle
        seen_texts.append(cleaned_text)
        passed_tweets.append(row.to_dict())
        
    return passed_tweets

def map_savas_label(label):
    label = label.lower()
    if "negative" in label or "label_0" in label:
        return "negatif"
    elif "positive" in label or "label_1" in label:
        return "pozitif"
    return "notr"

def map_ft_label(label):
    label = label.lower()
    if label == "label_0":
        return "negatif"
    elif label == "label_1":
        return "notr"
    elif label == "label_2":
        return "pozitif"
    return "notr"

def process_pipeline(raw_text, pipe, is_three_class):
    clean_text = clean_tweet_text(raw_text)
    if not clean_text:
        return "notr", 0.0, False
        
    # Model Tahmini
    res = pipe(clean_text, truncation=True, max_length=512)[0]
    score = res['score']
    
    # Etiket Eşleme
    if is_three_class:
        base_sentiment = map_ft_label(res['label'])
    else:
        base_sentiment = map_savas_label(res['label'])
        # 2-sınıflı eski Savaş modelinde güven skoru %85 altındaysa Nötr yapıyoruz
        if score < 0.85:
            base_sentiment = "notr"
            
    # İroni kontrolü ve ters yüz etme
    is_ironic = detect_irony(raw_text)
    final_sentiment = flip_sentiment(base_sentiment) if is_ironic else base_sentiment
    
    # Kurallar
    raw_lower = raw_text.lower()
    if final_sentiment in ["pozitif", "notr"]:
        if any(kw in raw_lower for kw in pure_negative_keywords):
            final_sentiment = "negatif"
        elif any(t in raw_lower for t in ["trafik", "trafiğ"]):
            if not any(good_word in raw_lower for good_word in ["yok", "açık", "rahat", "boş", "akıyor"]):
                final_sentiment = "negatif"
        elif any(kw in raw_lower for kw in ["tanker", "konteynır", "fıçısı"]) and "kanal istanbul" in raw_lower:
            final_sentiment = "notr"
            
    return final_sentiment, score, is_ironic

def main():
    excel_path = "pilot_v5_tweets 1copybudikkat.xlsx"
    if not os.path.exists(excel_path):
        print(f"Excel dosyası bulunamadı: {excel_path}")
        return
        
    print("Excel tweetleri okunuyor ve filtreleniyor...")
    passed_tweets = get_passed_tweets(excel_path)
    print(f"Toplam Filtreyi Geçen Tweet Sayısı: {len(passed_tweets)}")
    
    device = 0 if torch.cuda.is_available() else -1
    
    print("\n--- Savaş BERT Modeli Yükleniyor ---")
    savas_pipe = pipeline("sentiment-analysis", model="savasy/bert-base-turkish-sentiment-cased", device=device)
    
    print("\n--- Yeni Fine-Tuned BERTurk Modeli Yükleniyor ---")
    ft_pipe = pipeline("sentiment-analysis", model="./fine_tuned_bert", device=device)
    
    print("\nTüm tweetler her iki model ile analiz ediliyor...")
    
    savas_preds = []
    ft_preds = []
    
    for i, tweet in enumerate(passed_tweets):
        text = tweet['text']
        label_savas, _, _ = process_pipeline(text, savas_pipe, is_three_class=False)
        label_ft, _, _ = process_pipeline(text, ft_pipe, is_three_class=True)
        
        savas_preds.append(label_savas)
        ft_preds.append(label_ft)
        
    os.makedirs("reports", exist_ok=True)
    
    # --- PLOT 1: DAĞILIM KARŞILAŞTIRMASI BAR PLOT ---
    print("Grafik 1 çiziliyor: Duygu Dağılım Karşılaştırması...")
    classes = ['pozitif', 'negatif', 'notr']
    turkish_classes = ['Pozitif', 'Negatif', 'Nötr']
    
    savas_counts = [savas_preds.count(c) for c in classes]
    ft_counts = [ft_preds.count(c) for c in classes]
    
    x = np.arange(len(classes))
    width = 0.35
    
    # Premium Modern Tasarım Ayarları
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    
    rects1 = ax.bar(x - width/2, savas_counts, width, label='Eski Savaş BERT', color='#e74c3c', alpha=0.85, edgecolor='black', linewidth=0.7)
    rects2 = ax.bar(x + width/2, ft_counts, width, label='Yeni Fine-Tuned BERTurk', color='#2ecc71', alpha=0.85, edgecolor='black', linewidth=0.7)
    
    ax.set_ylabel('Tweet Sayısı', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_title('Modeller Arası Duygu Sınıflandırması Dağılımı (260 Temiz Tweet)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(turkish_classes, fontsize=11, fontweight='bold')
    ax.legend(frameon=True, facecolor='white', edgecolor='gray', fontsize=11)
    
    # Barların üstüne sayıları yazdır
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            percentage = (height / 260) * 100
            ax.annotate(f'{height}\n({percentage:.1f}%)',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='semibold')
            
    autolabel(rects1)
    autolabel(rects2)
    
    fig.tight_layout()
    dist_img_path = 'reports/savas_vs_berturk_distribution.png'
    plt.savefig(dist_img_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Grafik 1 başarıyla kaydedildi: {dist_img_path}")
    
    # --- PLOT 2: GEÇİŞ MATRİSİ ISI HARİTASI (HEATMAP) ---
    print("Grafik 2 çiziliyor: Geçiş Matrisi (Heatmap)...")
    matrix = np.zeros((3, 3), dtype=int)
    class_to_idx = {'pozitif': 0, 'negatif': 1, 'notr': 2}
    
    for s_p, f_p in zip(savas_preds, ft_preds):
        s_idx = class_to_idx[s_p]
        f_idx = class_to_idx[f_p]
        matrix[s_idx, f_idx] += 1
        
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    im = ax.imshow(matrix, cmap='Blues', interpolation='nearest')
    
    # Renk çubuğunu ekle
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Eşleşen Tweet Sayısı', rotation=-90, va="bottom", fontsize=10, fontweight='bold')
    
    # Etiketler ve Başlıklar
    ax.set_xticks(np.arange(len(classes)))
    ax.set_yticks(np.arange(len(classes)))
    ax.set_xticklabels(turkish_classes, fontsize=11, fontweight='bold')
    ax.set_yticklabels(turkish_classes, fontsize=11, fontweight='bold')
    
    # Eksen İsimleri
    ax.set_xlabel('Yeni Fine-Tuned BERTurk Kararı', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Eski Savaş BERT Kararı', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_title('Sınıflandırma Değişim Matrisi / Karar Geçişleri', fontsize=13, fontweight='bold', pad=15)
    
    # Matris Hücre Değerlerini Yaz
    thresh = matrix.max() / 2.
    for i in range(3):
        for j in range(3):
            text_color = "white" if matrix[i, j] > thresh else "black"
            ax.text(j, i, f"{matrix[i, j]}",
                    ha="center", va="center", color=text_color, fontsize=12, fontweight='bold')
            
    fig.tight_layout()
    matrix_img_path = 'reports/savas_vs_berturk_transitions.png'
    plt.savefig(matrix_img_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Grafik 2 başarıyla kaydedildi: {matrix_img_path}")
    
    print("\nGrafik üretimi başarıyla tamamlandı. Raporlar ve görseller reports/ altında hazır!")

if __name__ == "__main__":
    main()
