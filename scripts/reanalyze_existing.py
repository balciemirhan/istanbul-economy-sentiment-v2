import sys
import os

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Root dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import SessionLocal, Tweet
from nlp.sentiment_analyzer import SentimentAnalyzer

def reanalyze_all():
    print("=== Mevcut Tweetlerin Yeni Model ile Yeniden Analizi Başlıyor ===")
    
    db = SessionLocal()
    try:
        # Veritabanındaki tüm tweetleri çek
        tweets = db.query(Tweet).all()
        total = len(tweets)
        print(f"Veritabanında toplam {total} adet tweet bulundu.")
        
        if total == 0:
            print("Analiz edilecek tweet bulunamadı.")
            return
            
        # Yeni SentimentAnalyzer sınıfını yükle
        print("Yeni SentimentAnalyzer yükleniyor (GPU/CPU kontrolü yapılıyor)...")
        analyzer = SentimentAnalyzer()
        
        print("Analiz ediliyor...")
        updated_count = 0
        for i, tweet in enumerate(tweets, start=1):
            if i % 20 == 0 or i == total:
                print(f"İlerleme: {i}/{total} tamamlandı...")
                
            # Duygu analizi yap
            nlp_result = analyzer.analyze(tweet.text)
            
            # Eski duygu değerlerini yenileri ile güncelle
            tweet.sentiment = nlp_result['sentiment']
            tweet.score = nlp_result['score']
            tweet.is_ironic = nlp_result['is_ironic']
            
            updated_count += 1
            
        db.commit()
        print(f"\nBaşarılı! {updated_count} adet tweet yeni model ile başarıyla yeniden analiz edildi ve güncellendi.")
        
    except Exception as e:
        db.rollback()
        print(f"Hata oluştu: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reanalyze_all()
