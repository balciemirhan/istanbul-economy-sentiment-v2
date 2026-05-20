from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
import os
import threading
import pandas as pd
import io

from database.db_manager import (
    SessionLocal, Tweet, Keyword,
    get_dashboard_stats, get_weekly_trend, get_active_keywords,
    add_keyword, delete_keyword, init_db, export_all_tweets_to_excel
)
from nlp.insights_manager import generate_ai_insights
from api.tweet_fetcher import LocalUsageMonitor, config
from sqlalchemy import or_
from main import run_pipeline

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

@app.after_request
def add_header(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

FETCH_STATUS = {
    "is_running": False,
    "message": "Bekleniyor...",
    "logs": []
}

def update_fetch_status(msg):
    FETCH_STATUS["message"] = msg
    FETCH_STATUS["logs"].append(msg)
    if len(FETCH_STATUS["logs"]) > 10:
        FETCH_STATUS["logs"].pop(0)

def background_fetch_task(max_tweets, days):
    try:
        FETCH_STATUS["is_running"] = True
        FETCH_STATUS["logs"] = []
        update_fetch_status(f"Arka plan işlemi başlıyor ({max_tweets} hedef, {days} gün)...")
        
        # main_path eklemesine gerek yok çünkü root'tan çalıştırılacak
        
        run_pipeline(max_tweets=max_tweets, days=days, status_callback=update_fetch_status)
        update_fetch_status("İşlem başarıyla tamamlandı.")
    except Exception as e:
        update_fetch_status(f"Hata oluştu: {str(e)}")
    finally:
        FETCH_STATUS["is_running"] = False

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Dashboard HTML dosyası bulunamadı: {e}", 500

@app.route('/admin')
def admin():
    try:
        return render_template('admin.html')
    except Exception as e:
        return f"Admin HTML dosyası bulunamadı: {e}", 500

@app.route('/api/stats')
def stats():
    try:
        stats_data = get_dashboard_stats()
        return jsonify(stats_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/weekly-trend')
def weekly_trend():
    try:
        sentiment = request.args.get('sentiment', 'hepsi')
        topic = request.args.get('topic', 'hepsi')
        data = get_weekly_trend(sentiment=sentiment, topic=topic)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tweets')
def tweets():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    sentiment = request.args.get('sentiment', 'hepsi')
    topic = request.args.get('topic', 'hepsi')
    keyword = request.args.get('keyword', '')

    db = SessionLocal()
    try:
        query = db.query(Tweet)
        if sentiment != 'hepsi':
            query = query.filter(Tweet.sentiment == sentiment)
            
        if topic != 'hepsi':
            query = query.filter(Tweet.category == topic)
            
        if keyword:
            query = query.filter(Tweet.text.ilike(f"%{keyword}%"))

        total_count = query.count()
        offset = (page - 1) * limit
        
        recent_tweets = query.order_by(Tweet.created_at.desc()).offset(offset).limit(limit).all()
        
        tweets_list = []
        for t in recent_tweets:
            tweets_list.append({
                "id": t.tweet_id,
                "text": t.text,
                "user": f"@{t.author_username}",
                "date": t.created_at.strftime("%d %b"),
                "sentiment": t.sentiment,
                "score": t.score,
                "is_ironic": t.is_ironic
            })
            
        has_more = (offset + limit) < total_count
        
        return jsonify({
            "tweets": tweets_list,
            "has_more": has_more
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route('/api/ai-insights')
def ai_insights():
    sentiment = request.args.get('sentiment', 'hepsi')
    topic = request.args.get('topic', 'hepsi')
    
    db = SessionLocal()
    try:
        query = db.query(Tweet)
        if sentiment != 'hepsi':
            query = query.filter(Tweet.sentiment == sentiment)
        if topic != 'hepsi':
            query = query.filter(Tweet.category == topic)
            
        tweets = query.all()
        return jsonify(generate_ai_insights(tweets))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# --- ADMIN ENDPOINTS ---

@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    return jsonify(get_active_keywords())

@app.route('/api/keywords', methods=['POST'])
def post_keyword():
    data = request.json
    word = data.get('word')
    category = data.get('category', 'genel')
    if not word:
        return jsonify({"error": "Kelime boş olamaz"}), 400
    res = add_keyword(word.lower(), category)
    if res.get("success"):
        return jsonify(res)
    return jsonify(res), 400

@app.route('/api/keywords/<int:kw_id>', methods=['DELETE'])
def del_keyword(kw_id):
    res = delete_keyword(kw_id)
    if res.get("success"):
        return jsonify(res)
    return jsonify(res), 400

@app.route('/api/usage', methods=['GET'])
def get_usage():
    monitor = LocalUsageMonitor()
    usage = monitor.get_current_month_usage()
    limit = config.MONTHLY_TWEET_BUDGET
    return jsonify({
        "used": usage,
        "limit": limit,
        "percentage": round((usage / limit) * 100, 1) if limit > 0 else 0
    })

@app.route('/api/fetch-data', methods=['POST'])
def fetch_data():
    if FETCH_STATUS["is_running"]:
        return jsonify({"error": "İşlem zaten devam ediyor"}), 400
        
    data = request.json or {}
    max_tweets = int(data.get('max_tweets', 100))
    days = int(data.get('days', 7))
    
    # X API Basic kısıtlamaları
    if days > 7: days = 7
    if days < 1: days = 1
    
    thread = threading.Thread(target=background_fetch_task, args=(max_tweets, days))
    thread.daemon = True
    thread.start()
    return jsonify({"success": True, "message": "Arka plan işlemi başlatıldı."})

@app.route('/api/fetch-status', methods=['GET'])
def fetch_status():
    return jsonify(FETCH_STATUS)

@app.route('/api/export', methods=['GET'])
def export_excel():
    try:
        output = io.BytesIO()
        if not export_all_tweets_to_excel(output):
            return "Excel oluşturulacak veri bulunamadı veya hata oluştu.", 404
            
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="istanbul_ekonomi_tum_veriler.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return f"Excel oluşturulurken hata: {e}", 500

if __name__ == '__main__':
    # Flask sunucusu başlatılmadan önce veritabanı tablolarını (Keyword vs.) kontrol et ve eksikse yarat
    init_db()
    
    print("Dashboard baslatiliyor... Tarayicinizda http://127.0.0.1:5000 adresine gidin.")
    app.run(debug=True, port=5000)
