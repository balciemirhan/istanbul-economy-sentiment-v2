
let pieChartInstance = null;
let lineChartInstance = null;
let trendChartView = 'line';
let lastTrendWeeks = [];

let currentPage = 1;
let currentSentiment = 'hepsi';
let currentTopic = 'hepsi';
let isLoading = false;
let hasMore = true;

async function fetchStats() {
  try {
    const statsRes = await fetch('/api/stats');
    const stats = await statsRes.json();
    updateDashboard(stats);
  } catch (err) {
    console.error("İstatistikler çekilirken hata oluştu:", err);
  }
}

async function loadMoreTweets() {
  if (isLoading || !hasMore) return;
  isLoading = true;
  
  const list = document.getElementById('tweetList');
  if (currentPage === 1) {
    list.innerHTML = '';
  }
  
  const loadingHtml = `<div id="loadingIndicator" style="text-align:center; padding: 20px; color: var(--text-dim); font-size: 14px;">Yükleniyor...</div>`;
  list.insertAdjacentHTML('beforeend', loadingHtml);

  try {
    const res = await fetch(`/api/tweets?page=${currentPage}&limit=50&sentiment=${currentSentiment}&topic=${currentTopic}`);
    const data = await res.json();
    
    document.getElementById('loadingIndicator')?.remove();
    
    hasMore = data.has_more;
    const tweets = data.tweets;
    
    const tweetsHtml = tweets.map(t => `
      <div class="tweet-item">
        <div class="tweet-sentiment-dot ${t.sentiment}"></div>
        <div class="tweet-content">
          <div class="tweet-text">${t.text}</div>
          <div class="tweet-meta">
            <span>${t.user}</span>
            <span>${t.date}</span>
            <span class="tweet-score ${t.sentiment}">${t.sentiment.toUpperCase()} · ${t.score}</span>
            ${t.is_ironic ? '<span style="color:#6366f1;">🤖 İroni Tespit Edildi</span>' : ''}
          </div>
        </div>
      </div>
    `).join('');
    
    list.insertAdjacentHTML('beforeend', tweetsHtml);
    currentPage++;
    
  } catch (err) {
    console.error("Tweetler çekilirken hata oluştu:", err);
    document.getElementById('loadingIndicator')?.remove();
  } finally {
    isLoading = false;
  }
}

function updateDashboard(stats) {
  // Rakamları güncelle
  document.getElementById('stat-total').innerText = stats.total;
  document.getElementById('stat-positive').innerText = stats.positive.count;
  document.getElementById('sub-positive').innerText = `%${stats.positive.percentage} oran`;
  document.getElementById('stat-negative').innerText = stats.negative.count;
  document.getElementById('sub-negative').innerText = `%${stats.negative.percentage} oran`;
  document.getElementById('stat-neutral').innerText = stats.neutral.count;
  document.getElementById('sub-neutral').innerText = `%${stats.neutral.percentage} oran`;
  
  // Ortalama Güven Skorunu Güncelle
  if(document.getElementById('stat-confidence')) {
      document.getElementById('stat-confidence').innerText = `Ort. ${stats.avg_score}`;
  }

  // Pie Chart Güncelle
  const pieCtx = document.getElementById('pieChart').getContext('2d');
  if(pieChartInstance) pieChartInstance.destroy();
  pieChartInstance = new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: ['Pozitif', 'Negatif', 'Nötr'],
      datasets: [{
        data: [stats.positive.count, stats.negative.count, stats.neutral.count],
        backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
        borderColor: '#111827',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { family: 'Outfit', size: 13 }, padding: 20 }
        }
      }
    }
  });

}

const TREND_CHART_COLORS = {
  pozitif: { border: '#10b981', fill: 'rgba(16,185,129,0.15)' },
  negatif: { border: '#ef4444', fill: 'rgba(239,68,68,0.15)' },
  notr: { border: '#f59e0b', fill: 'rgba(245,158,11,0.15)' },
};

function setTrendLoading(visible) {
  const el = document.getElementById('trendLoading');
  const canvas = document.getElementById('lineChart');
  if (el) el.classList.toggle('visible', visible);
  if (canvas) canvas.style.opacity = visible ? '0.25' : '1';
}

function getWeekDominant(w) {
  const total = (w.positive || 0) + (w.negative || 0) + (w.neutral || 0);
  if (total === 0) return { key: 'empty', label: 'Veri yok', pct: 0 };
  const entries = [
    { key: 'pos', label: 'Pozitif', count: w.positive || 0 },
    { key: 'neg', label: 'Negatif', count: w.negative || 0 },
    { key: 'neu', label: 'Nötr', count: w.neutral || 0 },
  ];
  entries.sort((a, b) => b.count - a.count);
  return { key: entries[0].key, label: entries[0].label, pct: Math.round((entries[0].count / total) * 100) };
}

function renderTrendWeekPills(weeks) {
  const container = document.getElementById('trendWeekPills');
  if (!container) return;
  container.innerHTML = weeks.map((w, i) => {
    const dom = getWeekDominant(w);
    const moodClass = dom.key === 'pos' ? 'mood-pos' : dom.key === 'neg' ? 'mood-neg' : dom.key === 'neu' ? 'mood-neu' : 'mood-empty';
    const hasData = (w.total || 0) > 0;
    const shortLabel = `H${i + 1}`;
    return `
      <div class="trend-week-pill ${moodClass}${hasData ? ' has-data' : ''}" title="${w.label}" data-week-index="${i}">
        <div class="pill-label" title="${w.label}">${shortLabel}</div>
        <div class="pill-total">${w.total || 0}</div>
        <div class="pill-mood">${hasData ? dom.label + ' %' + dom.pct : '—'}</div>
      </div>
    `;
  }).join('');
}

function updateTrendSummary(weeks) {
  const periodTotal = weeks.reduce((s, w) => s + (w.total || 0), 0);
  const totalEl = document.getElementById('trendPeriodTotal');
  const momentumEl = document.getElementById('trendMomentumText');
  const emptyEl = document.getElementById('trendEmpty');
  const canvas = document.getElementById('lineChart');

  if (totalEl) totalEl.textContent = periodTotal;
  if (emptyEl) emptyEl.classList.toggle('visible', periodTotal === 0);
  if (canvas) canvas.style.visibility = periodTotal === 0 ? 'hidden' : 'visible';

  if (momentumEl && weeks.length >= 2) {
    const last = weeks[weeks.length - 1];
    const prev = weeks[weeks.length - 2];
    const lastNeg = last.total ? Math.round(((last.negative || 0) / last.total) * 100) : 0;
    const prevNeg = prev.total ? Math.round(((prev.negative || 0) / prev.total) * 100) : 0;
    const delta = lastNeg - prevNeg;
    if (last.total === 0 && prev.total === 0) {
      momentumEl.textContent = 'Son hafta: veri bekleniyor';
    } else if (delta > 0) {
      momentumEl.innerHTML = `Son hafta negatiflik: <strong>+%${delta}</strong> (önceki haftaya göre)`;
      momentumEl.style.color = 'var(--negative)';
    } else if (delta < 0) {
      momentumEl.innerHTML = `Son hafta negatiflik: <strong>${delta}%</strong> (iyileşme)`;
      momentumEl.style.color = 'var(--positive)';
    } else {
      momentumEl.textContent = 'Son iki hafta benzer duygu dağılımı';
      momentumEl.style.color = 'var(--text-dim)';
    }
  } else if (momentumEl) {
    momentumEl.textContent = '—';
  }
}

function buildTrendDatasets(weeks, chartType) {
  const isStacked = chartType === 'stacked';
  return [
    {
      label: 'Pozitif',
      data: weeks.map(w => w.positive),
      borderColor: TREND_CHART_COLORS.pozitif.border,
      backgroundColor: TREND_CHART_COLORS.pozitif.fill,
      borderWidth: isStacked ? 0 : 2,
      fill: !isStacked,
      tension: 0.35,
      pointRadius: isStacked ? 0 : 4,
      pointHoverRadius: 6,
      stack: isStacked ? 'week' : undefined,
    },
    {
      label: 'Negatif',
      data: weeks.map(w => w.negative),
      borderColor: TREND_CHART_COLORS.negatif.border,
      backgroundColor: TREND_CHART_COLORS.negatif.fill,
      borderWidth: isStacked ? 0 : 2,
      fill: !isStacked,
      tension: 0.35,
      pointRadius: isStacked ? 0 : 4,
      pointHoverRadius: 6,
      stack: isStacked ? 'week' : undefined,
    },
    {
      label: 'Nötr',
      data: weeks.map(w => w.neutral),
      borderColor: TREND_CHART_COLORS.notr.border,
      backgroundColor: TREND_CHART_COLORS.notr.fill,
      borderWidth: isStacked ? 0 : 2,
      fill: !isStacked,
      tension: 0.35,
      pointRadius: isStacked ? 0 : 4,
      pointHoverRadius: 6,
      stack: isStacked ? 'week' : undefined,
    },
  ];
}

function setTrendView(view) {
  trendChartView = view;
  document.querySelectorAll('.trend-view-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });
  if (lastTrendWeeks.length) updateLineChart(lastTrendWeeks);
}

async function loadWeeklyTrend() {
  setTrendLoading(true);
  try {
    const res = await fetch(`/api/weekly-trend?sentiment=${currentSentiment}&topic=${currentTopic}`);
    const data = await res.json();
    lastTrendWeeks = data.weeks || [];
    renderTrendWeekPills(lastTrendWeeks);
    updateTrendSummary(lastTrendWeeks);
    const periodTotal = lastTrendWeeks.reduce((s, w) => s + (w.total || 0), 0);
    if (periodTotal > 0) {
      updateLineChart(lastTrendWeeks);
    } else if (lineChartInstance) {
      lineChartInstance.destroy();
      lineChartInstance = null;
    }
  } catch (err) {
    console.error("Haftalık trend hatası:", err);
  } finally {
    setTrendLoading(false);
  }
}

function updateLineChart(weeks) {
  const canvas = document.getElementById('lineChart');
  if (!canvas || weeks.length === 0) return;

  const lineCtx = canvas.getContext('2d');
  if (lineChartInstance) lineChartInstance.destroy();

  const isStacked = trendChartView === 'stacked';
  const labels = weeks.map((w, i) => `H${i + 1}`);

  lineChartInstance = new Chart(lineCtx, {
    type: isStacked ? 'bar' : 'line',
    data: {
      labels,
      datasets: buildTrendDatasets(weeks, trendChartView),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { family: 'Outfit', size: 12 }, padding: 16, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#e2e8f0',
          bodyColor: '#94a3b8',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            title: (items) => {
              const idx = items[0]?.dataIndex;
              return weeks[idx]?.label || '';
            },
            label: (ctx) => {
              const val = ctx.parsed.y ?? 0;
              const w = weeks[ctx.dataIndex];
              const total = w?.total || 1;
              const pct = w?.total ? Math.round((val / total) * 100) : 0;
              return ` ${ctx.dataset.label}: ${val} (%${pct})`;
            },
            footer: (items) => {
              const idx = items[0]?.dataIndex;
              const w = weeks[idx];
              if (!w) return '';
              return `Toplam: ${w.total} tweet`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked: isStacked,
          grid: { color: 'rgba(148,163,184,0.06)' },
          ticks: { color: '#64748b', font: { size: 11 } },
        },
        y: {
          stacked: isStacked,
          beginAtZero: true,
          grid: { color: 'rgba(148,163,184,0.08)' },
          ticks: { color: '#64748b', stepSize: 1, precision: 0 },
          title: { display: true, text: 'Tweet sayısı', color: '#64748b', font: { size: 11 } },
        },
      },
    },
  });
}

function setSentimentFilter(filter) {
  document.querySelectorAll('#sentimentTabs .feed-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  currentSentiment = filter;
  resetAndLoadTweets();
}

function openTopicModal() {
  document.getElementById('topicModal').classList.add('active');
}

function closeTopicModal(event) {
  if (event && event.target !== document.getElementById('topicModal')) return;
  document.getElementById('topicModal').classList.remove('active');
}

function setTopicFilter(filter, displayName, icon) {
  currentTopic = filter;
  document.getElementById('topicFilterBtn').querySelector('.text').innerText = displayName;
  document.getElementById('topicFilterBtn').querySelector('.icon').innerText = icon;
  
  document.querySelectorAll('.topic-card').forEach(t => t.classList.remove('active'));
  const activeCard = document.querySelector(`.topic-card[data-cat="${filter}"]`);
  if(activeCard) activeCard.classList.add('active');
  
  closeTopicModal();
  resetAndLoadTweets();
}

function resetAndLoadTweets() {
  const list = document.getElementById('tweetList');
  if(list) list.style.opacity = '0.3';
  
  currentPage = 1;
  hasMore = true;
  
  loadMoreTweets().then(() => {
    if(list) list.style.opacity = '1';
  });
  loadAIInsights();
  loadWeeklyTrend();
}


async function loadAIInsights() {
  try {
    const list = document.getElementById('aiInsightsList');
    list.innerHTML = '<div style="font-size: 12px; color: var(--text-dim); text-align: center; padding-top: 30px;">İçgörüler hesaplanıyor...</div>';
    
    const res = await fetch(`/api/ai-insights?sentiment=${currentSentiment}&topic=${currentTopic}`);
    const insights = await res.json();
    
    let html = '';
    insights.forEach(item => {
      html += `
        <div class="ai-insight-item">
          <div class="ai-insight-icon">${item.icon}</div>
          <div class="ai-insight-text">${item.text}</div>
        </div>
      `;
    });
    
    list.innerHTML = html;
  } catch(e) {
    console.error("AI Insights hatası", e);
  }
}

async function loadTopics() {
  try {
    const res = await fetch('/api/keywords');
    const keywords = await res.json();
    const uniqueCats = [...new Set(keywords.map(k => k.category))];
    
    const container = document.getElementById('topicGrid');
    let html = `
      <div class="topic-card active" data-cat="hepsi" onclick="setTopicFilter('hepsi', 'Tüm Konular', '🌍')">
        <div class="topic-icon">🌍</div>
        <div class="topic-name">Tüm Konular</div>
      </div>
    `;
    
    const icons = {
      'makro_ekonomi': '📊',
      'ulasim_lojistik': '🚌',
      'gayrimenkul_insaat': '🏢',
      'ticaret_perakende': '🛒',
      'genel': '📌'
    };

    uniqueCats.forEach(cat => {
      const displayCat = cat.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      const icon = icons[cat] || '🏷️';
      html += `
        <div class="topic-card" data-cat="${cat}" onclick="setTopicFilter('${cat}', '${displayCat}', '${icon}')">
          <div class="topic-icon">${icon}</div>
          <div class="topic-name">${displayCat}</div>
        </div>
      `;
    });
    
    container.innerHTML = html;
  } catch(e) { console.error(e); }
}

// Scroll to Top Listener
window.addEventListener('scroll', () => {
  const btn = document.getElementById('scrollToTop');
  if (btn) {
    if (window.scrollY > 400) {
      btn.classList.add('visible');
    } else {
      btn.classList.remove('visible');
    }
  }
});

// Intersection Observer for Infinite Scroll
const observer = new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting) {
    loadMoreTweets();
  }
}, { rootMargin: '200px' });

document.addEventListener('DOMContentLoaded', () => {
  fetchStats();
  loadTopics();
  loadAIInsights();
  loadWeeklyTrend();
  
  // Gözlemci için sayfa sonuna gizli div ekle
  const listContainer = document.querySelector('.feed-section');
  const triggerDiv = document.createElement('div');
  triggerDiv.id = 'load-more-trigger';
  triggerDiv.style.height = '1px';
  listContainer.appendChild(triggerDiv);
  
  observer.observe(triggerDiv);
});
