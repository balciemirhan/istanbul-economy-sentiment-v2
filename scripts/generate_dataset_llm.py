import os
import sys
import csv
import time
import json
import random
import argparse
import re
from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 to prevent Windows encoding crashes
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Categories and their keywords
CATEGORIES = {
    "makro_ekonomi": [
        "enflasyon", "asgari ücret", "pahalılık", "alım gücü", "zam geldi", 
        "geçim derdi", "kredi kartı", "maaş", "gıda fiyatı", "asgari ücretli", 
        "aylık gelir", "milli gelir", "gelir adaletsizliği", "elektrik faturası", 
        "doğalgaz faturası", "su faturası", "dolar", "ekonomi", "euro", "altın", 
        "borsa", "döviz"
    ],
    "ulasim_lojistik": [
        "mazot", "benzin", "akaryakıt zammı", "akbil", "iett zammı", 
        "toplu taşıma ücreti", "taksi zammı", "köprü geçiş ücreti", 
        "metrobüs zammı", "marmaray ücreti", "otobüs bileti", "istanbul trafiği", "trafik"
    ],
    "gayrimenkul_insaat": [
        "kira", "ev sahibi", "depozito", "emlak", "konut fiyatları", 
        "aidat", "kiralık daire", "satılık ev", "ev fiyatı", "konut kredisi", 
        "ev kirası", "dükkan kirası"
    ],
    "ticaret_perakende": [
        "esnaf", "market fiyatları", "pazar arabası", "fahiş fiyat", 
        "etiket fiyatı", "gramaj", "mağaza fiyatları", "işyeri kirası", 
        "ticaret odası", "istanbul ticaret odası", "ito başkanı", "ito aidat"
    ]
}

def strict_clean_for_duplicate(text):
    """Sadece harf ve rakamlari birakarak kusursuz duplicate kontrolü yapar."""
    text_lower = text.lower()
    # Türkçe karakter dönüştürme (görünmez varyasyonları yakalamak için)
    text_lower = (text_lower.replace("ı", "i")
                            .replace("ğ", "g")
                            .replace("ü", "u")
                            .replace("ş", "s")
                            .replace("ö", "o")
                            .replace("ç", "c"))
    return re.sub(r'[^a-z0-9]', '', text_lower)

def load_existing_dataset(file_path):
    """Loads existing dataset to maintain unique records."""
    records = []
    seen_texts = set()
    if not os.path.exists(file_path):
        return records, seen_texts
        
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            header = next(reader, None) # Başlığı atla
            for row in reader:
                if not row or len(row) < 2:
                    continue
                text = row[0].strip()
                label_str = row[1].strip()
                reason = row[2].strip() if len(row) > 2 else ""
                
                try:
                    label = int(label_str)
                    cleaned = strict_clean_for_duplicate(text)
                    if cleaned not in seen_texts:
                        seen_texts.add(cleaned)
                        records.append({"text": text, "label": label, "reason": reason, "category": ""})
                except ValueError:
                    continue
    except Exception as e:
        print(f"Mevcut veri seti yüklenirken hata oluştu: {e}")
        
    return records, seen_texts

def generate_tweets_with_gemini(api_keys, category, label, count, seed_examples):
    """Calls Gemini API using raw requests with multi-key rotation and robust retry logic."""
    import requests
    import time
    
    # Prompt construction adhering to the strict user guidelines
    prompt = f"""
Sen son derece yetenekli bir Türk veri bilimcisisin. Görevin, bir duygu analizi modeli eğitmek için kullanılacak, son derece gerçekçi, tamamen benzersiz ve doğal Türkçe tweetler simüle etmektir.

HEDEF KATEGORİ: {category.upper()}
HEDEF ETİKET: {label} (0 = Negatif/İsyan/İroni, 1 = Nötr/Haber/Duyuru, 2 = Pozitif/Memnuniyet/Umut)

BU KATEGORİNİN ANAHTAR KELİMELERİ: {", ".join(CATEGORIES[category])}

LÜTFEN ŞU ÇOK KRİTİK KURALLARA GÖRE TAM {count} ADET BENZERSİZ TWEET ÜRET:

1. ETİKET TANIMLARI VE DETAYLARI:
   - 0 (Negatif / İroni / İsyan):
     * Hayat pahalılığı, zamlar, enflasyon, fahiş kiralar, geçim derdi, trafik çilesi, hizmet rötarları veya arızalar üzerine isyan, sitem ve mağduriyet içermelidir.
     * İRONİK (SARKASTİK) GÜLÜCÜKLER: Aslında kötü giden bir durumu (enflasyon, zam, trafik, pahalılık vb.) sahte bir şekilde övüyormuş gibi yapıp sonuna gülücük veya ünlem işareti koyan sarkastik tweetlerdir. (Örn: "Ekonomi çok iyi aynen :)", "Mazota yine zam gelmiş, uçuyoruz şahlanıyoruz maşallah :)", "Nasıl bir şehir oldu burası, denizde bile trafik var ya :)"). Bu tarz ironik gülücüklü tweetleri kesinlikle 0 (Negatif) etiketine dahil etmelisin!
   - 1 (Nötr / Bilgilendirme):
     * Hiçbir duygu barındırmayan, tarafsız haber başlıkları, resmi belediye veya ticaret odası duyuruları, borsa raporları, kamuoyu bilgilendirmeleri veya otomatik sistem paylaşımları olmalıdır. Kesinlikle duygu veya taraflılık içermelidir!
   - 2 (Pozitif / Gerçek Memnuniyet):
     * Samimi bir memnuniyet, yapıcı bir ilerleme, geleceğe dair gerçek bir umut, teşekkür veya beğeni içermelidir. (Örn: akıcı vapur keyfi, dürüst ev sahibi/esnaf övgüsü, kredi/teşvik rahatlaması).
     * GERÇEK MUTLULUKLU GÜLÜCÜKLER: Cümlede gülücük (:), :)), 😊, ;)) geçen ama kesinlikle ironi/sarkazm içermeyen, durumun gerçekten iyi olmasından duyulan samimi sevinci ve memnuniyeti belirten tweetlerdir. (Örn: "Son çeyrekte şirket ciromuz tavan yaptı, her şey çok güzel gidiyor gerçekten :)", "İstanbul'da bu sabah vapur keyfi yapıyorum, hava harika, durumlar çok güzel 😊", "Yeni aldığımız ofis konumu itibariyle işlerimizi inanılmaz kolaylaştırdı, her şey çok güzel :)"). Bunları kesinlikle 2 (Pozitif) etiketine dahil etmelisin!

2. DİL VE SOSYAL MEDYA AĞZI:
   - Cümleler sanki gerçek X (Twitter) kullanıcıları tarafından yazılmış gibi olmalıdır.
   - Yer yer gerçekçi yazım hataları, kısaltmalar (valla, bence, herhalde, tşk), sokak ağzı, samimi sitemler ve popüler klişeler içermelidir.
   - Emojileri yerinde ve çok gerçekçi kullan (😭, 😡, 🤮, 😌, 😊, :), (!)).
   - İSTANBUL KELİMESİ VE ARAMA MANTIĞI: Metinde "istanbul" veya "İstanbul" ifadesi (veya ek almış halleri: istanbul'da, istanbul'un vb.) doğal olarak geçmelidir. Ancak her tweet "İstanbul'da..." diye başlamamalıdır. Bazı tweetlerde cümlenin ortasında veya sonunda geçmeli, bazılarında ise düz kelime yerine sadece "#istanbul", "#İstanbul" veya "#ist" şeklinde hashtag olarak yer almalıdır.
   - Kesinlikle şablon (template) kullanma! Her cümlenin yapısı, uzunluğu ve kelime dizilimi tamamen birbirinden farklı ve benzersiz olmalıdır.

3. ÇIKTI FORMATI:
   Sadece ve sadece geçerli bir JSON liste formatında çıktı ver. Başka hiçbir açıklama yazısı ekleme.
   JSON formatı tam olarak şu yapıda olmalıdır:
   [
     {{"text": "Buraya tweet metni gelecek", "label": {label}, "reason": "Buraya tweetin etiketlenme gerekçesi yazılacak"}}
   ]

4. ANAHTAR KELİME ZORUNLULUĞU:
   Ürettiğin her tweetin içinde, sana yukarıda verilen o kategoriye ait anahtar kelimeler listesinden en az bir veya iki tanesi metnin doğal akışında MUTLAKA geçmelidir!

Referans Alabileceğin Örnek Tweetler:
{json.dumps(seed_examples[:3], ensure_ascii=False, indent=2)}
"""

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 1.0
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    # Sırasıyla denenecek modeller.
    models_to_try = ["gemini-3.5-flash", "gemini-2.5-flash"]
    max_retries = len(api_keys) * 2  # Her model için tüm anahtarları 2 kez dene
    base_delay = 2  # Daha kısa bekleme çünkü farklı anahtara geçiyoruz
    
    for model_name in models_to_try:
        print(f"  -> Model deneniyor: {model_name}")
        
        for attempt in range(max_retries):
            # Dönüşümlü anahtar seçimi
            key_index = attempt % len(api_keys)
            active_key = api_keys[key_index]
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={active_key}"
            print(f"     [Anahtar {key_index+1}/{len(api_keys)}] İstek atılıyor ({model_name})...")
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                if response.status_code == 200:
                    res_data = response.json()
                    text_response = res_data['candidates'][0]['content']['parts'][0]['text']
                    parsed_tweets = json.loads(text_response)
                    return parsed_tweets
                elif response.status_code in [429, 503]:
                    # Diğer anahtara geçmek için hemen bekleyip döngüyü sürdürüyoruz
                    delay = base_delay * (attempt // len(api_keys) + 1)
                    print(f"     [Hata {response.status_code} - Anahtar {key_index+1}] {delay} saniye beklenip diğer anahtara geçilecek...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"     [API Hatası {response.status_code}]: {response.text}")
                    # API hatası ise sonraki modele geçmek için döngüyü kesiyoruz
                    break
            except Exception as e:
                delay = base_delay * (attempt // len(api_keys) + 1)
                print(f"     [Bağlantı Hatası - Anahtar {key_index+1}] {e}. {delay} saniye beklenip diğer anahtara geçilecek...")
                time.sleep(delay)
                
    return []

def main():
    parser = argparse.ArgumentParser(description="LLM ile Dengeli Türkçe Tweet Üretim Aracı")
    parser.add_argument("--limit", type=int, default=5000, help="Hedef toplam tweet sayısı")
    parser.add_argument("--batch_size", type=int, default=20, help="İstek başına üretilecek tweet sayısı")
    parser.add_argument("--output", type=str, default="text,label,reason_5k.txt", help="Çıktı dosya yolu")
    args = parser.parse_args()

    api_key_env = os.getenv("GEMINI_API_KEY")
    if not api_key_env:
        print("🚨 HATA: GEMINI_API_KEY bulunamadı!")
        sys.exit(1)
    
    api_keys = [k.strip() for k in api_key_env.split(",") if k.strip()]
    print(f"Sistemde {len(api_keys)} adet API anahtarı algılandı. Anahtarlar dönüşümlü olarak kullanılacak.")
        
    target_file = args.output
    if os.path.exists(target_file):
        existing_records, seen_texts = load_existing_dataset(target_file)
        print(f"Hedef çıktı dosyası '{target_file}' bulundu. Buradan {len(existing_records)} benzersiz veri hafızaya yüklendi. Kaldığı yerden devam edilecek.")
    else:
        existing_records, seen_texts = load_existing_dataset("text,label,reason.txt")
        print(f"Mevcut 'text,label,reason.txt' dosyasından {len(existing_records)} benzersiz veri hafızaya yüklendi.")
    
    # 📊 DAĞILIM DENGELEYİCİ SAYAÇ SİSTEMİ
    # Her kategori ve etiket kombinasyonunun mevcut sayılarını hesapla
    matrix_counts = {cat: {0: 0, 1: 0, 2: 0} for cat in CATEGORIES.keys()}
    
    # Mevcut verileri anahtar kelimelerine göre kategorilere kabaca ata (Sayaç dengesi için)
    for r in existing_records:
        assigned = False
        for cat, keywords in CATEGORIES.items():
            if any(kw in r['text'].lower() for kw in keywords):
                matrix_counts[cat][r['label']] += 1
                r['category'] = cat
                assigned = True
                break
        if not assigned:
            # Bulamadıysa rastgele birine ekle dengeyi bozmasın
            chosen_cat = random.choice(list(CATEGORIES.keys()))
            matrix_counts[chosen_cat][r['label']] += 1
            r['category'] = chosen_cat

    print(f"\n=== MEVCUT VERİ DAĞILIM MATRİSİ ===")
    for cat, labels in matrix_counts.items():
        print(f"  {cat} -> Negatif(0): {labels[0]} | Nötr(1): {labels[1]} | Pozitif(2): {labels[2]}")

    if len(existing_records) >= args.limit:
        print(f"Hedef limite zaten ulaşılmış veya geçilmiş: {len(existing_records)} / {args.limit}")
        sys.exit(0)

    # Her kombinasyon için hedef sayı (Örn: 5000 / 12 = ~416)
    target_per_combo = args.limit // (len(CATEGORIES) * 3)
    print(f"Kombinasyon başına hedef veri sayısı: ~{target_per_combo}")
    
    new_records = []
    total_needed = args.limit - len(existing_records)
    total_added = 0
    
    while (len(existing_records) + len(new_records)) < args.limit:
        # En az veriye sahip olan (Aç kalmış) kategori ve etiketi seçerek tam terazi kuruyoruz
        incomplete_combos = []
        for cat in CATEGORIES.keys():
            for lbl in [0, 1, 2]:
                current_count = matrix_counts[cat][lbl]
                if current_count < target_per_combo:
                    incomplete_combos.append((cat, lbl, current_count))
                    
        if not incomplete_combos:
            # Eğer tüm kombinasyonlar ana hedefe ulaştıysa kalan küsuratı rastgele tamamla
            cat = random.choice(list(CATEGORIES.keys()))
            lbl = random.choice([0, 1, 2])
        else:
            # En az verisi olan kombinasyonu seç (Denge Şartı!)
            incomplete_combos.sort(key=lambda x: x[2])
            cat, lbl, _ = incomplete_combos[0]

        # Referans örnekler çekiyoruz
        seed_examples = [r for r in existing_records if r['label'] == lbl and r['category'] == cat][:5]
        if not seed_examples:
            # Eğer existing_records'ta bulamadıysa new_records içinden dene
            seed_examples = [r for r in new_records if r['label'] == lbl and r['category'] == cat][:5]
        if not seed_examples:
            # O da yoksa sadece etiket bazlı bul
            seed_examples = [r for r in existing_records if r['label'] == lbl][:5]
            
        print(f"\n[Dengeleyici Döngü] {cat} - Etiket: {lbl} ihtiyacı için istek atılıyor... (Güncel Sayısı: {matrix_counts[cat][lbl]}/{target_per_combo}, Toplam İlerleme: {len(existing_records) + len(new_records)}/{args.limit})")
        
        generated = generate_tweets_with_gemini(api_keys, cat, lbl, args.batch_size, seed_examples)
        
        added_in_batch = 0
        for item in generated:
            text = item.get("text", "").strip()
            reason = item.get("reason", "").strip()
            
            if not text:
                continue
                
            cleaned = strict_clean_for_duplicate(text)
            if cleaned not in seen_texts:
                seen_texts.add(cleaned)
                record = {"text": text, "label": lbl, "reason": reason, "category": cat}
                new_records.append(record)
                matrix_counts[cat][lbl] += 1
                added_in_batch += 1
                total_added += 1
                
        print(f"  -> Veri Havuzuna bu yığında {added_in_batch} adet BENZERSİZ tweet eklendi.")
        
        # Sürekli API'yi yormamak ve rate-limit'e takılmamak için dinamik bekleme
        if added_in_batch == 0:
            print("⚠️ Bu yığında 0 veri eklendi (Muhtemelen Rate Limit / 429 engeli). API penceresinin sıfırlanması için 30 saniye bekleniyor...")
            time.sleep(30)
        else:
            time.sleep(6)
        
        # Güvenli CSV Ara Kayıt (Tırnak işaretleri ve virgüller korumalı)
        all_records = existing_records + new_records
        with open(args.output, 'w', encoding='utf-8', newline='', errors='replace') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["text", "label", "reason"])
            for r in all_records:
                writer.writerow([r['text'], r['label'], r['reason']])

    print(f"\n🚀 TEBRİKLER! TAM DENGELİ VERİ SETİ TAMAMLANDI: {args.output}")

if __name__ == "__main__":
    main()
