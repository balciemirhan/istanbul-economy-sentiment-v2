/**
 * İstanbul Co-Pilot - AI Karar Destek Ajanı JS İletişim Motoru
 * Premium UI/UX, Çift Yönlü Ses Dalgası Görselleştiricileri ve Akıllı TTS desteği içerir.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elementleri
  const textarea = document.getElementById('copilotTextarea');
  const sendBtn = document.getElementById('copilotSendBtn');
  const voiceBtn = document.getElementById('copilotVoiceBtn');
  const btnClearChat = document.getElementById('btnClearChat');
  const speakerToggle = document.getElementById('copilotSpeakerToggle');
  const messagesContainer = document.getElementById('copilotMessagesContainer');
  const welcomeHub = document.getElementById('copilotWelcomeMessage');
  const suggestionsGrid = document.getElementById('copilotSuggestionsGrid');
  const chatBody = document.getElementById('copilotChatBody');
  const userSoundwave = document.getElementById('userSoundwave');

  // Durum Yönetimi
  let copilotHistory = [];
  let isRecordingVoice = false;
  let isSpeakerMuted = localStorage.getItem('copilot_speaker_muted') === 'true';
  let isSpacebarHolding = false;
  let voiceRecognitionInstance = null;
  let loadingInterval = null;
  let currentSpeakingElement = null;

  // Karşılama ekranının yedeğini al (temizleme işleminden sonra geri yüklemek için)
  const initialWelcomeHubHtml = welcomeHub ? welcomeHub.outerHTML : '';

  // 1. Hoparlör Ayarı Başlangıç Yüklemesi
  updateSpeakerToggleUI();

  // 2. Dinamik Başlangıç Sorgularını Çek ve Karşılama Ekranına Yerleştir
  loadCopilotSuggestions();

  // 3. Olay Dinleyicileri (Event Listeners)
  if (textarea) {
    // Textarea otomatik genişleme
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = (textarea.scrollHeight - 4) + 'px';
      
      // Yazı yazıldığında asistanın konuşmasını kes (Es verme özelliği)
      interruptAssistantSpeech();
    });

    // Enter ile gönderme (Shift+Enter alt satıra geçer)
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendCopilotMessage();
      }
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', sendCopilotMessage);
  }

  if (voiceBtn) {
    voiceBtn.addEventListener('click', toggleVoiceRecording);
  }

  if (speakerToggle) {
    speakerToggle.addEventListener('click', () => {
      isSpeakerMuted = !isSpeakerMuted;
      localStorage.setItem('copilot_speaker_muted', isSpeakerMuted);
      updateSpeakerToggleUI();
      
      if (isSpeakerMuted) {
        window.speechSynthesis.cancel();
        clearSpeakingVisuals();
      }
    });
  }

  if (btnClearChat) {
    btnClearChat.addEventListener('click', () => {
      // Sohbeti temizle
      messagesContainer.innerHTML = '';
      copilotHistory = [];
      window.speechSynthesis.cancel();
      clearSpeakingVisuals();
      
      // Karşılama ekranını geri getir
      const chatBodyEl = document.getElementById('copilotChatBody');
      if (chatBodyEl && initialWelcomeHubHtml) {
        // Eski karşılama ekranını kaldır (varsa)
        const oldWelcome = document.getElementById('copilotWelcomeMessage');
        if (oldWelcome) oldWelcome.remove();
        
        // Yenisini mesajların önüne ekle
        chatBodyEl.insertAdjacentHTML('afterbegin', initialWelcomeHubHtml);
        
        // Önerileri yeniden bağla ve yükle
        const newSuggestionsGrid = document.getElementById('copilotSuggestionsGrid');
        if (newSuggestionsGrid) {
          loadCopilotSuggestions();
        }
      }
    });
  }

  // --- SPACEBAR PUSH-TO-TALK (BAS-KONUŞ) KISAYOLU ---
  window.addEventListener('keydown', (e) => {
    const activeEl = document.activeElement;
    const isEditing = activeEl && (
      activeEl.tagName === 'INPUT' || 
      activeEl.tagName === 'TEXTAREA' || 
      activeEl.tagName === 'SELECT' || 
      activeEl.isContentEditable
    );
    
    if (e.code === 'Space' && !isEditing) {
      e.preventDefault(); // Sayfa kaymasını engelle
      
      if (e.repeat) return; // Sürekli tetiklenmeyi engelle
      
      isSpacebarHolding = true;
      interruptAssistantSpeech();
      
      if (!isRecordingVoice) {
        startVoiceRecording();
      }
    }
  });

  window.addEventListener('keyup', (e) => {
    if (e.code === 'Space' && isSpacebarHolding) {
      isSpacebarHolding = false;
      if (isRecordingVoice) {
        stopVoiceRecording();
      }
    }
  });

  // Kullanıcı herhangi bir tuşa bastığında asistan konuşuyorsa kes (Es verme / Kesme özelliği)
  window.addEventListener('keydown', (e) => {
    if (e.code !== 'Space') {
      interruptAssistantSpeech();
    }
  });

  // --- HOPARLÖR UI GÜNCELLEME ---
  function updateSpeakerToggleUI() {
    if (!speakerToggle) return;
    
    if (isSpeakerMuted) {
      speakerToggle.classList.remove('active');
      speakerToggle.title = "Sesli Yanıtı Aç";
      speakerToggle.innerHTML = `
        <svg class="speaker-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <line x1="23" y1="9" x2="17" y2="15"/>
          <line x1="17" y1="9" x2="23" y2="15"/>
        </svg>
      `;
    } else {
      speakerToggle.classList.add('active');
      speakerToggle.title = "Sesli Yanıtı Kapat";
      speakerToggle.innerHTML = `
        <svg class="speaker-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
        </svg>
      `;
    }
  }

  // --- DİNAMİK BAŞLANGIÇ SORGULARI YÜKLEYİCİ ---
  async function loadCopilotSuggestions() {
    const grid = document.getElementById('copilotSuggestionsGrid');
    if (!grid) return;
    
    try {
      const res = await fetch('/api/copilot/suggestions');
      const data = await res.json();
      
      if (data.suggestions && data.suggestions.length > 0) {
        grid.innerHTML = data.suggestions.map(sug => `
          <div class="suggestion-hub-card" onclick="selectCopilotSuggestion('${sug.replace(/'/g, "\\'")}')">
            <span>${sug}</span>
            <span class="card-arrow">➔</span>
          </div>
        `).join('');
      } else {
        grid.innerHTML = '<div class="suggestion-hub-cardloading">Veritabanı taranırken sorun oluştu. Alternatif vakalar bekleniyor...</div>';
      }
    } catch (err) {
      console.error("Dinamik Co-Pilot önerileri yüklenirken hata:", err);
      grid.innerHTML = '<div class="suggestion-hub-cardloading">Bağlantı hatası: Dinamik vakalar yüklenemedi.</div>';
    }
  }

  // Öneri kartı tıklama yöneticisi (global scope'a bağlanır)
  window.selectCopilotSuggestion = function(text) {
    interruptAssistantSpeech();
    
    if (textarea) {
      textarea.value = text;
      sendCopilotMessage();
    }
  };

  // --- SES TANIYAN MOTOR (Speech-to-Text) ---
  function startVoiceRecording() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Tarayıcınız ses tanıma (Speech-to-Text) özelliğini desteklemiyor. Lütfen Chrome, Edge veya Safari kullanın.");
      return;
    }

    interruptAssistantSpeech();

    isRecordingVoice = true;
    if (voiceBtn) voiceBtn.classList.add('recording');
    if (userSoundwave) userSoundwave.classList.add('active');

    voiceRecognitionInstance = new SpeechRecognition();
    voiceRecognitionInstance.lang = 'tr-TR';
    voiceRecognitionInstance.interimResults = false;
    voiceRecognitionInstance.maxAlternatives = 1;

    voiceRecognitionInstance.onresult = (event) => {
      const resultText = event.results[0][0].transcript;
      if (textarea && resultText) {
        textarea.value = resultText;
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight - 4) + 'px';
        
        // Otomatik gönderim tetikleme
        sendCopilotMessage();
      }
    };

    voiceRecognitionInstance.onspeechend = () => {
      stopRecordingUI();
    };

    voiceRecognitionInstance.onerror = (event) => {
      console.error("Ses tanıma hatası:", event.error);
      stopRecordingUI();
    };

    voiceRecognitionInstance.onend = () => {
      stopRecordingUI();
    };

    voiceRecognitionInstance.start();
  }

  function stopVoiceRecording() {
    if (voiceRecognitionInstance) {
      voiceRecognitionInstance.stop();
    }
    stopRecordingUI();
  }

  function toggleVoiceRecording() {
    if (isRecordingVoice) {
      stopVoiceRecording();
    } else {
      startVoiceRecording();
    }
  }

  function stopRecordingUI() {
    isRecordingVoice = false;
    if (voiceBtn) voiceBtn.classList.remove('recording');
    if (userSoundwave) userSoundwave.classList.remove('active');
  }

  // --- SIFIR SÜRTÜNMELİ SOHBET MOTORU ---
  async function sendCopilotMessage() {
    if (!textarea) return;
    const messageText = textarea.value.trim();
    if (!messageText) return;

    // Aktif asistan konuşmasını sonlandır
    interruptAssistantSpeech();

    // Giriş kutusu temizliği
    textarea.value = '';
    textarea.style.height = 'auto';

    // Karşılama ekranını kaldır
    const welcomeHubEl = document.getElementById('copilotWelcomeMessage');
    if (welcomeHubEl) welcomeHubEl.remove();

    // 1. Kullanıcı Mesajını Arayüze Ekle
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'copilot-msg user';
    userMsgDiv.innerHTML = `
      <div class="msg-avatar">Y</div>
      <div class="msg-bubble">${escapeHTML(messageText)}</div>
    `;
    messagesContainer.appendChild(userMsgDiv);
    scrollCopilotToBottom();

    // Geçmişe ekle
    copilotHistory.push({ role: 'user', content: messageText });

    // AI yükleme orbu animasyonunu başlat
    startLoadingTextAnimation();

    try {
      // 2. Sunucu API Çağrısı
      const response = await fetch('/api/copilot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          history: copilotHistory
        })
      });
      const data = await response.json();

      // Animasyonu kapat
      stopLoadingTextAnimation();

      if (data.error) {
        appendCopilotErrorMessage(data.error);
        return;
      }

      // Sohbet geçmişini güncelle
      copilotHistory.push({ role: 'assistant', content: data.response });

      // 3. Asistan Mesajını Hazırla
      const aiMsgDiv = document.createElement('div');
      aiMsgDiv.className = 'copilot-msg assistant';

      // Avatar
      const avatarDiv = document.createElement('div');
      avatarDiv.className = 'msg-avatar';
      avatarDiv.innerText = 'A';
      aiMsgDiv.appendChild(avatarDiv);

      // Bubble
      const bubbleDiv = document.createElement('div');
      bubbleDiv.className = 'msg-bubble';

      // Eylem planı var mı kontrol et yoksa normal formatla
      const actionPlanHtml = tryRenderActionPlan(data.response);
      if (actionPlanHtml) {
        bubbleDiv.innerHTML = actionPlanHtml;
      } else {
        bubbleDiv.innerHTML = formatAssistantMessage(data.response);
      }

      // Asistan ses dalgası görselini ve Sustur butonunu içeren kontrol panelini ekle
      const assistantWaveHtml = `
        <div class="assistant-voice-controls">
          <div class="assistant-soundwave-inline" style="display: none;">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
          <button type="button" class="stop-tts-btn" title="Seslendirmeyi Durdur">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
            </svg>
            <span>Sustur</span>
          </button>
        </div>
      `;
      bubbleDiv.insertAdjacentHTML('beforeend', assistantWaveHtml);
      aiMsgDiv.appendChild(bubbleDiv);

      // 4. Grafik (Chart.js) Desteği
      if (data.chart_data && Object.keys(data.chart_data).length > 0) {
        const canvasId = `copilot-chart-${Date.now()}`;
        const chartContainer = document.createElement('div');
        chartContainer.className = 'copilot-embedded-chart';
        chartContainer.style.height = '240px';
        chartContainer.style.marginTop = '16px';
        chartContainer.innerHTML = `<canvas id="${canvasId}"></canvas>`;
        bubbleDiv.appendChild(chartContainer);
        
        messagesContainer.appendChild(aiMsgDiv);
        scrollCopilotToBottom();
        
        setTimeout(() => renderEmbeddedChart(canvasId, data.chart_data), 100);
      } else {
        messagesContainer.appendChild(aiMsgDiv);
        scrollCopilotToBottom();
      }

      // --- OTOMATİK TÜRKÇE SESLENDİRME VE GÖRSEL DALGA ENTEGRASYONU ---
      speakText(data.response, aiMsgDiv);

    } catch (err) {
      console.error("Co-Pilot bağlantı hatası:", err);
      stopLoadingTextAnimation();
      appendCopilotErrorMessage("Bağlantı hatası: Yapay Zeka sunucusu ile iletişim kurulamadı.");
    }
  }

  function appendCopilotErrorMessage(errorText) {
    const errDiv = document.createElement('div');
    errDiv.className = 'copilot-msg assistant';
    errDiv.innerHTML = `
      <div class="msg-avatar" style="background: var(--negative);">⚠️</div>
      <div class="msg-bubble" style="color: var(--negative);">🤖 Bir hata oluştu: ${escapeHTML(errorText)}</div>
    `;
    messagesContainer.appendChild(errDiv);
    scrollCopilotToBottom();
  }

  function scrollCopilotToBottom() {
    if (chatBody) {
      chatBody.scrollTop = chatBody.scrollHeight;
    }
  }

  // --- EMBEDDED CHART.JS YANSITMA MOTORU ---
  function renderEmbeddedChart(canvasId, chartData) {
    const ctxEl = document.getElementById(canvasId);
    if (!ctxEl) return;

    const customColors = ['#10b981', '#ef4444', '#f59e0b', '#6366f1', '#a855f7'];
    const isPieOrDoughnut = chartData.type === 'pie' || chartData.type === 'doughnut';

    new Chart(ctxEl.getContext('2d'), {
      type: chartData.type || 'bar',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: chartData.title || 'Ekonomik Dağılım',
          data: chartData.data,
          backgroundColor: isPieOrDoughnut ? customColors.slice(0, chartData.labels.length) : 'rgba(99, 102, 241, 0.7)',
          borderColor: '#0f172a',
          borderWidth: 2,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: isPieOrDoughnut,
            position: 'bottom',
            labels: {
              color: '#94a3b8',
              font: { family: 'Outfit', size: 10 },
              padding: 10
            }
          },
          tooltip: {
            backgroundColor: '#1e293b',
            titleColor: '#e2e8f0',
            bodyColor: '#94a3b8',
            borderColor: 'rgba(255,255,255,0.05)',
            borderWidth: 1
          }
        },
        scales: isPieOrDoughnut ? {} : {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.02)' },
            ticks: { color: '#64748b', font: { size: 10 } }
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#64748b', font: { size: 10 }, stepSize: 1 }
          }
        }
      }
    });
  }

  // --- MARKDOWN & BİÇİMLENDİRME PARSER ---
  function formatAssistantMessage(text) {
    if (!text) return "";
    
    const lines = text.split('\n');
    let html = [];
    let inList = false;
    let inNumList = false;
    let inTable = false;
    let tableHeaders = null;
    let tableRows = [];
    let inCodeBlock = false;
    let codeBlockContent = [];
    let codeLanguage = '';

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      let trimmed = line.trim();

      // Code blocks
      if (trimmed.startsWith('```')) {
        if (inCodeBlock) {
          // Close code block
          html.push(`<pre class="msg-code-block"><div class="code-block-header">${codeLanguage || 'code'}</div><code class="code-block-content">${escapeHTML(codeBlockContent.join('\n'))}</code></pre>`);
          inCodeBlock = false;
          codeBlockContent = [];
        } else {
          // Open code block
          inCodeBlock = true;
          codeLanguage = trimmed.substring(3).trim();
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      // Tables
      if (trimmed.startsWith('|') && trimmed.length > 2) {
        // If we are in lists, close them
        if (inList) { html.push('</ul>'); inList = false; }
        if (inNumList) { html.push('</ol>'); inNumList = false; }

        let cells = trimmed.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
        
        // Check if it's separator line (e.g. |---|---|)
        let isSeparator = cells.every(c => /^:-*|-+:?|:-+:?|-+$/.test(c));
        
        if (isSeparator) {
          // Skip separator line
          continue;
        }

        if (!inTable) {
          inTable = true;
          tableHeaders = cells;
          tableRows = [];
        } else {
          tableRows.push(cells);
        }
        continue;
      } else {
        if (inTable) {
          // Table ended
          html.push(renderHTMLTable(tableHeaders, tableRows));
          inTable = false;
          tableHeaders = null;
          tableRows = [];
        }
      }

      // Headings
      if (trimmed.startsWith('#')) {
        if (inList) { html.push('</ul>'); inList = false; }
        if (inNumList) { html.push('</ol>'); inNumList = false; }
        
        let level = 0;
        while (trimmed.charAt(level) === '#') {
          level++;
        }
        let headingText = trimmed.substring(level).trim();
        let tag = level <= 2 ? 'h3' : 'h4';
        let cls = level <= 2 ? 'msg-h3' : 'msg-h4';
        html.push(`<${tag} class="${cls}">${formatInlineMarkdown(headingText)}</${tag}>`);
        continue;
      }

      // Lists
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
        if (inNumList) { html.push('</ol>'); inNumList = false; }
        if (!inList) {
          html.push('<ul class="msg-list">');
          inList = true;
        }
        let content = trimmed.replace(/^[-*•]\s+/, '');
        html.push(`<li>${formatInlineMarkdown(content)}</li>`);
        continue;
      } else {
        if (inList) {
          html.push('</ul>');
          inList = false;
        }
      }

      // Numbered Lists
      if (/^\d+\.\s+/.test(trimmed)) {
        if (inList) { html.push('</ul>'); inList = false; }
        if (!inNumList) {
          html.push('<ol class="msg-num-list">');
          inNumList = true;
        }
        let content = trimmed.replace(/^\d+\.\s+/, '');
        html.push(`<li>${formatInlineMarkdown(content)}</li>`);
        continue;
      } else {
        if (inNumList) {
          html.push('</ol>');
          inNumList = false;
        }
      }

      // Plain paragraphs
      if (trimmed) {
        html.push(`<p class="msg-para">${formatInlineMarkdown(trimmed)}</p>`);
      }
    }

    // Close any unclosed tags
    if (inCodeBlock) {
      html.push(`<pre class="msg-code-block"><code class="code-block-content">${escapeHTML(codeBlockContent.join('\n'))}</code></pre>`);
    }
    if (inTable) {
      html.push(renderHTMLTable(tableHeaders, tableRows));
    }
    if (inList) {
      html.push('</ul>');
    }
    if (inNumList) {
      html.push('</ol>');
    }

    return html.join('');
  }

  function formatInlineMarkdown(text) {
    let safe = escapeHTML(text);
    // Bold
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Inline code
    safe = safe.replace(/`(.*?)`/g, '<code class="inline-code">$1</code>');
    return safe;
  }

  function renderHTMLTable(headers, rows) {
    let html = ['<div class="table-container"><table class="msg-table">'];
    if (headers) {
      html.push('<thead><tr>');
      headers.forEach(h => {
        html.push(`<th>${formatInlineMarkdown(h)}</th>`);
      });
      html.push('</tr></thead>');
    }
    if (rows && rows.length > 0) {
      html.push('<tbody>');
      rows.forEach(r => {
        html.push('<tr>');
        r.forEach(cell => {
          html.push(`<td>${formatInlineMarkdown(cell)}</td>`);
        });
        html.push('</tr>');
      });
      html.push('</tbody>');
    }
    html.push('</table></div>');
    return html.join('');
  }

  // Kısa/Orta/Uzun vadeli Karar Destek eylem planı ayrıştırıcı
  function tryRenderActionPlan(text) {
    const hasKisa = text.includes("Kısa Vadeli");
    const hasOrta = text.includes("Orta Vadeli");
    const hasUzun = text.includes("Uzun Vadeli");
    
    if (hasKisa || hasOrta || hasUzun) {
      let html = '<div class="copilot-action-plan" style="display: flex; flex-direction: column; gap: 16px; margin-top: 10px;">';
      
      const extractSection = (titleKeyword) => {
        const lines = text.split('\n');
        let collected = [];
        let found = false;
        
        for (let line of lines) {
          const trimmed = line.trim();
          if (trimmed.toLowerCase().includes(titleKeyword.toLowerCase()) && 
              (trimmed.includes("Acil") || trimmed.includes("Düzenleme") || trimmed.includes("Stratejik") || trimmed.includes("Vadeli"))) {
            found = true;
            collected.push(trimmed);
            continue;
          }
          
          if (found) {
            if ((trimmed.includes("Kısa Vadeli") || trimmed.includes("Orta Vadeli") || trimmed.includes("Uzun Vadeli")) && 
                !trimmed.toLowerCase().includes(titleKeyword.toLowerCase())) {
              break;
            }
            collected.push(trimmed);
          }
        }
        
        if (collected.length > 0) {
          collected.shift();
          return collected.join('\n');
        }
        return "";
      };
      
      if (hasKisa) {
        const kisaText = extractSection("Kısa Vadeli");
        if (kisaText) {
          html += `
            <div class="action-card kisa">
              <div class="action-card-header">🎯 Kısa Vadeli Acil Aksiyonlar</div>
              <div class="action-card-body">${formatAssistantMessage(kisaText)}</div>
            </div>
          `;
        }
      }
      
      if (hasOrta) {
        const ortaText = extractSection("Orta Vadeli");
        if (ortaText) {
          html += `
            <div class="action-card orta">
              <div class="action-card-header">⚙️ Orta Vadeli Düzenlemeler</div>
              <div class="action-card-body">${formatAssistantMessage(ortaText)}</div>
            </div>
          `;
        }
      }
      
      if (hasUzun) {
        const uzunText = extractSection("Uzun Vadeli");
        if (uzunText) {
          html += `
            <div class="action-card uzun">
              <div class="action-card-header">🏛️ Uzun Vadeli Stratejik Yatırımlar</div>
              <div class="action-card-body">${formatAssistantMessage(uzunText)}</div>
            </div>
          `;
        }
      }
      
      html += '</div>';
      return html;
    }
    return null;
  }

  // --- DİNAMİK CO-PILOT ORB YÜKLEME SÜRECİ ---
  function startLoadingTextAnimation() {
    const indicator = document.getElementById('copilotTypingIndicator');
    const text = document.getElementById('copilotThinkingText');
    const subtext = document.getElementById('copilotThinkingSubtext');

    if (!indicator || !text || !subtext) return;

    text.innerText = "Yapay Zeka düşünüyor...";
    subtext.innerText = "BERT modeli & veritabanı analiz ediliyor";
    indicator.style.display = "flex";
    scrollCopilotToBottom();

    if (loadingInterval) clearInterval(loadingInterval);

    let step = 0;
    loadingInterval = setInterval(() => {
      step++;
      if (step === 1) {
        text.innerText = "Veritabanı taranıyor...";
        subtext.innerText = "SQLite sentiment verileri ve ironi durumları taranıyor";
      } else if (step === 2) {
        text.innerText = "Etkileşimli haritalar & grafikler çiziliyor...";
        subtext.innerText = "Chart.js interaktif grafik yapısı hazırlanıyor";
      } else if (step === 3) {
        text.innerText = "Karar destek modeli çalıştırılıyor...";
        subtext.innerText = "Kısa, orta ve uzun vadeli eylem kartları sentezleniyor";
      } else if (step >= 4) {
        text.innerText = "Yanıt oluşturuluyor ve seslendiriliyor...";
        subtext.innerText = "Sentezleyici ses çıktısını derliyor";
      }
      scrollCopilotToBottom();
    }, 3000);
  }

  function stopLoadingTextAnimation() {
    if (loadingInterval) {
      clearInterval(loadingInterval);
      loadingInterval = null;
    }
    const indicator = document.getElementById('copilotTypingIndicator');
    if (indicator) {
      indicator.style.display = "none";
    }
  }

  // --- AKILLI TTS METİN TEMİZLEYİCİ VE YARDIMCI METODLARI ---
  function cleanTextForTTS(text) {
    if (!text) return "";
    let cleaned = text;
    cleaned = cleaned.replace(/grafi[ğg]i yans[ıi]t[ıi]yorum/gi, "");
    cleaned = cleaned.replace(/<[^>]*>/g, " ");
    cleaned = cleaned.replace(/\*\*/g, "");
    cleaned = cleaned.replace(/\*/g, "");
    cleaned = cleaned.replace(/^- /gm, "");
    cleaned = cleaned.replace(/^#+ /gm, "");
    cleaned = cleaned.replace(/https?:\/\/\S+/gi, "");
    cleaned = cleaned.replace(/\s+/g, " ").trim();
    return cleaned;
  }

  function speakText(text, aiMessageElement) {
    if (isSpeakerMuted) return;

    window.speechSynthesis.cancel();
    clearSpeakingVisuals();

    const cleanText = cleanTextForTTS(text);
    if (!cleanText) return;

    // Sustur butonu dinleyicisi
    const stopTtsBtn = aiMessageElement ? aiMessageElement.querySelector('.stop-tts-btn') : null;
    if (stopTtsBtn) {
      stopTtsBtn.onclick = (e) => {
        e.stopPropagation();
        interruptAssistantSpeech();
      };
    }

    // Balonun kendisine tıklandığında susturma dinleyicisi
    if (aiMessageElement) {
      aiMessageElement.onclick = () => {
        if (aiMessageElement.classList.contains('speaking')) {
          interruptAssistantSpeech();
        }
      };
    }

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'tr-TR';

    // Türkçe ses ayarla
    const voices = window.speechSynthesis.getVoices();
    const trVoice = voices.find(v => v.lang.includes('tr-TR') || v.lang.includes('tr_TR'));
    if (trVoice) {
      utterance.voice = trVoice;
    }

    currentSpeakingElement = aiMessageElement;
    const waveEl = aiMessageElement ? aiMessageElement.querySelector('.assistant-soundwave-inline') : null;

    utterance.onstart = () => {
      if (aiMessageElement) {
        aiMessageElement.classList.add('speaking');
      }
      if (waveEl) {
        waveEl.style.display = 'inline-flex';
      }
    };

    utterance.onend = () => {
      if (aiMessageElement) {
        aiMessageElement.classList.remove('speaking');
      }
      if (waveEl) {
        waveEl.style.display = 'none';
      }
      currentSpeakingElement = null;
    };

    utterance.onerror = () => {
      if (aiMessageElement) {
        aiMessageElement.classList.remove('speaking');
      }
      if (waveEl) {
        waveEl.style.display = 'none';
      }
      currentSpeakingElement = null;
    };

    window.speechSynthesis.speak(utterance);
  }

  function interruptAssistantSpeech() {
    window.speechSynthesis.cancel();
    clearSpeakingVisuals();
  }

  function clearSpeakingVisuals() {
    if (currentSpeakingElement) {
      currentSpeakingElement.classList.remove('speaking');
      const waveEl = currentSpeakingElement.querySelector('.assistant-soundwave-inline');
      if (waveEl) waveEl.style.display = 'none';
      currentSpeakingElement = null;
    }
    // Tüm mesajlardaki speaking durumlarını sıfırla (garantiye almak için)
    document.querySelectorAll('.copilot-msg.assistant').forEach(el => {
      el.classList.remove('speaking');
      const wave = el.querySelector('.assistant-soundwave-inline');
      if (wave) wave.style.display = 'none';
    });
  }

  function escapeHTML(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
