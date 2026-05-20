import sys
import os
import logging
import datetime
import pandas as pd

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Root dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import (
    init_db, save_tweets_bulk, get_recent_tweet_texts, get_active_keywords
)
from nlp.sentiment_analyzer import SentimentAnalyzer
from nlp.text_cleaner import clean_tweet_text, contains_profanity

try:
    from thefuzz import fuzz
except ImportError:
    fuzz = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def classify_category(text, active_keywords):
    """Tweet içeriğinde geçen aktif anahtar kelimelere göre dinamik kategori belirler."""
    text_lower = text.lower()
    for kw in active_keywords:
        word = kw["word"].lower()
        if word in text_lower:
            return kw["category"]
    return "genel"

def process_excel(excel_path, output_excel_path):
    logger.info("=== Excel Tweet Analiz ve Entegrasyon Betiği Başlatılıyor ===")
    
    # 1. Veritabanını ve Model'i başlat
    logger.info("Veritabanı kontrol ediliyor...")
    init_db()
    
    logger.info("İnce ayarlı XML-RoBERTa modeli yükleniyor...")
    analyzer = SentimentAnalyzer()
    
    # 2. Excel dosyasını pandas ile yükle
    if not os.path.exists(excel_path):
        logger.error(f"Excel dosyası bulunamadı: {excel_path}")
        return
        
    logger.info(f"Excel dosyası yükleniyor: {excel_path}")
    df = pd.read_excel(excel_path)
    logger.info(f"Toplam {len(df)} adet tweet satırı okundu.")
    
    # 3. Kategori kelimelerini veritabanından çek
    active_keywords = get_active_keywords()
    logger.info(f"Kategori belirleme için {len(active_keywords)} aktif anahtar kelime yüklendi.")
    
    # 4. Semantik kopya denetimi için geçmiş tweet metinlerini çek
    seen_texts = []
    db_texts = get_recent_tweet_texts(days=7)
    for t_text in db_texts:
        cleaned_db = clean_tweet_text(t_text)
        if len(cleaned_db) >= 15:
            seen_texts.append(cleaned_db)
    logger.info(f"Geçmiş veritabanından {len(seen_texts)} referans metin semantik kopya kontrolü (%75 eşik) için hafızaya alındı.")
    
    # 5. Tweetleri işle
    processed_for_db = []
    all_results_for_excel = []
    
    stats = {
        "total": len(df),
        "passed": 0,
        "too_short": 0,
        "profanity": 0,
        "duplicate": 0,
        "pozitif": 0,
        "negatif": 0,
        "notr": 0
    }
    
    for i, row in df.iterrows():
        if i % 30 == 0 or i == len(df) - 1:
            logger.info(f"Analiz ediliyor: {i + 1}/{len(df)} tamamlandı...")
            
        raw_text = str(row.get('text', ''))
        cleaned_text = clean_tweet_text(raw_text)
        
        # Filtre durumunu belirleme
        filter_status = "Passed"
        
        # A. Uzunluk kontrolü
        if len(cleaned_text) < 15:
            filter_status = "Filtered: Too Short"
            stats["too_short"] += 1
            
        # B. Küfür/kaba kelime kontrolü
        elif contains_profanity(raw_text):
            filter_status = "Filtered: Profanity"
            stats["profanity"] += 1
            
        # C. Semantik kopya / duplicate kontrolü
        else:
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
                filter_status = "Filtered: Duplicate"
                stats["duplicate"] += 1
            else:
                # Kopya değilse hem hafızaya ekle hem de DB kaydına ekle
                seen_texts.append(cleaned_text)
                stats["passed"] += 1
                
        # D. Kategori sınıflandırması
        category = classify_category(raw_text, active_keywords)
        
        # E. Model ile Sentiment Analizi
        nlp_result = analyzer.analyze(raw_text)
        sentiment = nlp_result['sentiment']
        score = nlp_result['score']
        is_ironic = nlp_result['is_ironic']
        
        # Duygu istatistikleri
        stats[sentiment] += 1
        
        # Veri yapılarını oluştur
        tweet_id = str(row.get('id'))
        author_id = row.get('author_id')
        author_username = f"user_{author_id}" if pd.notna(author_id) else "unknown"
        created_at_val = row.get('created_at')
        created_at_str = str(created_at_val) if pd.notna(created_at_val) else ""
        
        like_count = int(row.get('like_count', 0)) if pd.notna(row.get('like_count')) else 0
        retweet_count = int(row.get('retweet_count', 0)) if pd.notna(row.get('retweet_count')) else 0
        
        # SQLite DB'ye gönderilecek veri (sadece Passed olanlar)
        if filter_status == "Passed":
            processed_for_db.append({
                "tweet_id": tweet_id,
                "text": raw_text,
                "author_username": author_username,
                "created_at": created_at_str,
                "sentiment": sentiment,
                "score": score,
                "is_ironic": is_ironic,
                "likes": like_count,
                "retweets": retweet_count,
                "views": 0,
                "category": category
            })
            
        # Excel raporuna yazılacak geniş veri (tüm tweetler)
        row_dict = row.to_dict()
        row_dict.update({
            "cleaned_text": cleaned_text,
            "category": category,
            "sentiment": sentiment,
            "score": score,
            "is_ironic": "Evet" if is_ironic else "Hayır",
            "filter_status": filter_status
        })
        all_results_for_excel.append(row_dict)
        
    # 6. Veritabanına bulk kayıt yap (Passed olanları)
    if processed_for_db:
        logger.info(f"Filtreleri geçen {len(processed_for_db)} adet tweet SQLite veritabanına bulk olarak kaydediliyor...")
        save_tweets_bulk(processed_for_db)
        logger.info("Veritabanı kaydı başarıyla tamamlandı.")
    else:
        logger.warning("Filtreleri geçen tweet bulunamadığı için veritabanına kayıt yapılmadı.")
        
    # 7. Tüm sonuçları Excel olarak kaydet
    df_output = pd.DataFrame(all_results_for_excel)
    logger.info(f"Analiz sonuçları Excel'e yazılıyor: {output_excel_path}")
    
    # Biçimlendirilmiş bir Excel dosyası oluşturmak için openpyxl kullanıyoruz
    try:
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            df_output.to_excel(writer, index=False, sheet_name='Analiz Sonuclari')
            worksheet = writer.sheets['Analiz Sonuclari']
            
            # Sütun genişliklerini ayarla
            worksheet.column_dimensions['A'].width = 25  # id
            worksheet.column_dimensions['H'].width = 80  # text
            worksheet.column_dimensions['I'].width = 80  # text_clean (ya da cleaned_text)
            
            from openpyxl.styles import Alignment
            for cell in worksheet['H']:
                cell.alignment = Alignment(wrap_text=True)
            for cell in worksheet['I']:
                cell.alignment = Alignment(wrap_text=True)
                
        logger.info("Excel sonuç raporu başarıyla kaydedildi.")
    except Exception as e:
        logger.error(f"Excel raporu yazılırken hata: {e}")
        # Hata durumunda standart to_excel fallback
        df_output.to_excel(output_excel_path, index=False)
        logger.info("Excel fallback kaydı tamamlandı.")
        
    # 8. Rapor istatistiklerini konsola yazdır
    logger.info("\n" + "="*50)
    logger.info("               ANALİZ RAPORU VE İSTATİSTİKLER")
    logger.info("="*50)
    logger.info(f"Toplam İşlenen Tweet: {stats['total']}")
    logger.info(f"Filtreleri Geçen (DB'ye Kaydedilen): {stats['passed']}")
    logger.info(f"Elenen Tweet (Kısa Metin): {stats['too_short']}")
    logger.info(f"Elenen Tweet (Küfür/Kaba Metin): {stats['profanity']}")
    logger.info(f"Elenen Tweet (Semantik Kopya/Bot): {stats['duplicate']}")
    logger.info("-"*50)
    logger.info("Duygu Durum Dağılımı (Tüm Veriler İçin):")
    logger.info(f"  🟢 Pozitif: {stats['pozitif']} ({round(stats['pozitif']/stats['total']*100, 1)}%)")
    logger.info(f"  🔴 Negatif: {stats['negatif']} ({round(stats['negatif']/stats['total']*100, 1)}%)")
    logger.info(f"  🟡 Nötr   : {stats['notr']} ({round(stats['notr']/stats['total']*100, 1)}%)")
    logger.info("="*50)

if __name__ == "__main__":
    excel_file = "pilot_v5_tweets 1copybudikkat.xlsx"
    output_file = "pilot_v5_tweets_analiz_sonuclari.xlsx"
    
    process_excel(excel_file, output_file)
