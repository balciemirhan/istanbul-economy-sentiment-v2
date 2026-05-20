
  let statusInterval = null;
  let countdownInterval = null;
  let countdownValue = 10;

  async function loadData() {
    loadUsage();
    loadKeywords();
    checkStatus(); // Eğer arkaplanda çalışan işlem varsa onu da yakalar
  }

  async function loadUsage() {
    try {
      const res = await fetch('/api/usage');
      const data = await res.json();
      document.getElementById('usage-text').innerText = `${data.used.toLocaleString()} / ${data.limit.toLocaleString()}`;
      document.getElementById('usage-helper-text').innerText = `*X API hesabınızın aylık limiti ${data.limit.toLocaleString()} tweet'tir.`;
      document.getElementById('usage-fill').style.width = `${data.percentage}%`;
      if (data.percentage > 80) document.getElementById('usage-fill').style.background = 'var(--negative)';
    } catch(e) { console.error(e); }
  }

  async function loadKeywords() {
    try {
      const res = await fetch('/api/keywords');
      const keywords = await res.json();
      // Kategorilere göre grupla
      const categories = {};
      keywords.forEach(k => {
        if (!categories[k.category]) categories[k.category] = [];
        categories[k.category].push(k);
      });

      const list = document.getElementById('keywordList');
      list.innerHTML = '';
      
      for (const [cat, kws] of Object.entries(categories)) {
        // Bu kategori için API'ye gidecek gerçek sorgu uzunluğunu hesapla
        const words = kws.map(k => k.word);
        const queryStr = '(istanbul OR i̇stanbul) (' + words.join(' OR ') + ') lang:tr -is:retweet -is:nullcast';
        const qLen = queryStr.length;
        
        let limitColor = 'var(--text-dim)';
        let limitWarning = '';
        let barColor = 'var(--accent)';
        
        if (qLen > 512) {
            limitColor = 'var(--negative)';
            barColor = 'var(--negative)';
            limitWarning = ' ⚠️';
        } else if (qLen > 450) {
            limitColor = 'orange';
            barColor = 'orange';
        }

        const qPct = Math.min(100, Math.round((qLen / 512) * 100));
        let displayCat = cat.replace('_', ' ').toUpperCase();
        
        let catHtml = `<div style="margin-bottom: 20px; width: 100%;">`;
        
        catHtml += `
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <h4 style="color: var(--accent); font-size: 13px; letter-spacing: 0.5px; margin: 0;">🏷️ ${displayCat}</h4>
                <span style="color: ${limitColor}; font-size: 11px; font-family: 'JetBrains Mono', monospace;">${qLen}/512${limitWarning}</span>
            </div>
            <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; overflow: hidden;">
                <div style="height: 100%; width: ${qPct}%; background: ${barColor}; transition: width 0.5s ease;"></div>
            </div>
        </div>`;
        
        catHtml += `<div class="tag-container" style="margin-bottom: 0;">`;
        catHtml += kws.map(k => `
          <div class="tag">
            ${k.word}
            <button onclick="deleteKeyword(${k.id})">×</button>
          </div>
        `).join('');
        catHtml += `</div></div>`;
        list.innerHTML += catHtml;
      }

      // Benzersiz kategorileri bulup datalist'e ekle
      const uniqueCats = Object.keys(categories);
      const dataList = document.getElementById('catList');
      dataList.innerHTML = uniqueCats.map(cat => `<option value="${cat}">`).join('');

    } catch(e) { console.error(e); }
  }

  async function addKeyword() {
    const word = document.getElementById('newKw').value.trim();
    let cat = document.getElementById('newCat').value.trim();
    
    // Kategori adını otomatik olarak temizle (örneğin: "Teknoloji Marketi" -> "teknoloji_marketi")
    if (cat) {
      cat = cat.toLowerCase().replace(/\s+/g, '_');
    } else {
      cat = 'genel';
    }
    
    if(!word) return;

    try {
      await fetch('/api/keywords', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word: word, category: cat})
      });
      document.getElementById('newKw').value = '';
      document.getElementById('newCat').value = '';
      loadKeywords();
    } catch(e) { alert("Eklenemedi"); }
  }

  async function deleteKeyword(id) {
    if(!confirm("Silmek istediğinize emin misiniz?")) return;
    try {
      await fetch(`/api/keywords/${id}`, { method: 'DELETE' });
      loadKeywords();
    } catch(e) { console.error(e); }
  }

  // --- Modal & Countdown Mantığı ---
  function showFetchModal() {
    document.getElementById('fetchModal').style.display = 'flex';
    countdownValue = 10;
    document.getElementById('countdownTimer').innerText = countdownValue;
    
    countdownInterval = setInterval(() => {
      countdownValue--;
      document.getElementById('countdownTimer').innerText = countdownValue;
      if(countdownValue <= 0) {
        clearInterval(countdownInterval);
        executeFetch();
      }
    }, 1000);
  }

  function cancelFetch() {
    clearInterval(countdownInterval);
    document.getElementById('fetchModal').style.display = 'none';
  }

  async function executeFetch() {
    clearInterval(countdownInterval);
    document.getElementById('fetchModal').style.display = 'none';
    
    const maxTweets = document.getElementById('inputMaxTweets').value;
    const days = document.getElementById('inputDays').value;
    
    try {
      const res = await fetch('/api/fetch-data', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_tweets: parseInt(maxTweets), days: parseInt(days) })
      });
      const data = await res.json();
      if(data.success) {
        startTracking();
      } else {
        alert(data.error);
      }
    } catch(e) { alert("Başlatılamadı"); }
  }

  function startTracking() {
    document.getElementById('fetchText').style.display = 'none';
    document.getElementById('fetchLoader').style.display = 'block';
    document.getElementById('fetchBtn').disabled = true;
    
    statusInterval = setInterval(checkStatus, 1000);
  }

  async function checkStatus() {
    try {
      const res = await fetch('/api/fetch-status');
      const data = await res.json();
      
      const logBox = document.getElementById('logBox');
      logBox.innerHTML = data.logs.map(log => {
        let cls = "info";
        if (log.includes("Hata") || log.includes("Error")) cls = "error";
        return `<p class="${cls}">> ${log}</p>`;
      }).join('');
      
      logBox.scrollTop = logBox.scrollHeight;

      if(data.is_running) {
        document.getElementById('fetchText').style.display = 'none';
        document.getElementById('fetchLoader').style.display = 'block';
        document.getElementById('fetchBtn').disabled = true;
      } else {
        // Eğer durduysa (ve daha önce çalışıyor olduğunu biliyorsak)
          if (statusInterval) {
          clearInterval(statusInterval);
          statusInterval = null;
          document.getElementById('fetchText').style.display = 'block';
          document.getElementById('fetchLoader').style.display = 'none';
          document.getElementById('fetchBtn').disabled = false;
          
          const logsText = data.logs.join(" ");
          if (logsText.includes("kotaya ulaşıldı") || logsText.includes("bulunamadı") || logsText.includes("Hata")) {
            // alert("⚠️ İşlem tamamlandı ancak veri çekilemedi...");
            document.getElementById('errorModal').style.display = 'flex';
          } else {
            // alert("✅ İşlem başarıyla tamamlandı...");
            document.getElementById('successModal').style.display = 'flex';
            setTimeout(() => {
                window.location.href = '/'; 
            }, 2500); // 2.5 saniye animasyon izletip yönlendir
          }
        }
      }
    } catch(e) { console.error(e); }
  }

  // Sayfa yüklendiğinde çalıştır
  loadData();
