from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Tweet(Base):
    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tweet_id = Column(String, unique=True, nullable=False) # X API'den gelen orijinal ID
    text = Column(String, nullable=False)
    author_username = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    category = Column(String, default='genel', index=True)

    
    # NLP Sonuçları
    sentiment = Column(String, index=True) # pozitif, negatif, notr
    score = Column(Float) # 0.0 - 1.0
    is_ironic = Column(Boolean, default=False)
    
    # Etkileşim Metrikleri
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    views = Column(Integer, default=0)
    hashtags = Column(String) # Virgülle ayrılmış etiketler

class Keyword(Base):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False, default='genel') # ekonomi, ulasim, turizm vb.
