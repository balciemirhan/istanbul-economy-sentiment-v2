import sys
import os
import pandas as pd

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Root dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.sentiment_analyzer import SentimentAnalyzer

def calculate_metrics(y_true, y_pred):
    classes = ['pozitif', 'negatif', 'notr']
    correct = sum(1 for gt, pr in zip(y_true, y_pred) if gt == pr)
    accuracy = correct / len(y_true) if len(y_true) > 0 else 0
    
    metrics = {}
    f1_sum = 0
    for cls in classes:
        tp = sum(1 for gt, pr in zip(y_true, y_pred) if gt == cls and pr == cls)
        fp = sum(1 for gt, pr in zip(y_true, y_pred) if gt != cls and pr == cls)
        fn = sum(1 for gt, pr in zip(y_true, y_pred) if gt == cls and pr != cls)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics[cls] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'count': sum(1 for gt in y_true if gt == cls)
        }
        f1_sum += f1
        
    macro_f1 = f1_sum / len(classes)
    return accuracy, macro_f1, metrics

def evaluate():
    print("=== NLP Modelleri Karşılaştırmalı Performans Analizi ===")
    
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'gold_labels.csv')
    if not os.path.exists(csv_path):
        print(f"Hata: gold_labels.csv dosyası bulunamadı: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    
    # Sadece gold_label sütunu dolu olan ve geçerli sınıflara sahip satırları al
    df = df[df['gold_label'].isin(['pozitif', 'negatif', 'notr'])].copy()
    
    total_samples = len(df)
    if total_samples == 0:
        print("Değerlendirme için geçerli etiketlenmiş veri bulunamadı.")
        return
        
    print(f"Toplam {total_samples} adet etiketli gold veri üzerinden analiz yapılıyor...")
    
    # 1. Eski Modelin Performansı (csv'deki db_label)
    y_true = df['gold_label'].tolist()
    y_old_pred = df['db_label'].tolist()
    
    old_acc, old_f1, old_metrics = calculate_metrics(y_true, y_old_pred)
    
    # 2. Yeni Modelin Performansı (SentimentAnalyzer üzerinden tahmin)
    print("Yeni SentimentAnalyzer yükleniyor ve tahminler alınıyor...")
    sa = SentimentAnalyzer()
    
    y_new_pred = []
    for text in df['text']:
        res = sa.analyze(text)
        y_new_pred.append(res['sentiment'])
        
    new_acc, new_f1, new_metrics = calculate_metrics(y_true, y_new_pred)
    
    # Sonuçları ekrana yazdır
    model_desc = "İnce Ayar 3-Sınıf BERTurk" if getattr(sa, "is_three_class", False) else "Mevcut SavasY BERT + Kurallar"
    print("\n=========================================================================")
    print("                      PERFORMANS KARŞILAŞTIRMA                           ")
    print("=========================================================================")
    print(f"| Metrik    | Eski Model (Veritabanı)    | {model_desc.ljust(35)} |")
    print(f"|-----------|----------------------------|-------------------------------------|")
    print(f"| Accuracy  | {old_acc*100:23.2f}% | {new_acc*100:35.2f}% |")
    print(f"| Macro-F1  | {old_f1:24.4f} | {new_f1:36.4f} |")
    print("=========================================================================")
    
    print("\n--- Sınıf Bazında F1-Skorları ---")
    for cls in ['pozitif', 'negatif', 'notr']:
        print(f"[{cls.upper()}] (n={old_metrics[cls]['count']}):")
        print(f"  Eski Model: F1 = {old_metrics[cls]['f1']:.4f} (P={old_metrics[cls]['precision']:.4f}, R={old_metrics[cls]['recall']:.4f})")
        print(f"  Yeni Model: F1 = {new_metrics[cls]['f1']:.4f} (P={new_metrics[cls]['precision']:.4f}, R={new_metrics[cls]['recall']:.4f})")

if __name__ == "__main__":
    evaluate()
