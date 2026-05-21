import os
import datetime
import logging
import shutil
import pandas as pd
from openpyxl.styles import Alignment
from sqlalchemy import create_engine, func, text
from dateutil import parser
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from database.models import Base, Tweet, Keyword, FetchJob
from config import DB_NAME

logger = logging.getLogger(__name__)

# SQLite Bağlantısı (Proje kök dizininde DB_NAME ile oluşturulacak)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = f"sqlite:///{os.path.join(BASE_DIR, f'{DB_NAME}.db')}"
engine = create_engine(db_path, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Database session context manager (DRY compliance)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Veritabanı tablolarını oluşturur."""
    db_file = os.path.join(BASE_DIR, f"{DB_NAME}.db")
    demo_file = os.path.join(BASE_DIR, "istanbul_ekonomi_demo.db")
    
    if not os.path.exists(db_file) and os.path.exists(demo_file):
        try:
            shutil.copy(demo_file, db_file)
            logger.info("Demo veritabanı başarıyla kopyalandı.")
            return
        except Exception as e:
            logger.error(f"Demo veritabanı kopyalama hatası: {e}")

    Base.metadata.create_all(bind=engine)
    
    # Kategori sütunu migration (geçiş)
    with get_db() as db:
        try:
            res = db.execute(text("PRAGMA table_info(tweets);")).fetchall()
            columns = [row[1] for row in res]
            if "category" not in columns:
                db.execute(text("ALTER TABLE tweets ADD COLUMN category VARCHAR DEFAULT 'genel';"))
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Migration hatası: {e}")
        
    seed_keywords_if_empty()



def save_tweets_bulk(tweets_list):
    """Çoklu tweetleri tek bir seferde (bulk) veritabanına kaydeder."""
    with get_db() as db:
        try:
            new_tweet_ids = [str(t['tweet_id']) for t in tweets_list]
            existing_tweets = db.query(Tweet.tweet_id).filter(Tweet.tweet_id.in_(new_tweet_ids)).all()
            existing_ids = {t[0] for t in existing_tweets}
            
            objects_to_save = []
            for tweet_data in tweets_list:
                t_id = str(tweet_data['tweet_id'])
                if t_id not in existing_ids:
                    # String ISO tarihini datetime objesine çeviriyoruz (Eğer varsa)
                    created_dt = datetime.datetime.utcnow()
                    if tweet_data.get('created_at'):
                        try:
                            # Twitter'ın formatı: 2026-05-11T12:00:00.000Z
                            created_dt = parser.isoparse(tweet_data['created_at']).replace(tzinfo=None)
                        except:
                            pass

                    new_tweet = Tweet(
                        tweet_id=t_id,
                        text=tweet_data['text'],
                        author_username=tweet_data.get('author_username', ''),
                        created_at=created_dt,
                        sentiment=tweet_data.get('sentiment', 'notr'),
                        score=tweet_data.get('score', 0.0),
                        is_ironic=tweet_data.get('is_ironic', False),
                        likes=tweet_data.get('likes', 0),
                        retweets=tweet_data.get('retweets', 0),
                        views=tweet_data.get('views', 0),
                        hashtags=tweet_data.get('hashtags', ''),
                        category=tweet_data.get('category', 'genel')
                    )
                    objects_to_save.append(new_tweet)
                    existing_ids.add(t_id) # Aynı listede kopya varsa engellemek için
                    
            if objects_to_save:
                db.bulk_save_objects(objects_to_save)
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Toplu tweet kaydedilirken hata oluştu: {e}")

def get_dashboard_stats():
    """Dashboard'un ihtiyaç duyduğu temel istatistikleri çeker."""
    with get_db() as db:
        total = db.query(Tweet).count()
        positive = db.query(Tweet).filter(Tweet.sentiment == 'pozitif').count()
        negative = db.query(Tweet).filter(Tweet.sentiment == 'negatif').count()
        neutral = db.query(Tweet).filter(Tweet.sentiment == 'notr').count()
        
        avg_score = db.query(func.avg(Tweet.score)).scalar() or 0.0
        
        return {
            "total": total,
            "positive": {"count": positive, "percentage": round((positive/total)*100, 1) if total > 0 else 0},
            "negative": {"count": negative, "percentage": round((negative/total)*100, 1) if total > 0 else 0},
            "neutral": {"count": neutral, "percentage": round((neutral/total)*100, 1) if total > 0 else 0},
            "avg_score": round(avg_score, 2)
        }


_MONTHS_TR = (
    "Oca", "Şub", "Mar", "Nis", "May", "Haz",
    "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara",
)


def _format_tr_short_date(dt):
    return f"{dt.day} {_MONTHS_TR[dt.month - 1]}"


def get_weekly_trend(days=28, weeks=4, sentiment=None, topic=None):
    """
    Son `days` günü `weeks` eşit dilime böler; her dilimde duygu sayılarını döner.
    Tweet.created_at = X yayın tarihi (DB kayıt anı değil).
    """
    now = datetime.datetime.utcnow()
    window_start = now - datetime.timedelta(days=days)
    week_duration = days // weeks

    with get_db() as db:
        result_weeks = []
        for i in range(weeks):
            bucket_start = window_start + datetime.timedelta(days=i * week_duration)
            bucket_end = (
                now
                if i == weeks - 1
                else window_start + datetime.timedelta(days=(i + 1) * week_duration)
            )

            query = db.query(Tweet).filter(
                Tweet.created_at >= bucket_start,
                Tweet.created_at < bucket_end,
            )
            if sentiment and sentiment != "hepsi":
                query = query.filter(Tweet.sentiment == sentiment)
            if topic and topic != "hepsi":
                query = query.filter(Tweet.category == topic)

            positive = query.filter(Tweet.sentiment == "pozitif").count()
            negative = query.filter(Tweet.sentiment == "negatif").count()
            neutral = query.filter(Tweet.sentiment == "notr").count()
            total = positive + negative + neutral

            label_end = bucket_end - datetime.timedelta(days=1)
            if label_end < bucket_start:
                label_end = bucket_start

            result_weeks.append({
                "label": f"{_format_tr_short_date(bucket_start)} – {_format_tr_short_date(label_end)}",
                "start": bucket_start.strftime("%Y-%m-%d"),
                "end": label_end.strftime("%Y-%m-%d"),
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total": total,
            })

        return {"period_days": days, "weeks": result_weeks}


def seed_keywords_if_empty():
    """Tablo boşsa yeni varsayılan kelimeleri ekler. Dinamik eklenenleri silmez."""
    with get_db() as db:
        try:
            count = db.query(Keyword).count()
            if count == 0:
                default_topics = {
                    "makro_ekonomi": ["enflasyon", "asgari ücret", "fatura", "pahalılık", "alım gücü", "zam geldi", "geçim derdi", "kredi kartı", "maaş", "gelir", "gıda fiyatı"],
                    "ulasim_lojistik": ["mazot", "benzin", "akaryakıt zammı", "akbil", "iett zammı", "toplu taşıma ücreti", "taksi zammı", "köprü geçiş ücreti", "metrobüs zammı", "marmaray ücreti", "otobüs bileti"],
                    "gayrimenkul_insaat": ["kira", "ev sahibi", "depozito", "emlak", "konut fiyatları", "aidat", "kiralık daire", "satılık ev", "ev fiyatı", "konut kredisi"],
                    "ticaret_perakende": ["esnaf", "market fiyatları", "pazar arabası", "fahiş fiyat", "etiket fiyatı", "gramaj", "kasiyer", "mağaza fiyatları", "işyeri kirası", "ticaret odası"]
                }
                objects_to_save = []
                for category, words in default_topics.items():
                    for word in words:
                        objects_to_save.append(Keyword(word=word, category=category))
                db.bulk_save_objects(objects_to_save)
                db.commit()
                logger.info("Varsayılan filtreleme kelimeleri veritabanına ilk kez eklendi.")
        except Exception as e:
            db.rollback()
            logger.error(f"Kelimeler güncellenirken hata oluştu: {e}")

def get_active_keywords():
    """Tüm aktif kelimeleri liste olarak döner."""
    with get_db() as db:
        keywords = db.query(Keyword).all()
        return [{"id": k.id, "word": k.word, "category": k.category} for k in keywords]

def add_keyword(word, category="genel"):
    with get_db() as db:
        try:
            existing = db.query(Keyword).filter(Keyword.word == word).first()
            if not existing:
                new_kw = Keyword(word=word, category=category)
                db.add(new_kw)
                db.commit()
                return {"success": True, "id": new_kw.id, "word": new_kw.word, "category": new_kw.category}
            return {"success": False, "error": "Bu kelime zaten var"}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

def delete_keyword(kw_id):
    with get_db() as db:
        try:
            kw = db.query(Keyword).filter(Keyword.id == kw_id).first()
            if kw:
                db.delete(kw)
                db.commit()
                return {"success": True}
            return {"success": False, "error": "Kelime bulunamadı"}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}

def get_recent_tweet_texts(days=7):
    """Son 'days' gün içindeki tweetlerin metinlerini döndürür. Spam/Kopya filtresi için kullanılır."""
    with get_db() as db:
        try:
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            recent_tweets = db.query(Tweet.text).filter(Tweet.created_at >= cutoff_date).all()
            return [t[0] for t in recent_tweets if t[0]]
        except Exception as e:
            logger.error(f"Geçmiş tweet metinleri çekilirken hata: {e}")
            return []

def export_all_tweets_to_excel(output_target):
    """
    Tüm tweetleri veritabanından çeker ve biçimlendirilmiş bir Excel dosyası olarak
    verilen output_target (dosya yolu veya BytesIO nesnesi) üzerine yazar.
    """
    with get_db() as db:
        try:
            all_tweets = db.query(Tweet).all()
            if not all_tweets:
                return False
                
            data = []
            for t in all_tweets:
                data.append({
                    "Tarih": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
                    "Kullanıcı": t.author_username,
                    "Tweet Metni": t.text,
                    "Duygu Durumu": t.sentiment.upper() if t.sentiment else "",
                    "Skor": round(t.score, 2) if t.score else 0,
                    "İroni mi?": "Evet" if t.is_ironic else "Hayır",
                    "Beğeni": t.likes,
                    "RT": t.retweets,
                    "Görüntülenme": t.views
                })
                
            df = pd.DataFrame(data)
            
            with pd.ExcelWriter(output_target, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Tum Tweetler')
                worksheet = writer.sheets['Tum Tweetler']
                
                # Biçimlendirmeler
                worksheet.column_dimensions['A'].width = 18
                worksheet.column_dimensions['B'].width = 18
                worksheet.column_dimensions['C'].width = 80
                worksheet.column_dimensions['D'].width = 15
                worksheet.column_dimensions['E'].width = 10
                worksheet.column_dimensions['F'].width = 12
                worksheet.column_dimensions['G'].width = 10
                worksheet.column_dimensions['H'].width = 10
                worksheet.column_dimensions['I'].width = 15
                
                for cell in worksheet['C']:
                    cell.alignment = Alignment(wrap_text=True)
            return True
        except Exception as e:
            logger.error(f"Excel export hatası: {e}")
            return False


def get_paginated_tweets(page=1, limit=50, sentiment='hepsi', topic='hepsi', keyword=''):
    """Sayfalanmış ve filtrelenmiş tweetleri döner."""
    with get_db() as db:
        query = db.query(Tweet)
        if sentiment != 'hepsi':
            query = query.filter(Tweet.sentiment == sentiment)
            
        if topic != 'hepsi':
            query = query.filter(Tweet.category == topic)
            
        if keyword:
            query = query.filter(Tweet.text.ilike(f"%{keyword}%"))

        total_count = query.count()
        offset = (page - 1) * limit
        
        recent_tweets = query.order_by(Tweet.created_at.desc()).offset(offset).limit(limit).all()
        
        tweets_list = []
        for t in recent_tweets:
            tweets_list.append({
                "id": t.tweet_id,
                "text": t.text,
                "user": f"@{t.author_username}",
                "date": t.created_at.strftime("%d %b") if t.created_at else "",
                "sentiment": t.sentiment,
                "score": t.score,
                "is_ironic": t.is_ironic
            })
            
        has_more = (offset + limit) < total_count
        
        return {
            "tweets": tweets_list,
            "has_more": has_more
        }


def get_tweets_by_filter(sentiment='hepsi', topic='hepsi'):
    """Duygu ve kategoriye göre filtrelenmiş tüm tweet nesnelerini döndürür."""
    with get_db() as db:
        query = db.query(Tweet)
        if sentiment != 'hepsi':
            query = query.filter(Tweet.sentiment == sentiment)
        if topic != 'hepsi':
            query = query.filter(Tweet.category == topic)
            
        tweets = query.all()
        db.expunge_all()
        return tweets


def get_fetch_job_status():
    """Son FetchJob girdisini veritabanından çeker ve logları çözümler."""
    with get_db() as db:
        job = db.query(FetchJob).order_by(FetchJob.id.desc()).first()
        if not job:
            return {
                "is_running": False,
                "message": "Bekleniyor...",
                "logs": []
            }
        logs_list = job.logs.split('\n') if job.logs else []
        logs_list = [l for l in logs_list if l]
        return {
            "is_running": job.is_running,
            "message": job.message,
            "logs": logs_list
        }


def start_fetch_job():
    """Yeni bir fetch iş girdisi oluşturur veya mevcut çalışanı sıfırlar."""
    with get_db() as db:
        active_job = db.query(FetchJob).filter(FetchJob.is_running == True).first()
        if active_job:
            active_job.is_running = True
            active_job.message = "Bekleniyor..."
            active_job.logs = ""
            active_job.updated_at = datetime.datetime.utcnow()
            db.commit()
            return
        
        job = FetchJob(is_running=True, message="Bekleniyor...", logs="", updated_at=datetime.datetime.utcnow())
        db.add(job)
        db.commit()


def update_fetch_job_status(msg, is_running=True):
    """Log satırlarını (maksimum 10) günceller, durumu ve tarihi kaydeder."""
    with get_db() as db:
        job = db.query(FetchJob).order_by(FetchJob.id.desc()).first()
        if not job:
            job = FetchJob(is_running=is_running, message=msg, logs=msg, updated_at=datetime.datetime.utcnow())
            db.add(job)
            db.commit()
            return
        
        job.is_running = is_running
        job.message = msg
        job.updated_at = datetime.datetime.utcnow()
        
        logs_list = job.logs.split('\n') if job.logs else []
        logs_list = [l for l in logs_list if l]
        logs_list.append(msg)
        if len(logs_list) > 10:
            logs_list = logs_list[-10:]
        
        job.logs = '\n'.join(logs_list)
        db.commit()


