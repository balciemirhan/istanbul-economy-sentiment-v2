import re

def clean_tweet_text(text):
    """
    BERT modeline girmeden önce metni gürültüden arındırır.
    """
    if not text:
        return ""
        
    # URL'leri kaldır (https, http, pic.twitter.com, t.co vb. her türlü varyasyon)
    text = re.sub(r'http[s]?://\S+|pic\.twitter\.com/\S+|t\.co/\S+', '', text)
    
    # Kullanıcı etiketlerini (@mention) kaldır
    text = re.sub(r'@\w+', '', text)
    
    # Hashtag'leri (#) kaldır (Türkçe karakterler dahil tüm etiketi ve kelimeyi siler ki gürültü/manipülasyon yapmasın)
    text = re.sub(r'#[\wçÇğĞıİöÖşŞüÜ]+', '', text)
    
    # Sadece harfler, rakamlar, temel noktalama işaretleri ve Türkçe karakterler kalsın (Emojileri uçarır)
    text = re.sub(r'[^\w\s\.,!\?\-\(\)\'":;çÇğĞıİöÖşŞüÜ]', '', text)
    
    # RT önekini kaldır
    text = re.sub(r'^RT[\s]+', '', text)
    
    # Harf uzatmalarını normalleştir (örn: yaaaaaaaaaaaaaa -> ya, bıktıkkkkkkkkk -> bıktık)
    text = re.sub(r'([a-zA-ZçÇğĞıİöÖşŞüÜ])\1{2,}', r'\1', text)
    
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def contains_profanity(text):
    """
    Tweetin içinde kaba, argo veya küfür içerikli kelimeler olup olmadığını kontrol eder.
    Büyük/küçük harf duyarsızdır.
    """
    if not text:
        return False
        
    text_lower = text.lower()
    
    # Twitter Türkiye'de en çok kullanılan kaba ve küfürlü kelimeler
    # \b kelime sınırlarını belirler ki 'sıkıntı' kelimesindeki 'sık' kısmı yanlışlıkla küfür algılanmasın.
    profanity_patterns = [
        r'\bamk\w*', r'\bamq\w*', r'\baq\w*', r'\bmk\w*', r'\bo\.ç\w*', r'\boç\w*',
        r'\bsik(?!inti|let)\w*', r's\*k\w*', r's\.k\w*', 
        r'\borospu\w*', r'\bpiç\w*', r'\bpıc\w*', r'\bgavat\w*', r'\bibne\w*', r'\byavşak\w*', r'\byavsak\w*',
        r'\bgöt\w*', r'\bamcık\w*', r'\bamcik\w*', r'\bşerefsiz\w*', r'\bserefsiz\w*', 
        r'\bpezevenk\w*', r'\bkahpe\w*', r'\bfahişe\w*'
    ]
    
    for pattern in profanity_patterns:
        if re.search(pattern, text_lower):
            return True
            
    return False
