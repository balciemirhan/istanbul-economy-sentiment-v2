import sqlite3
import re

def normalize_for_spam_check(text):
    # Sadece harf ve rakamları tut, her şeyi küçük harfe çevir
    # Bu sayede ' ve ’ farkı veya nokta/virgül farkı spam engelini aşamaz
    return re.sub(r'[^\w]', '', text.lower())[:100] # İlk 100 karakterlik saf metin

conn = sqlite3.connect('istanbul_ekonomi.db')
c = conn.cursor()
c.execute('SELECT id, text FROM tweets ORDER BY created_at ASC')
tweets = c.fetchall()

seen = set()
to_delete = []

for t_id, text in tweets:
    normalized = normalize_for_spam_check(text)
    if normalized in seen:
        to_delete.append((t_id,))
    else:
        seen.add(normalized)

print(f"Yeni akıllı filtre ile silinecek kopya sayısı: {len(to_delete)} adet.")
c.executemany('DELETE FROM tweets WHERE id = ?', to_delete)
conn.commit()
conn.close()
print("Veritabanı mükemmel şekilde temizlendi!")
