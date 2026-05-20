import logging
import torch
from transformers import pipeline
from nlp.text_cleaner import clean_tweet_text
from nlp.irony_detector import detect_irony, flip_sentiment
from config import SENTIMENT_MODEL

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        logger.info(f"Model yükleniyor: {SENTIMENT_MODEL} (Bu işlem ilk seferde vakit alabilir)...")
        try:
            device = 0 if torch.cuda.is_available() else -1
            self.analyzer = pipeline("sentiment-analysis", model=SENTIMENT_MODEL, device=device)
            
            # Check if the loaded model is natively a 3-class model
            self.is_three_class = False
            if self.analyzer and hasattr(self.analyzer, "model") and hasattr(self.analyzer.model, "config"):
                self.is_three_class = getattr(self.analyzer.model.config, "num_labels", 2) == 3
                
            logger.info(f"Duygu analizi modeli başarıyla yüklendi (Cihaz: {'GPU' if device == 0 else 'CPU'}, 3-Sınıf: {self.is_three_class}).")
        except Exception as e:
            logger.error(f"Model yüklenirken hata oluştu: {e}")
            self.analyzer = None

    def map_label(self, label):
        """HuggingFace modelinden dönen etiketi standartlaştırır (LABEL_0=negatif, LABEL_1=notr, LABEL_2=pozitif)."""
        label = label.lower()
        if label in ["label_0", "negative"]:
            return "negatif"
        elif label in ["label_1", "neutral", "notr"]:
            return "notr"
        elif label in ["label_2", "positive"]:
            return "pozitif"
        else:
            return "notr"

    def analyze(self, raw_text):
        """Metni alır, temizler ve duygu analizinden geçirir."""
        if not self.analyzer:
            return {"sentiment": "notr", "score": 0.0, "is_ironic": False}
            
        # 1. Metni temizle
        clean_text = clean_tweet_text(raw_text)
        
        # Eğer temizlenmiş metin boşsa, nötr dön
        if not clean_text:
             return {"sentiment": "notr", "score": 0.0, "is_ironic": False}
        
        # 2. Model Analizi
        try:
            result = self.analyzer(clean_text, truncation=True, max_length=512)[0]
            base_sentiment = self.map_label(result['label'])
            score = result['score']
        except Exception as e:
            logger.error(f"Analiz sırasında hata: {e}")
            return {"sentiment": "notr", "score": 0.0, "is_ironic": False}
            
        # 0.85 Nötr Kapısı (savasy model is 2-class, so low confidence must be neutral)
        if not getattr(self, "is_three_class", False) and score < 0.85:
            base_sentiment = "notr"
            
        # 3. İroni Kontrolü
        is_ironic = detect_irony(raw_text)
        
        # 4. İroni varsa duygu etiketini tersine çevir
        final_sentiment = flip_sentiment(base_sentiment) if is_ironic else base_sentiment
        
        # 5. Kural Tabanlı Duygu Ezmesi (Override)
        pure_negative_keywords = [
            "protesto", "eylem", "yürüyoruz", "yoksulluk", "açlık", "geçinemiyoruz", "pahalılık", "istifa", 
            "isyan", "arızası", "rötar", "kaza yaptı", "kilitlendi", "çilesi", "pahalı", "belanızı", "belası", 
            "iş değil", "yerlerde", "rezalet", "soygun", "hırsızlık", "çıldırdım", "çıldırırsın"
        ]
        raw_lower = raw_text.lower()
        
        if final_sentiment in ["pozitif", "notr"]:
            # Eğer saf isyan/arıza kelimelerinden biri geçiyorsa direkt negatif yap
            if any(kw in raw_lower for kw in pure_negative_keywords):
                final_sentiment = "negatif"
                
            # İSTANBUL TRAFİK OVERRIDE (Özel Kural)
            # Eğer içinde 'trafik' veya 'trafiğ' kelimesi geçiyorsa ve cümlede 'yok', 'açık', 'rahat' gibi rahatlama belirtisi yoksa, o tweet kesinlikle şikayettir!
            # Suffix mutation: trafik -> trafiği (bu yüzden "trafiğ" de kontrol edilir)
            elif any(t in raw_lower for t in ["trafik", "trafiğ"]):
                if not any(good_word in raw_lower for good_word in ["yok", "açık", "rahat", "boş", "akıyor"]):
                    final_sentiment = "negatif"
                    
            # Sadece liste veya nötr kavramlar geçiyorsa pozitifi nötre çek
            elif any(kw in raw_lower for kw in ["tanker", "konteynır", "fıçısı"]) and "kanal istanbul" in raw_lower:
                final_sentiment = "notr"
                
        return {
            "sentiment": final_sentiment,
            "score": round(score, 4),
            "is_ironic": is_ironic
        }

