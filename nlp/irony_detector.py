import re

# İroni ve kinaye belirten Türkçe kelime öbekleri
IRONY_KEYWORDS = [
    "harika", "mükemmel", "süper", "muazzam", "şahane", "uçuyoruz", "şahlanıyoruz", 
    "kıskanıyor", "büyüyoruz", "asgari ücretli her gün antrikot yiyor", "tabi canım", 
    "aynen", "yersen", "kesin yaşanmıştır bu", "büyük oyun", "dış güçler", 
    "avrupa bizi kıskanıyor", "almanya bitmiş", "ekonomi çok iyi", "ekonomi çok güzel",
    "her şey çok güzel", "her şey çok iyi", "durumlar çok iyi", "durumlar çok güzel",
    "telefonunu çıkar", "şükredin", "porsiyonları küçültün", "aa ne güzel", "maşallah",
    "nazar değmesin", "vay be", "keşke", "yersen", "ironidir", "ironi", "sarkasm", "sarkastik"
]

# Performans için regex patternini bir kere derliyoruz
IRONY_PATTERN = re.compile(r'\b(' + '|'.join(map(re.escape, IRONY_KEYWORDS)) + r')\b')

def detect_irony(text):
    """
    Metinde ironi/kinaye olup olmadığını kural tabanlı olarak analiz eder.
    """
    text_lower = text.lower()
    
    # Explicit ironi işaretleri
    if any(marker in text_lower for marker in ["(ironi)", "/s", "(!)", "(?)"]):
        return True
    
    # Gülen yüz / göz kırpma / sarkastik gülücükler (örn: :), :)), ;), ;)) )
    has_smiley = bool(re.search(r'[:;=]-?[\)\(dDpP]|[\)\(]{2,}', text_lower))
    
    # Anahtar kelime var mı? (Derlenmiş regex kullanıyoruz)
    has_irony_pattern = bool(IRONY_PATTERN.search(text_lower))
    
    # Noktalama (tek bir ünlem veya aşırı soru işareti) var mı?
    has_punctuation = text.count("!") >= 1 or text.count("?") > 1
    
    # Sarcastic bağlaçlar veya destekleyiciler
    sarcastic_boosters = ["aynen", "yersen", "ya", "tabi", "tabii", "canım", "şükür", "maşallah"]
    has_booster = any(b in text_lower for b in sarcastic_boosters)
    
    # Eğer ironik kelimelerden biri geçiyorsa ve yanına gülücük, ünlem veya sarkastik bağlaç gelmişse ironidir!
    if has_irony_pattern and (has_smiley or has_punctuation or has_booster):
        return True
        
    return False

def flip_sentiment(sentiment_label):
    """
    İroni tespit edildiğinde duygu etiketini tersine çevirir.
    """
    if sentiment_label == "pozitif":
        return "negatif"
    elif sentiment_label == "negatif":
        return "pozitif"
    return sentiment_label
