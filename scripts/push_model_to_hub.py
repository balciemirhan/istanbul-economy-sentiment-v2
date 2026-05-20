import os
import sys
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Reconfigure stdout/stderr to UTF-8 to prevent Windows encoding crashes
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    print("\n" + "="*65)
    print("🚀  İSTANBUL METRE - HUGGING FACE HUB MODEL YÜKLEME ARACI  🚀")
    print("="*65)
    
    local_dir = "./fine_tuned_bert"
    if not os.path.exists(local_dir):
        print(f"❌ Hata: Yerel model klasörü bulunamadı: {local_dir}")
        print("Lütfen öncelikle modelinizi eğittiğinizden veya bu klasörün mevcut olduğundan emin olun.")
        return

    # Hugging Face Token Kontrolü
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("\n💡 Hugging Face Hub'a yükleme yapabilmek için 'Write' (Yazma) yetkili bir Access Token gereklidir.")
        print("Eğer tokenınız yoksa şu adresten hemen ücretsiz oluşturabilirsiniz: https://huggingface.co/settings/tokens")
        hf_token = input("👉 Hugging Face Access Token'ınızı girin: ").strip()
        if not hf_token:
            print("❌ Hata: Token girilmediği için işlem iptal edildi.")
            return

    print("\n" + "-"*65)
    username = input("👉 Hugging Face kullanıcı adınız (Örn: 'balciemirhan'): ").strip()
    if not username:
        print("❌ Hata: Kullanıcı adı girilmediği için işlem iptal edildi.")
        return

    repo_name = input("👉 Model depo adı (Örn: 'bert-base-turkish-128k-istanbul-sentiment'): ").strip()
    if not repo_name:
        print("❌ Hata: Depo adı girilmediği için işlem iptal edildi.")
        return

    repo_id = f"{username}/{repo_name}"
    
    print("\n" + "-"*65)
    print(f"📦 Yerel model yükleniyor: '{local_dir}'...")
    try:
        # Load from local
        tokenizer = AutoTokenizer.from_pretrained(local_dir)
        model = AutoModelForSequenceClassification.from_pretrained(local_dir)
        
        print(f"☁️  Model Hugging Face Hub'a yükleniyor (https://huggingface.co/{repo_id})...")
        print("⚡ Bu işlem dosya boyutu (~737 MB) nedeniyle internet hızınıza bağlı olarak birkaç dakika sürebilir.")
        print("⏳ Lütfen bekleyin, yükleme tamamlandığında bildireceğiz...\n")
        
        # Push tokenizer and model to hub
        tokenizer.push_to_hub(repo_id, token=hf_token)
        model.push_to_hub(repo_id, token=hf_token)
        
        print("\n" + "═"*65)
        print("🎉  TEBRİKLER! MODELİNİZ BAŞARIYLA HUGGING FACE HUB'A YÜKLENDİ!  🎉")
        print(f"🔗  Model Sayfanız: https://huggingface.co/{repo_id}")
        print("═"*65)
        print(f"\n💡  Şimdi projenizi indirenlerin doğrudan sizin modelinizi internetten çekmesi için:")
        print(f"    1. 'config.py' dosyasını açın.")
        print(f"    2. 'savasy/bert-base-turkish-sentiment-cased' olan fallback model adını '{repo_id}' olarak güncelleyin.")
        print(f"    3. README.md dosyasındaki model indirme linklerini kendi linkinizle değiştirin.")
        print("    Artık projeyi klonlayan herkes sıfır kurulumla direkt sizin özel eğitilmiş zekanızı kullanabilecek!\n")
        
    except Exception as e:
        print(f"\n❌ Bir hata oluştu: {e}")

if __name__ == "__main__":
    main()
