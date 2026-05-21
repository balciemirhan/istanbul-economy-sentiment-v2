from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
import os
import sys
import threading
import pandas as pd
import io

# Proje kök dizinini Python yoluna ekle (böylece doğrudan da çalıştırılabilir)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db_manager import (
    Keyword, get_dashboard_stats, get_weekly_trend, get_active_keywords,
    add_keyword, delete_keyword, init_db, export_all_tweets_to_excel,
    get_paginated_tweets, get_tweets_by_filter,
    get_fetch_job_status, start_fetch_job, update_fetch_job_status
)
from nlp.insights_manager import generate_ai_insights
from api.tweet_fetcher import LocalUsageMonitor, config
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

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler for both API and HTML routes (DRY compliance)."""
    app.logger.exception(f"Beklenmeyen hata: {e}")
    if request.path.startswith('/api/'):
        return jsonify({"error": str(e)}), 500
    else:
        return f"Sistem hatası: {str(e)}", 500

def background_fetch_task(max_tweets, days):
    try:
        start_fetch_job()
        update_fetch_job_status(f"Arka plan işlemi başlıyor ({max_tweets} hedef, {days} gün)...", is_running=True)
        
        run_pipeline(max_tweets=max_tweets, days=days, status_callback=lambda msg: update_fetch_job_status(msg, is_running=True))
        update_fetch_job_status("İşlem başarıyla tamamlandı.", is_running=False)
    except Exception as e:
        update_fetch_job_status(f"Hata oluştu: {str(e)}", is_running=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/stats')
def stats():
    stats_data = get_dashboard_stats()
    return jsonify(stats_data)

@app.route('/api/weekly-trend')
def weekly_trend():
    sentiment = request.args.get('sentiment', 'hepsi')
    topic = request.args.get('topic', 'hepsi')
    data = get_weekly_trend(sentiment=sentiment, topic=topic)
    return jsonify(data)

@app.route('/api/tweets')
def tweets():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    sentiment = request.args.get('sentiment', 'hepsi')
    topic = request.args.get('topic', 'hepsi')
    keyword = request.args.get('keyword', '')

    data = get_paginated_tweets(
        page=page,
        limit=limit,
        sentiment=sentiment,
        topic=topic,
        keyword=keyword
    )
    return jsonify(data)

@app.route('/api/ai-insights')
def ai_insights():
    sentiment = request.args.get('sentiment', 'hepsi')
    topic = request.args.get('topic', 'hepsi')
    
    tweets_data = get_tweets_by_filter(sentiment=sentiment, topic=topic)
    return jsonify(generate_ai_insights(tweets_data))

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
    status = get_fetch_job_status()
    if status["is_running"]:
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
    return jsonify(get_fetch_job_status())

@app.route('/api/export', methods=['GET'])
def export_excel():
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

if __name__ == '__main__':
    # Flask sunucusu başlatılmadan önce veritabanı tablolarını (Keyword vs.) kontrol et ve eksikse yarat
    init_db()
    
    print("Dashboard baslatiliyor... Tarayicinizda http://127.0.0.1:5000 adresine gidin.")
    app.run(debug=True, port=5000)
