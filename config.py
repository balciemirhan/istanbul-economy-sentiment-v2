import os
from dotenv import load_dotenv

load_dotenv()

# X API Credentials
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")

# Database
DB_NAME = os.getenv("DB_NAME", "istanbul_ekonomi")

# NLP Model
SENTIMENT_MODEL = "./fine_tuned_bert" if os.path.exists("./fine_tuned_bert") else "Emirhan41/bert-base-turkish-128k-istanbul-sentiment"

if not X_BEARER_TOKEN:
    import warnings
    warnings.warn("🚨 KRİTİK UYARI: X_BEARER_TOKEN .env dosyasından okunamadı! API istekleri başarısız olacaktır.")
