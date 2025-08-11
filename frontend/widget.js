// Longopass AI widget (simple)
(function () {
  const API_BASE = (window.LONGOPASS_AI_BASE || "https://ai.longopass.com"); // set to your gateway host
  let conversationId = null;
  let plan = window.LONGOPASS_PLAN || "free";
  let userId = window.LONGOPASS_USER_ID || null;

  // --- UI ---
  const style = document.createElement('style');
  style.textContent = `
    .lp-ai-button{position:fixed;right:20px;bottom:20px;background:#0ea5e9;color:#fff;border:none;border-radius:999px;padding:12px 16px;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.15);z-index:999999}
    .lp-ai-window{position:fixed;right:20px;bottom:70px;width:360px;max-width:90vw;height:480px;background:#fff;border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.2);display:none;flex-direction:column;overflow:hidden;z-index:999999}
    .lp-ai-header{padding:10px 12px;background:#0369a1;color:#fff;font-weight:600;display:flex;justify-content:space-between;align-items:center}
    .lp-ai-body{padding:10px;height:100%;overflow:auto;background:#f8fafc}
    .lp-ai-input{display:flex;border-top:1px solid #e5e7eb}
    .lp-ai-input input{flex:1;border:none;padding:10px;outline:none}
    .lp-ai-input button{border:none;background:#0ea5e9;color:#fff;padding:10px 14px;cursor:pointer}
    .lp-msg{margin:6px 0;padding:8px 10px;border-radius:10px;max-width:80%}
    .lp-user{background:#dbeafe;margin-left:auto}
    .lp-bot{background:#e2e8f0}
  `;
  document.head.appendChild(style);

  const btn = document.createElement('button');
  btn.className = 'lp-ai-button';
  btn.innerText = 'Longopass AI';
  document.body.appendChild(btn);

  const win = document.createElement('div');
  win.className = 'lp-ai-window';
  win.innerHTML = `
    <div class="lp-ai-header">
      <span>Longopass AI</span>
      <span id="lp-close" style="cursor:pointer;">✕</span>
    </div>
    <div class="lp-ai-body" id="lp-body"></div>
    <div class="lp-ai-input">
      <input id="lp-input" placeholder="Sağlıkla ilgili bir şey sor..." />
      <button id="lp-send">Gönder</button>
    </div>
  `;
  document.body.appendChild(win);

  const body = () => document.getElementById('lp-body');
  const input = () => document.getElementById('lp-input');

  function addMsg(role, text) {
    const div = document.createElement('div');
    div.className = 'lp-msg ' + (role === 'user' ? 'lp-user' : 'lp-bot');
    div.textContent = text;
    body().appendChild(div);
    body().scrollTop = body().scrollHeight;
  }

  async function startConversation() {
    const res = await fetch(`${API_BASE}/ai/chat/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId || '',
        'X-User-Plan': plan
      },
      body: JSON.stringify({})
    });
    if (res.status === 403) {
      addMsg('assistant','Chat yalnızca premium kullanıcılar için kullanılabilir.');
      return null;
    }
    const j = await res.json();
    return j.conversation_id;
  }

  async function sendMessage(text) {
    if (!conversationId) {
      conversationId = await startConversation();
      if (!conversationId) return;
    }
    addMsg('user', text);
    const res = await fetch(`${API_BASE}/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId || '',
        'X-User-Plan': plan
      },
      body: JSON.stringify({ conversation_id: conversationId, text })
    });
    const j = await res.json();
    if (res.status !== 200) {
      addMsg('assistant', j.detail || 'Bir hata oluştu.');
      return;
    }
    addMsg('assistant', j.reply);
  }

  document.getElementById('lp-close').onclick = () => { win.style.display = 'none'; };
  btn.onclick = async () => {
    win.style.display = (win.style.display === 'flex' ? 'none' : 'flex');
    win.style.display = 'flex';
    if (plan !== 'premium') {
      body().innerHTML = '';
      addMsg('assistant','Chat yalnızca premium kullanıcılar için. Lütfen hesabınızı yükseltin.');
    } else {
      if (!conversationId) { conversationId = await startConversation(); }
    }
  };
  document.getElementById('lp-send').onclick = async () => {
    const t = input().value.trim();
    if (!t) return;
    input().value = '';
    await sendMessage(t);
  };

  // Hook buttons for analyze
  async function callAnalyze(endpoint, data) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId || '',
        'X-User-Plan': plan
      },
      body: JSON.stringify(data)
    });
    const j = await res.json();
    if (res.status !== 200) {
      alert(j.detail || 'Hata');
      return;
    }
    const recs = (j.recommendations || []).map(r => `• ${r.name}: ${r.reason}`).join('\n');
    alert(`AI Önerileri:\n${recs || '(boş)'}\n\nUyarı: ${j.disclaimer || ''}`);
  }

  const quizBtn = document.getElementById('lp-ai-quiz-btn');
  if (quizBtn) {
    quizBtn.addEventListener('click', async () => {
      // TODO: Sayfadaki quiz verisini DOM'dan topla
      const fakeQuiz = { answers: "Kullanıcının quiz cevapları burada..." };
      await callAnalyze('/ai/quiz', { payload: fakeQuiz });
    });
  }
  const labBtn = document.getElementById('lp-ai-lab-btn');
  if (labBtn) {
    labBtn.addEventListener('click', async () => {
      // TODO: Sayfadaki lab verisini DOM'dan oku
      const fakeLab = { results: [{ test: "Glukoz", value: 160, unit: "mg/dL" }] };
      await callAnalyze('/ai/lab/analyze', fakeLab);
    });
  }

  // --- Public API + Custom Events ---
  async function openWidget() {
    win.style.display = 'flex';
    if (plan === 'premium' && !conversationId) {
      conversationId = await startConversation();
    }
  }
  function closeWidget() { win.style.display = 'none'; }
  function setPlan(p) { plan = p || 'free'; }
  function setUserId(id) { userId = id || null; }
  async function quiz(payload) { return callAnalyze('/ai/quiz', { payload }); }
  async function lab(results) { return callAnalyze('/ai/lab/analyze', { results }); }
  async function send(t) { return sendMessage(t); }

  window.LongopassAI = {
    open: openWidget,
    close: closeWidget,
    send,
    quiz,
    lab,
    setPlan,
    setUserId
  };

  // Allow triggering via CustomEvent without DOM IDs
  window.addEventListener('lp-ai-quiz', (e) => {
    const detail = (e && e.detail) || {};
    callAnalyze('/ai/quiz', { payload: detail });
  });
  window.addEventListener('lp-ai-lab', (e) => {
    const detail = (e && e.detail) || [];
    callAnalyze('/ai/lab/analyze', { results: detail });
  });

})();