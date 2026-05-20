import re
from collections import Counter

STOP_WORDS = set([
    "bir", "ve", "bu", "ile", "de", "da", "için", "gibi", "çok", "istanbul", 
    "var", "yok", "kadar", "olan", "olarak", "daha", "en", "ki", "mi", "mı", 
    "mu", "mü", "ne", "niye", "ama", "fakat", "lakin", "ise", "diye", "ben", 
    "sen", "o", "biz", "siz", "onlar", "bana", "sana", "onu", "bunu", "şunu", 
    "her", "hiç", "sonra", "önce", "hangi", "nasıl", "neden", "niçin", "şimdi",
    "şu", "öyle", "göre", "kendi", "bile", "zaten", "başka", "tüm", "hep",
    "yani", "bence", "sadece", "zira", "çünkü", "meğer", "oysa", "oysaki", 
    "halgbu", "madem", "belki", "biri", "birkaç", "birşeyi", "şey", "şeyi", 
    "şeyler", "böyle", "şöyle", "şunlar", "bunlar", "herkes", "hepsi", "kim", 
    "kimse", "hiçbiri", "miyiz", "misiniz", "midir", "mıdır", "miz", "mizdir", 
    "böylece", "şunları", "bunları", "tarafından", "altı", "yedi", "sekiz", 
    "dokuz", "on", "bilyon", "milyon", "bin", "yüz", "trilyon"
])

def generate_ai_insights(tweets):
    total_tweets = len(tweets)
    
    if total_tweets == 0:
        return [
            {"icon": "📭", "text": "Bu filtreye uygun yeterli veri bulunamadı."}
        ]
        
    # İstatistikleri hesapla
    pos_count = sum(1 for t in tweets if t.sentiment == 'pozitif')
    neg_count = sum(1 for t in tweets if t.sentiment == 'negatif')
    ironic_count = sum(1 for t in tweets if t.is_ironic)
    total_engagement = sum((t.likes or 0) + (t.retweets or 0) for t in tweets)
    
    pos_pct = (pos_count / total_tweets) * 100
    neg_pct = (neg_count / total_tweets) * 100
    irony_pct = (ironic_count / total_tweets) * 100
    
    insights = []
    
    # 1. ATMOSFER & RİSK SKORU (Sentez)
    if neg_pct > 55 and total_engagement > 1500:
        insights.append({
            "icon": "🚨", 
            "text": f"<b>Kriz Atmosferi (Yüksek Risk):</b> Hızla yayılan güçlü bir hoşnutsuzluk (%{neg_pct:.1f} Negatif, {total_engagement} Etkileşim). Konu ana akım (mainstream) tartışma eşiğini aşmış durumda."
        })
    elif neg_pct > 55:
        insights.append({
            "icon": "⚠️", 
            "text": f"<b>İzole Şikayetler (Bölgesel Hoşnutsuzluk):</b> Güçlü bir negatiflik eğilimi var (%{neg_pct:.1f}), ancak etkileşim hacmi ({total_engagement}) henüz geniş kitlelere sıçramadığını gösteriyor."
        })
    elif pos_pct > 55 and total_engagement > 1500:
        insights.append({
            "icon": "⭐", 
            "text": f"<b>Güçlü Pozitif Gündem:</b> Toplum genelinde net bir memnuniyet (%{pos_pct:.1f} Pozitif) ve yüksek katılım (Viral yayılım) gözlemleniyor."
        })
    elif pos_pct > 55:
        insights.append({
            "icon": "📈", 
            "text": f"<b>Ilımlı Memnuniyet:</b> Konu etrafında destekleyici ve pozitif (%{pos_pct:.1f}) bir hava hakim, stabil bir etkileşim mevcut."
        })
    else:
        if total_engagement > 1500:
            insights.append({
                "icon": "⚖️", 
                "text": f"<b>Yüksek Kutuplaşma:</b> Kitleler ikiye bölünmüş durumda. Yoğun bir etkileşim savaşı ({total_engagement}) ve duygu karmaşası var."
            })
        else:
            insights.append({
                "icon": "📊", 
                "text": f"<b>Stabil/Nötr Seyir:</b> Konuda radikal bir duygu baskınlığı veya viral bir sıçrama tespit edilmedi."
            })

    # 2. LOCAL NLP (N-GRAM) MOTORU (Kök Nedenler)
    
    bigram_counts = Counter()
    unigram_counts = Counter()
    for t in tweets:
        text = str(t.text).replace('İ', 'i').replace('I', 'ı').lower()
        text = re.sub(r'http[s]?://\S+|pic\.twitter\.com/\S+|t\.co/\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        words = [w for w in re.findall(r'[a-zçğıöşü]+', text) if len(w) > 2 and w not in STOP_WORDS]
        
        for w in words:
            unigram_counts[w] += 1
            
        if len(words) >= 2:
            for i in range(len(words)-1):
                bigram = f"{words[i]} {words[i+1]}"
                bigram_counts[bigram] += 1
                
    top_bigrams = bigram_counts.most_common(2)
    if len(top_bigrams) == 2 and top_bigrams[0][1] > 1:
        bg1 = top_bigrams[0][0].title()
        bg2 = top_bigrams[1][0].title()
        insights.append({
            "icon": "🧬",
            "text": f"<b>Ana Katalizörler (Kök Neden):</b> Semantik analiz motorumuz, tepkilerin merkez üssünde spesifik olarak <b>'{bg1}'</b> ve <b>'{bg2}'</b> konularının yattığını tespit etti."
        })
    elif len(top_bigrams) > 0 and top_bigrams[0][1] > 1:
        bg1 = top_bigrams[0][0].title()
        insights.append({
            "icon": "🧬",
            "text": f"<b>Baskın Katalizör (Kök Neden):</b> Tartışmaları domine eden spesifik odak noktası <b>'{bg1}'</b> olarak ölçümlenmiştir."
        })
    else:
        top_unigrams = unigram_counts.most_common(2)
        if len(top_unigrams) == 2:
            ug1 = top_unigrams[0][0].title()
            ug2 = top_unigrams[1][0].title()
            insights.append({
                "icon": "🧬",
                "text": f"<b>Anahtar Konu Dağılımı:</b> Veri mimarimiz, mevcut tartışma havuzunda öne çıkan temaların <b>'{ug1}'</b> ve <b>'{ug2}'</b> olduğunu gösteriyor."
            })
        elif len(top_unigrams) == 1:
            ug1 = top_unigrams[0][0].title()
            insights.append({
                "icon": "🧬",
                "text": f"<b>Tekil Odak Noktası:</b> Sistemdeki dar veri setinde tespit edilen yegane kavramsal odak: <b>'{ug1}'</b>."
            })
        else:
            insights.append({
                "icon": "🧬",
                "text": "<b>Veri Yetersizliği:</b> Havuz, spesifik bir semantik örüntü veya kök neden çıkarılamayacak kadar dağınık."
            })

    # 3. DAVRANIŞSAL PROFİL
    if irony_pct > 10:
        insights.append({
            "icon": "🎭", 
            "text": f"<b>Toplumsal Tepki Profili:</b> Kitle reaksiyonlarını doğrudan yüzleşmek yerine, yoğun düzeyde (<b>%{irony_pct:.1f}</b>) alaycı ve sarkastik bir dille ifade etmeyi seçiyor."
        })
    elif irony_pct > 4:
        insights.append({
            "icon": "🤔", 
            "text": f"<b>Toplumsal Tepki Profili:</b> İfadelerde yer yer (<b>%{irony_pct:.1f}</b>) ironik bir ton kullanılsa da, iletişim genel olarak net."
        })
    else:
        insights.append({
            "icon": "🛡️", 
            "text": f"<b>Toplumsal Tepki Profili:</b> İroni oranı çok düşük. Kitle, öfkesini veya memnuniyetini hiçbir mecaza saklamadan, sert ve doğrudan bir yüzleşme diliyle dışa vuruyor."
        })
        
    return insights
