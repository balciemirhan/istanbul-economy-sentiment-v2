# İstanbul Metre — Proje Anlama Rehberi

Bu belge, kod tabanının aşama aşama anlaşılması için hazırlanmıştır. Plan: sadece anlama (kod değişikliği zorunlu değil).

---

## 1. Belgeler: hedef vs güncel durum

| Kaynak | Ne anlatır | Güvenilirlik |
|--------|------------|--------------|
| `project_status.md` | 5 adımlı iş akışı, hedef klasör yapısı, “sıradaki adımlar” | **Eski** — checklist’teki maddelerin çoğu kodda tamamlanmış |
| `project_state.md` | Son özellikler (kota, TheFuzz, trafik override, N-gram içgörü) | **Güncel** — mühendislik detayı için referans |
| `README.md` | Kurulum, genel NLP kuralları | **Kısmen eski** — örn. “ilk 50 karakter” deduplication; kodda %75 TheFuzz |

### İş akışı hedefi (`project_status.md`)

1. Haftalık X’ten veri çek → **Var** (admin panel, manuel)
2. NLP analizi → **Var**
3. SQLite kayıt → **Var**
4. Dashboard → **Var** (trend grafiği kısmen demo)
5. Haftalık PDF rapor → **Yok**

### Dokümanda var, kodda yok

- `api/scheduler.py` — otomatik Pazartesi çekimi
- `reports/pdf_generator.py` — PDF (`fpdf2` requirements’ta)
- `database/migrations/` — Alembic yok; `db_manager.init_db` içinde manuel `ALTER TABLE`
- `dashboard/frontend/` — gerçek yol: `dashboard/templates/`

### Kodda var, doküman/UI ile uyumsuz

- `GET /api/viral-tweets` — `app.py` içinde duruyor; `project_state.md` UI’dan kaldırıldığını söylüyor

---

## 2. Pipeline: `main.run_pipeline` uçtan uca

**Tetikleyiciler:**

- Admin: `POST /api/fetch-data` → `background_fetch_task` → `run_pipeline(max_tweets, days, status_callback)`
- CLI: `python main.py` → `run_pipeline(max_tweets=0)` → **veri çekmez** (bilinçli kapalı)

**Adımlar:**

```
init_db()
  → TweetFetcher().fetch_tweets(max_tweets, days)     # X API
  → Her tweet için:
       clean_tweet_text()
       len < 15 → elenir
       contains_profanity(ham metin) → elenir
       TheFuzz token_set_ratio >= 75 (DB son N gün + bu batch) → elenir
       SentimentAnalyzer.analyze() → sentiment, score, is_ironic
  → save_tweets_bulk(processed)
  → Tüm DB → reports/istanbul_tum_yedek_YYYYMMDD_HHMMSS.xlsx
```

**Dönüş:** `{ success, saved, filtered, message }`

---

## 3. Veri çekme: `api/tweet_fetcher.py`

### `XAPIClient`

- `GET https://api.x.com/2/tweets/search/recent`
- Alanlar: `created_at`, `public_metrics`, `author_id`; expansion: `users`

### `LocalUsageMonitor`

- Dosya: `data/local_usage_history.json`
- Aylık limit: `MONTHLY_TWEET_BUDGET = 10000` (ham API response tweet sayısı)

### Sorgu (`build_istanbul_query`)

```
(istanbul OR i̇stanbul) (kelime1 OR kelime2 ...) lang:tr -is:retweet -is:nullcast
```

Kelimeler: `keywords` tablosu, kategoriye göre gruplanır.

### Kota dağılımı

1. `max_tweets` kategori sayısına bölünür
2. Her kategori için `days` (max 7) güne bölünür
3. **Smart quota:** `(tweets_for_cat // days) < 10` ve `days > 1` ise günlere bölünmez; tek aralıkta `max(10, tweets_for_cat)` çekilir (X API minimum 10/request israfını önler)
4. Her istekte `max_results = max(10, min(100, kalan))`

### `TweetFilter` (API sonrası)

- Min 20 karakter, min 5 kelime, min 0 beğeni
- Emoji-only eleme

### Çıktı formatı (`_parse_item`)

`tweet_id`, `text`, `author_username`, `likes`, `retweets`, `views`, `created_at`, `category`

### Varsayılan seed kategoriler (`db_manager.seed_keywords_if_empty`)

| Kategori | Örnek kelimeler |
|----------|-----------------|
| `makro_ekonomi` | enflasyon, asgari ücret, pahalılık, … |
| `ulasim_lojistik` | mazot, iett zammı, metrobüs, … |
| `gayrimenkul_insaat` | kira, emlak, aidat, … |
| `ticaret_perakende` | esnaf, market fiyatları, … |

---

## 4. NLP sırası ve sorumluluklar

### Gerçek çalışma sırası

| Sıra | Nerede | Ne |
|------|--------|-----|
| 1 | `main.py` | `clean_tweet_text`, uzunluk, küfür, TheFuzz dedup |
| 2 | `sentiment_analyzer.analyze` | Tekrar `clean_tweet_text` |
| 3 | `sentiment_analyzer` | Büyük harf terbiyecisi (%60+ uppercase → `.capitalize()`) |
| 4 | `sentiment_analyzer` | BERT `savasy/bert-base-turkish-sentiment-cased` |
| 5 | `sentiment_analyzer` | Skor < 0.85 → `notr` |
| 6 | `irony_detector` | `detect_irony` (ham metin) |
| 7 | `irony_detector` | İroni varsa `flip_sentiment` |
| 8 | `sentiment_analyzer` | Override: isyan kelimeleri, trafik kuralı, kanal istanbul nötr |

### `text_cleaner.py`

- URL, @, #, RT, emoji temizliği
- `contains_profanity`: regex + negative lookahead (`sik(?!inti|let)`)

### `irony_detector.py`

- İroni = ironi kelimesi **ve** (çoklu `!`/`?` **veya** harf uzatması)
- Flip: pozitif ↔ negatif

---

## 5. Dashboard: API ve frontend

### Flask route’ları (`dashboard/api/app.py`)

| Route | Method | Kullanım |
|-------|--------|----------|
| `/` | GET | Ana dashboard |
| `/admin` | GET | Yönetim paneli |
| `/api/stats` | GET | Pasta grafik, özet kartlar |
| `/api/weekly-trend` | GET | Son 28 gün, 4 hafta; `sentiment`, `topic` filtre (`Tweet.created_at` = X yayın tarihi) |
| `/api/tweets` | GET | Sayfalı feed (`page`, `limit`, `sentiment`, `topic`, `keyword`) |
| `/api/ai-insights` | GET | Sentez + bigram/unigram + ironi profili |
| `/api/keywords` | GET/POST | Kelime listesi / ekleme |
| `/api/keywords/<id>` | DELETE | Kelime sil |
| `/api/usage` | GET | Aylık kota |
| `/api/fetch-data` | POST | Pipeline thread |
| `/api/fetch-status` | GET | Son 10 log satırı |
| `/api/export` | GET | Excel indir |
| `/api/viral-tweets` | GET | **Kullanılmıyor** (ölü) |

### `index.html` — ne zaman hangi API?

| Olay | API |
|------|-----|
| `DOMContentLoaded` | `GET /api/stats`, `GET /api/keywords`, `GET /api/ai-insights`, `GET /api/weekly-trend` |
| Sonsuz scroll | `GET /api/tweets?page=&sentiment=&topic=` |
| Filtre değişimi | `resetAndLoadTweets` + `loadAIInsights` + `loadWeeklyTrend` |
| Excel linki | `GET /api/export` (doğrudan href) |

### `admin.html` — ne zaman hangi API?

| Olay | API |
|------|-----|
| Sayfa yükleme | `GET /api/usage`, `GET /api/keywords`, `GET /api/fetch-status` |
| Veri çek | `POST /api/fetch-data` → her 1 sn `GET /api/fetch-status` |
| Kelime CRUD | `POST /api/keywords`, `DELETE /api/keywords/<id>` |

### Veritabanı (`database/models.py`)

- **Tweet:** `tweet_id` (unique), `text`, `sentiment`, `score`, `is_ironic`, `category`, metrikler
- **Keyword:** `word` (unique), `category`
- Dosya: `{proje_kökü}/istanbul_ekonomi.db`

---

## 6. Bilinen eksikler ve sınırlar

| Konu | Durum |
|------|--------|
| Haftalık trend grafiği | `GET /api/weekly-trend` + `get_weekly_trend()` — son 28 gün, 4x7 gün, tweet yayın tarihi |
| PDF haftalık rapor | Planlanmış, implementasyon yok |
| Scheduler (Pazartesi) | Planlanmış, implementasyon yok |
| `/api/viral-tweets` | Backend’de var, UI yok |
| `project_status.md` checklist | Güncellenmemiş |
| README deduplication | “50 karakter” yerine kodda TheFuzz %75 |
| CLI `main.py` | `max_tweets=0` ile kapalı |

---

## Kontrol listesi

- [x] Veri çekimi admin’den thread ile `run_pipeline` tetikleniyor
- [x] Kota JSON + X min-10 smart quota ile yönetiliyor
- [x] NLP: temizlik → BERT → ironi → override
- [x] Kopya: TheFuzz %75 + DB geçmişi
- [x] Dashboard: sentiment + `Tweet.category` filtreleri
- [x] Haftalık trend gerçek (28 gün / 4 hafta); PDF/scheduler yok

---

## Önerilen okuma sırası (kod)

1. `project_status.md` → `project_state.md`
2. `main.py` → `api/tweet_fetcher.py` → `api/x_api_client.py`
3. `nlp/text_cleaner.py` → `nlp/sentiment_analyzer.py` → `nlp/irony_detector.py`
4. `database/models.py` → `database/db_manager.py`
5. `dashboard/api/app.py` → `dashboard/templates/index.html` → `admin.html`
