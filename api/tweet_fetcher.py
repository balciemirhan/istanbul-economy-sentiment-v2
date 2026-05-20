import os
import json
import time
import logging
import re
from datetime import datetime, timedelta
from typing import List
from config import X_BEARER_TOKEN
from api.x_api_client import XAPIClient
from database.db_manager import get_active_keywords

logger = logging.getLogger(__name__)

class Config:
    MONTHLY_TWEET_BUDGET = 10000   # Aylık maksimum çekilecek tweet sınırı
    REQUEST_DELAY = 1.0            # İstekler arası bekleme (saniye)

    # Filtreleme Ayarları
    MIN_FAVES = 0                  # En az 0 beğeni (Tümünü al)
    MIN_TWEET_LENGTH = 20          # Minimum karakter sayısı
    MIN_WORD_COUNT = 5             # Minimum kelime sayısı

    DATA_DIR = "data"
    USAGE_FILE = os.path.join(DATA_DIR, "local_usage_history.json")

config = Config()


class TweetFilter:
    """Metinsel ve etkileşim kalitesi açısından tweetleri doğrular."""

    @staticmethod
    def is_valid_tweet(tweet: dict) -> bool:
        # Etkileşim kontrolü (API'deki min_faves yerine burada yapıyoruz)
        public_metrics = tweet.get("public_metrics", {})
        like_count = public_metrics.get("like_count", 0)
        if like_count < config.MIN_FAVES:
            return False

        text = tweet.get("text", "")
        if not text or len(text) < config.MIN_TWEET_LENGTH:
            return False
        
        words = text.split()
        if len(words) < config.MIN_WORD_COUNT:
            return False

        if TweetFilter._is_only_emojis_or_symbols(text):
            return False

        return True

    @staticmethod
    def _is_only_emojis_or_symbols(text: str) -> bool:
        alphanumeric_only = re.sub(r'[^\w\s]', '', text).replace(" ", "")
        return len(alphanumeric_only) < 5


class LocalUsageMonitor:
    """Kotayı yerel bir JSON dosyası üzerinden takip eden sınıf."""
    def __init__(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)

    def _load_history(self) -> dict:
        if os.path.exists(config.USAGE_FILE):
            with open(config.USAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_current_month_usage(self) -> int:
        history = self._load_history()
        current_month = datetime.now().strftime('%Y-%m')
        return history.get(current_month, 0)

    def add_usage(self, count: int):
        history = self._load_history()
        current_month = datetime.now().strftime('%Y-%m')
        
        if current_month in history:
            history[current_month] += count
        else:
            history[current_month] = count

        with open(config.USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)

    def check_budget_limit(self) -> bool:
        current_usage = self.get_current_month_usage()
        logger.info(f"Bu ay yerel kayıtlara göre harcanan toplam tweet (RAW): {current_usage:,}")

        if current_usage >= config.MONTHLY_TWEET_BUDGET:
            logger.error(f"🚨 DİKKAT: Aylık {config.MONTHLY_TWEET_BUDGET} tweet limiti aşıldı! Harcanan: {current_usage}")
            return False
            
        return True


class TweetFetcher:
    """main.py'ın çağıracağı temel sınıf."""
    def __init__(self):
        if not X_BEARER_TOKEN:
            logger.error("X_BEARER_TOKEN config dosyasından okunamadı. .env dosyanızı kontrol edin.")
            self.api = None
        else:
            self.api = XAPIClient(X_BEARER_TOKEN)
            
        self.filter = TweetFilter()
        self.monitor = LocalUsageMonitor()

    def build_istanbul_query(self, category_keywords: List[str] = None) -> str:
        # X API büyük/küçük harfe duyarsızdır, sadece 'istanbul' yazmak yeterlidir.
        istanbul_terms = ["istanbul", "i̇stanbul"]
        
        # Eğer kategori kelimeleri verilmemişse varsayılan bir kelime ekle
        if not category_keywords:
            category_keywords = ["ekonomi"]

        istanbul_part = "(" + " OR ".join(istanbul_terms) + ")"
        topic_part = "(" + " OR ".join(category_keywords) + ")"

        # API limitlerine takılmamak için min_faves çıkarıldı, sadece sunucu taraflı çöp filtreleri bırakıldı.
        # Not: Halkın siyasiler/kurumlara yazdığı şikayetleri (reply) ve kanıtlı (link/foto) tweetleri 
        # kaçırmamak için -is:reply ve -has:links engelleri kaldırıldı.
        filters = [
            "lang:tr",
            "-is:retweet",
            "-is:nullcast"
        ]

        return f"{istanbul_part} {topic_part} " + " ".join(filters)

    def fetch_tweets(self, max_tweets: int = 100, days: int = 7) -> List[dict]:
        """
        API üzerinden belirlenen gün sayısına ve kategorilere göre tweet çekerek
        gerçek bir dağılım (trend) oluşturur. Kotayı kategorilere ve günlere böler.
        """
        if not self.api:
            return []

        if not self.monitor.check_budget_limit():
            logger.error("Bütçe sınırı nedeniyle veri çekimi başlatılamıyor.")
            return []

        active_keywords_data = get_active_keywords()
        
        # Kategorilere ayır
        categories = {}
        for kw in active_keywords_data:
            cat = kw.get("category", "genel")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(kw["word"])
            
        if not categories:
            categories = {"genel": ["ekonomi"]}
            
        num_categories = len(categories)
        base_tweets_per_cat = max_tweets // num_categories
        remainder_cat = max_tweets % num_categories

        all_tweets = []
        fetched_in_this_run = 0
        
        if days < 1: days = 1
        if days > 7: days = 7 # X API Basic Sınırı

        for i, (cat_name, cat_keywords) in enumerate(categories.items()):
            tweets_for_this_cat = base_tweets_per_cat
            # Kalanı (remainder) son kategoriye ekle
            if i == num_categories - 1:
                tweets_for_this_cat += remainder_cat
                
            if tweets_for_this_cat <= 0:
                continue

            query = self.build_istanbul_query(cat_keywords)
            logger.info(f"[{cat_name}] kategorisi için {days} günlük X API araması başlıyor: {query}")
            
            # KOTA İSRAFI ÖNLEYİCİ ALGORİTMA:
            # Eğer günlere böldüğümüzde günlük hedef tweet 10'un altında kalıyorsa (API minimum limiti),
            # gün gün bölüp her gün için zorla 10 tweet çekerek (israf yaparak) faturayı şişirmek yerine,
            # tüm günleri tek bir zaman aralığında birleştirerek (tek request ile) noktası noktasına kota harcarız.
            date_ranges = []
            now_utc = datetime.utcnow() - timedelta(seconds=15)
            
            if (tweets_for_this_cat // days) < 10 and days > 1:
                logger.info(f"[{cat_name}] Hedef kota dar olduğu için günlere bölünmeden tek potada çekilecek (İsraf Önleyici Aktif).")
                start_date = now_utc - timedelta(days=days)
                date_ranges.append({
                    "start": start_date,
                    "end": now_utc,
                    "target": max(10, tweets_for_this_cat) # En az 10 olmak zorunda
                })
            else:
                base_tweets_per_day = tweets_for_this_cat // days
                remainder_day = tweets_for_this_cat % days
                for day_offset in range(days, 0, -1):
                    target = base_tweets_per_day
                    if day_offset == 1:
                        target += remainder_day
                    
                    s_date = now_utc - timedelta(days=day_offset)
                    e_date = now_utc - timedelta(days=day_offset - 1)
                    date_ranges.append({
                        "start": s_date,
                        "end": e_date,
                        "target": max(10, target)
                    })

            for dr in date_ranges:
                tweets_per_day = dr["target"]
                
                # Milisaniyeleri atarak temiz bir ISO formatı elde ediyoruz
                start_time = dr["start"].replace(microsecond=0).isoformat() + "Z"
                end_time = dr["end"].replace(microsecond=0).isoformat() + "Z"
                
                logger.info(f"[{cat_name}] {dr['start'].strftime('%Y-%m-%d')} tarihi için {tweets_per_day} tweet çekiliyor...")

                try:
                    tweets_fetched_for_day = 0
                    next_token = None
                    
                    while tweets_fetched_for_day < tweets_per_day:
                        current_max_results = min(100, tweets_per_day - tweets_fetched_for_day)
                        if current_max_results < 10:
                            current_max_results = 10

                        response = self.api.get_recent_tweets(
                            query=query,
                            start_time=start_time,
                            end_time=end_time,
                            max_results=current_max_results,
                            next_token=next_token
                        )

                        tweets = response.get("data", [])
                        if not tweets:
                            break
                            
                        raw_tweet_count = len(tweets)
                        if raw_tweet_count > 0:
                            self.monitor.add_usage(raw_tweet_count)
                            fetched_in_this_run += raw_tweet_count
                            tweets_fetched_for_day += raw_tweet_count

                        includes = response.get("includes", {})
                        users = includes.get("users", [])

                        for item in tweets:
                            author_id = item.get("author_id")
                            user = next((u for u in users if u.get("id") == author_id), {})

                            # TweetFilter'ın bekleği format
                            tweet_data = {
                                **item,
                                "author": user
                            }

                            if self.filter.is_valid_tweet(tweet_data):
                                # Gelen tweet'i sistemin geri kalanının beklediği formata çeviriyoruz (Apify formatına benzetiyoruz)
                                formatted_tweet = self._parse_item(item, user, cat_name)
                                all_tweets.append(formatted_tweet)
                                
                        meta = response.get("meta", {})
                        next_token = meta.get("next_token")
                        
                        if not next_token:
                            break
                            
                        if not self.monitor.check_budget_limit():
                            logger.warning("Çekim esnasında aylık limite ulaşıldı. İşlem durduruluyor.")
                            break
                            
                        time.sleep(config.REQUEST_DELAY)

                    logger.info(f"[{cat_name}] Bu günden {tweets_fetched_for_day} raw tweet çekildi, Kaliteli Toplam (Kümülatif): {len(all_tweets)}")

                    if not self.monitor.check_budget_limit():
                        break
                        
                    time.sleep(config.REQUEST_DELAY)

                except Exception as e:
                    logger.error(f"[{cat_name}] {dr['start'].strftime('%Y-%m-%d')} hatası: {e}")
                    # Hata olsa bile diğer günlere geçmesi için break yerine pass/continue yapıyoruz
                    continue

        return all_tweets

    def _parse_item(self, item: dict, user: dict, category: str = 'genel') -> dict:
        """Sistemin geri kalanının (SQLite, NLP) anlayacağı standart formata çevirir."""
        public_metrics = item.get('public_metrics', {})
        username = user.get('username', 'unknown')
        text = item.get('text', '')
        
        return {
            "tweet_id": str(item.get('id')),
            "text": text,
            "author_username": username,
            "likes": public_metrics.get('like_count', 0),
            "retweets": public_metrics.get('retweet_count', 0),
            "views": public_metrics.get('impression_count', 0),
            "created_at": item.get('created_at'),
            "category": category
        }
