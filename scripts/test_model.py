import sys
import os
import torch
from transformers import pipeline

# Configure UTF-8
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Root dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SENTIMENT_MODEL

print(f"Model yükleniyor: {SENTIMENT_MODEL}")
device = 0 if torch.cuda.is_available() else -1
analyzer = pipeline("sentiment-analysis", model=SENTIMENT_MODEL, device=device)

test_texts = [
    "İstanbul trafiği artık dayanılmaz bir hal aldı. #trafik #istanbul",
    "Ulaşım ücretleri çok ucuz, her şey harika!",
    "İstanbul Ticaret Odası yeni toplantısını düzenledi.",
    "Borsa İstanbul güne düşüşle başladı, çok kötü bir gün.",
    "Yeni SaaS ürünümüzle İstanbul'daki esnafın stok yönetimini uçurduk, harika."
]

print("\n--- Model Test Sonuçları ---")
for text in test_texts:
    res = analyzer(text, truncation=True, max_length=512)[0]
    print(f"Metin: {text}")
    print(f"  Raw Label: {res['label']} | Raw Score: {res['score']}")
    print("-" * 50)
