// ═══════════════════════════════════════
//  mrAvzal Donation — main.js
//  Frontend → Python backend API ga ulangan
// ═══════════════════════════════════════

const CARD_NUMBER_PLAIN   = '4231200015619835';
const CARD_NUMBER_DISPLAY = '4231 2000 1561 9835';
const AUTO_DELETE_MS      = 10 * 60 * 1000;

let currentLang     = 'uz';
let currentCurrency = 'UZS';
let pendingDonation = null;

// ── LANG ──────────────────────────────
function setLang(lang) {
  currentLang = lang;
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.lang-btn[data-lang="${lang}"]`).classList.add('active');
  document.querySelectorAll('[data-uz]').forEach(el => {
    if (['INPUT', 'TEXTAREA'].includes(el.tagName)) return;
    el.textContent = el.dataset[lang] || el.dataset.uz;
  });
  updateBtn();
}

// ── CURRENCY ──────────────────────────
function setCurrency(cur) {
  currentCurrency = cur;
  document.getElementById('cur-uzs').classList.toggle('active', cur === 'UZS');
  document.getElementById('cur-usd').classList.toggle('active', cur === 'USD');
  document.getElementById('cur-symbol').textContent = cur;
  document.getElementById('card-cur-show').textContent = cur;
  document.getElementById('amount').value = '';
  updateBtn();
}

// ── AMOUNT → BUTTON ───────────────────
function updateBtn() {
  const val = parseFloat(document.getElementById('amount').value);
  const btn = document.getElementById('donate-btn');
  const txt = document.getElementById('btn-text');
  const min = currentCurrency === 'UZS' ? 1000 : 0.5;

  if (val && val >= min) {
    btn.disabled = false;
    const fmt = currentCurrency === 'UZS'
      ? val.toLocaleString('uz-UZ') : val.toFixed(2);
    txt.textContent = currentLang === 'uz'
      ? `${currentCurrency} ${fmt} — To'lov →`
      : `Pay ${currentCurrency} ${fmt} →`;
  } else {
    btn.disabled = true;
    txt.textContent = currentLang === 'uz' ? 'Summa kiriting' : 'Enter an amount';
  }
}

// ── OPEN PAYMENT MODAL ─────────────────
function openPayment() {
  const val  = parseFloat(document.getElementById('amount').value);
  const name = document.getElementById('donor-name').value.trim() || 'Anonymous';
  if (!val) return;

  pendingDonation = { amount: val, currency: currentCurrency, name };
  const fmt = currentCurrency === 'UZS'
    ? val.toLocaleString('uz-UZ') : val.toFixed(2);
  document.getElementById('modal-amount').textContent = `${currentCurrency} ${fmt}`;

  // Step 1 ga qaytarish
  document.getElementById('step1-box').classList.remove('hidden');
  document.getElementById('step2-box').classList.remove('show');
  document.getElementById('si-1').className = 'step active';
  document.getElementById('sn-1').textContent = '1';
  document.getElementById('si-2').className = 'step';
  document.getElementById('modal-bg').classList.add('show');
}

function closeModal() { document.getElementById('modal-bg').classList.remove('show'); }
function closeModalBg(e) { if (e.target === document.getElementById('modal-bg')) closeModal(); }

// ── COPY CARD ─────────────────────────
function copyCard() {
  navigator.clipboard.writeText(CARD_NUMBER_PLAIN).then(() => {
    const btn = document.getElementById('copy-btn');
    btn.classList.add('copied');
    document.getElementById('copy-icon').textContent = '✓';
    document.getElementById('copy-text').textContent =
      currentLang === 'uz' ? 'Nusxalandi!' : 'Copied!';
    setTimeout(() => {
      btn.classList.remove('copied');
      document.getElementById('copy-icon').textContent = '📋';
      document.getElementById('copy-text').textContent =
        currentLang === 'uz' ? 'Karta raqamini nusxalash' : 'Copy card number';
    }, 2500);
  });
}

// ── STEP 1 → STEP 2 ───────────────────
function goToStep2() {
  document.getElementById('step1-box').classList.add('hidden');
  document.getElementById('step2-box').classList.add('show');
  document.getElementById('si-1').className = 'step done';
  document.getElementById('sn-1').textContent = '✓';
  document.getElementById('si-2').className = 'step active';
  document.getElementById('donor-msg').value = '';
}

// ── SUBMIT / SKIP MESSAGE ─────────────
function submitMessage() {
  saveAndFinish(document.getElementById('donor-msg').value.trim());
}
function skipMessage() { saveAndFinish(''); }

async function saveAndFinish(msg) {
  if (!pendingDonation) return;
  const { amount, currency, name } = pendingDonation;

  try {
    const res = await fetch('/api/donations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, amount, currency, message: msg })
    });
    if (!res.ok) throw new Error('API xatosi');
  } catch (e) {
    // Backend ishlamasa localStorage ga yozadi
    const local = JSON.parse(localStorage.getItem('d_fallback') || '[]');
    local.unshift({
      id: Date.now().toString(), name, amount, currency, message: msg,
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + AUTO_DELETE_MS).toISOString()
    });
    localStorage.setItem('d_fallback', JSON.stringify(local));
    showToast(currentLang === 'uz' ? '⚠️ Offline rejim' : '⚠️ Offline mode');
  }

  closeModal();

  // Success ekrani — o'chirilishi haqida hech narsa yozilmaydi
  document.getElementById('main-wrap').style.display = 'none';
  document.getElementById('success-wrap').classList.add('show');
  const fmt = currency === 'UZS'
    ? amount.toLocaleString('uz-UZ') : amount.toFixed(2);
  document.getElementById('success-msg').textContent = currentLang === 'uz'
    ? `${name}, ${currency} ${fmt} uchun katta rahmat! 🙏`
    : `${name}, thank you for ${currency} ${fmt}! 🙏`;

  document.querySelectorAll('[data-uz]').forEach(el => {
    if (['INPUT', 'TEXTAREA'].includes(el.tagName)) return;
    el.textContent = el.dataset[currentLang] || el.dataset.uz;
  });
}

function goBack() {
  document.getElementById('success-wrap').classList.remove('show');
  document.getElementById('main-wrap').style.display = 'flex';
  document.getElementById('amount').value = '';
  document.getElementById('donor-name').value = '';
  updateBtn();
}

// ── TOAST ─────────────────────────────
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── ADMIN ─────────────────────────────
function openAdmin() {
  document.getElementById('admin-overlay').classList.add('show');
  document.getElementById('admin-pass').value = '';
  document.getElementById('login-err').style.display = 'none';
  document.getElementById('admin-login-box').style.display = 'block';
  document.getElementById('admin-messages').style.display = 'none';
}

function closeAdmin() {
  document.getElementById('admin-overlay').classList.remove('show');
}

async function checkPass() {
  const pass = document.getElementById('admin-pass').value;
  try {
    const res = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pass })
    });
    if (res.ok) {
      const data = await res.json();
      sessionStorage.setItem('admin_token', data.token);
      document.getElementById('admin-login-box').style.display = 'none';
      document.getElementById('admin-messages').style.display = 'block';
      loadMessages();
    } else {
      document.getElementById('login-err').style.display = 'block';
      document.getElementById('admin-pass').value = '';
    }
  } catch (e) {
    document.getElementById('login-err').style.display = 'block';
  }
}

async function loadMessages() {
  const token = sessionStorage.getItem('admin_token');
  try {
    const res = await fetch('/api/admin/donations', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) { closeAdmin(); return; }
    const data = await res.json();
    renderMsgs(data.donations);
    document.getElementById('stat-count').textContent = data.stats.count;
    document.getElementById('stat-total').textContent =
      data.stats.total_uzs > 0
        ? Math.round(data.stats.total_uzs).toLocaleString('uz-UZ') : '0';
  } catch (e) {
    // Fallback: localStorage
    const local = JSON.parse(localStorage.getItem('d_fallback') || '[]');
    renderMsgs(local);
  }
}

async function delMsg(id) {
  const token = sessionStorage.getItem('admin_token');
  try {
    await fetch(`/api/admin/donations/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } catch (e) {
    const local = JSON.parse(localStorage.getItem('d_fallback') || '[]');
    localStorage.setItem('d_fallback', JSON.stringify(local.filter(m => m.id != id)));
  }
  loadMessages();
}

async function clearAll() {
  const label = currentLang === 'uz' ? 'Barchasini o\'chirmoqchimisiz?' : 'Clear all messages?';
  if (!confirm(label)) return;
  const token = sessionStorage.getItem('admin_token');
  try {
    await fetch('/api/admin/donations', {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
  } catch (e) {
    localStorage.removeItem('d_fallback');
  }
  loadMessages();
}

function renderMsgs(msgs) {
  const list = document.getElementById('msg-list');
  if (!msgs || !msgs.length) {
    list.innerHTML = '<div class="no-msgs">Hozircha xabar yo\'q 📭</div>';
    return;
  }
  list.innerHTML = msgs.map(m => {
    const amt    = m.amount || 0;
    const cur    = m.currency || 'UZS';
    const fmt    = cur === 'UZS' ? amt.toLocaleString('uz-UZ') : amt.toFixed(2);
    const msgTxt = m.message || '';
    const exp    = m.expires_at ? new Date(m.expires_at) : null;
    const minsLeft = exp ? Math.max(0, Math.round((exp - Date.now()) / 60000)) : '?';
    return `
      <div class="msg-card" id="mc-${m.id}">
        <div class="msg-top">
          <span class="msg-sender">${esc(m.name)}</span>
          <span class="msg-amount">${cur} ${fmt}</span>
        </div>
        ${msgTxt
          ? `<div class="msg-text">"${esc(msgTxt)}"</div>`
          : `<div class="msg-text" style="color:#333;font-style:normal">— xabar yozilmagan —</div>`
        }
        <div class="msg-meta">
          <span class="msg-time">${fmtTime(m.created_at || m.time)}</span>
          <span class="msg-timer">⏱ ${minsLeft} daq</span>
          <button class="del-btn" onclick="delMsg('${m.id}')">O'chirish</button>
        </div>
      </div>`;
  }).join('');
}

// ── HELPERS ───────────────────────────
function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
       + ' · ' + d.toLocaleDateString('uz-UZ');
}
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── INIT ──────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('amount').addEventListener('input', updateBtn);
  setInterval(() => {
    if (document.getElementById('admin-messages').style.display !== 'none') loadMessages();
  }, 60000);
});
