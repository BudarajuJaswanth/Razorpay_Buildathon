// ============================================================
//  KicksVault India — Agentic Commerce SPA v2.0
//  app.js — Ultra-premium client-side application
// ============================================================

// ---------- Product config (mirrors backend catalog) ----------
// ---------- Product config (mirrors backend catalog) ----------
const PRODUCTS = {
  PROD_001: {
    name: "Air Jordan 1 High OG 'Chicago Lost & Found'",
    image: 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80',
    price: 24999, floor: 21500, stock: 2,
    badges: [['Grail Drop', 'red'], ['Verified Authentic', 'emerald']],
    desc: 'Iconic high-top with cracked leather detailing and the legendary Chicago colorway. Deadstock release.'
  },
  PROD_002: {
    name: "Yeezy Boost 350 V2 'Onyx'",
    image: 'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=800&q=80',
    price: 19499, floor: 17000, stock: 4,
    badges: [['Primeknit', 'indigo'], ['Boost', 'indigo']],
    desc: 'Sleek all-black monochrome silhouette with full-length re-engineered Boost cushioning.'
  },
  PROD_003: {
    name: "Nike Dunk Low Retro 'Panda'",
    image: 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80',
    price: 11999, floor: 9999, stock: 7,
    badges: [['Street Icon', 'cyan'], ['In Stock', 'emerald']],
    desc: "The timeless two-tone monochrome dunk — a certified collector's daily staple."
  },
  PROD_004: {
    name: 'CreaseGuard Pro Care & Sneaker Shield Kit',
    image: 'https://images.unsplash.com/photo-1607522370275-f14206abe5d3?auto=format&fit=crop&w=800&q=80',
    price: 1499, floor: 999, stock: 25,
    badges: [['Essential Addon', 'amber']],
    desc: 'Hydro-repellent shields, natural horsehair brush, and enzymatic foam. Protect your grails.'
  },
  PROD_005: {
    name: "Travis Scott x AJ1 Low 'Reverse Mocha'",
    image: 'https://images.unsplash.com/photo-1512374382149-233c42b6a83b?auto=format&fit=crop&w=800&q=80',
    price: 89999, floor: 82000, stock: 1,
    badges: [['Holy Grail', 'red'], ['NFC Verified', 'emerald']],
    desc: 'Sail and Ridgerock nubuck upper with Cactus Jack oversized backward Swoosh embroidery.'
  },
  PROD_006: {
    name: "New Balance 9060 'Rain Cloud'",
    image: 'https://images.unsplash.com/photo-1539185441755-769473a23570?auto=format&fit=crop&w=800&q=80',
    price: 16499, floor: 14200, stock: 5,
    badges: [['ABZORB Pods', 'cyan'], ['Essential', 'indigo']],
    desc: 'Futuristic retro-runner fusing 990-series heritage with sculpted dual-density cushioning.'
  },
  PROD_007: {
    name: "Air Jordan 4 Retro 'Military Black'",
    image: 'https://images.unsplash.com/photo-1575537302964-96cd47c06b1b?auto=format&fit=crop&w=800&q=80',
    price: 34999, floor: 30500, stock: 3,
    badges: [['Vault Heat', 'red'], ['Deadstock', 'emerald']],
    desc: 'Clean white leather with neutral grey suede toe-wrap and contrasting black TPU eyelets.'
  },
  PROD_008: {
    name: 'KicksVault Premium Acrylic Sneaker Crate',
    image: 'https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?auto=format&fit=crop&w=800&q=80',
    price: 3999, floor: 2800, stock: 15,
    badges: [['Display Vault', 'amber'], ['LED Ready', 'indigo']],
    desc: 'Handcrafted display vault with UV-filtering magnetic door and integrated LED spotlighting.'
  }
};

const BADGE_COLORS = {
  red:     { bg: 'rgba(248,113,113,0.12)', color: '#fca5a5', border: 'rgba(248,113,113,0.3)' },
  emerald: { bg: 'rgba(52,211,153,0.10)',  color: '#6ee7b7', border: 'rgba(52,211,153,0.28)' },
  indigo:  { bg: 'rgba(99,102,241,0.12)',  color: '#a5b4fc', border: 'rgba(99,102,241,0.3)' },
  amber:   { bg: 'rgba(251,191,36,0.10)',  color: '#fcd34d', border: 'rgba(251,191,36,0.28)' },
  cyan:    { bg: 'rgba(34,211,238,0.10)',  color: '#67e8f9', border: 'rgba(34,211,238,0.25)' }
};

// ---------- State ----------
let sessionId = generateSessionId();
let currentCheckout = null;
let isSending = false;
let chatHistory = [];
const DEV_TOKEN = 'dev-secret-token-razorpay-agentic-2026';

let currentUser = JSON.parse(localStorage.getItem('kv_user') || 'null') || {
  user_id: 'usr_collector',
  role: 'user',
  name: 'Verified Collector',
  email: 'collector@kicksvault.in',
  avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80',
  token: 'guest_token'
};

let userDeliveryLocation = localStorage.getItem('kv_delivery_location') || 'India (Standard Courier)';

function generateSessionId() {
  return `sess_${Math.random().toString(36).slice(2,8)}_${Date.now().toString(36)}`;
}

// ============================================================
//  INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  initClock();
  initSession();
  initLocation();
  initAuth();
  initNav();
  initChat();
  initHUD();
  initInventoryManager();
  renderProductGrid();
  startHUDPoller();
  startFailurePoller();
  showPage('page-storefront');
});

// ============================================================
//  AUTHENTICATION & RBAC (USER VS. ADMIN)
// ============================================================
function initAuth() {
  updateAuthUI();

  document.getElementById('user-profile-pill')?.addEventListener('click', openAuthModal);
  document.getElementById('btn-auth-trigger')?.addEventListener('click', openAuthModal);
  document.getElementById('btn-close-auth')?.addEventListener('click', closeAuthModal);

  document.getElementById('btn-login-customer')?.addEventListener('click', () => {
    loginAs('user', 'Verified Collector', 'collector@kicksvault.in');
  });

  document.getElementById('btn-login-admin')?.addEventListener('click', () => {
    loginAs('admin', 'Merchant Administrator', 'admin@kicksvault.in');
  });

  document.getElementById('btn-google-signin')?.addEventListener('click', () => {
    loginAs('user', 'Google User (Collector)', 'google.user@kicksvault.in');
  });
}

function openAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.style.display = 'flex';
}

function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.style.display = 'none';
}

async function loginAs(role, name, email) {
  try {
    const resp = await fetch('/api/auth/demo-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, name, email })
    });
    if (resp.ok) {
      const user = await resp.json();
      currentUser = user;
      localStorage.setItem('kv_user', JSON.stringify(currentUser));
      updateAuthUI();
      closeAuthModal();
      logTerminal('ok', `[AUTH] Signed in as: ${user.name} (${user.role.toUpperCase()})`);
    }
  } catch (err) {
    currentUser = {
      user_id: `usr_${role}`,
      role: role,
      name: name,
      email: email,
      avatar: role === 'admin' 
        ? 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80'
        : 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80',
      token: 'local_token'
    };
    localStorage.setItem('kv_user', JSON.stringify(currentUser));
    updateAuthUI();
    closeAuthModal();
  }
}

function updateAuthUI() {
  const nameEl = document.getElementById('user-display-name');
  const roleBadge = document.getElementById('user-role-badge');
  const avatarEl = document.getElementById('user-avatar');
  const merchantLock = document.getElementById('tab-merchant-lock');

  if (nameEl) nameEl.textContent = currentUser.name.split(' ')[0];
  if (avatarEl) avatarEl.src = currentUser.avatar;

  if (roleBadge) {
    roleBadge.textContent = currentUser.role.toUpperCase();
    roleBadge.className = currentUser.role === 'admin' ? 'role-badge-admin' : 'role-badge-user';
  }

  if (merchantLock) {
    merchantLock.style.display = currentUser.role === 'admin' ? 'none' : 'inline';
  }
}

// ============================================================
//  MERCHANT INVENTORY & STOCK CONTROLLER
// ============================================================
function initInventoryManager() {
  renderInventoryTable();

  document.getElementById('btn-toggle-add-product')?.addEventListener('click', () => {
    const panel = document.getElementById('add-product-panel');
    if (panel) {
      panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
  });

  document.getElementById('btn-cancel-add-prod')?.addEventListener('click', () => {
    const panel = document.getElementById('add-product-panel');
    if (panel) panel.style.display = 'none';
  });

  document.getElementById('form-add-product')?.addEventListener('submit', handleAddNewProduct);
}

function renderInventoryTable() {
  const tbody = document.getElementById('inventory-tbody');
  if (!tbody) return;

  tbody.innerHTML = Object.entries(PRODUCTS).map(([pid, p]) => {
    const stockColor = p.stock > 3 ? 'var(--emerald)' : (p.stock > 0 ? 'var(--amber)' : 'var(--red)');
    return `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:10px">
            <img src="${p.image}" style="width:34px;height:34px;border-radius:8px;object-fit:cover;border:1px solid rgba(255,255,255,0.1)"/>
            <div>
              <div style="font-weight:700;font-size:12px;color:var(--text-primary)">${esc(p.name)}</div>
              <div style="font-family:var(--font-mono);font-size:10px;color:var(--indigo-bright)">${pid}</div>
            </div>
          </div>
        </td>
        <td style="font-weight:700;color:var(--text-primary)">₹${Number(p.price).toLocaleString('en-IN')}</td>
        <td>
          <span style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:${stockColor}">
            ${p.stock} in vault
          </span>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px">
            <button onclick="changeProductStock('${pid}', -1)" class="btn btn-ghost btn-sm" style="padding:2px 8px;font-size:12px;border:1px solid rgba(255,255,255,0.1)" title="Decrease Stock">
              -
            </button>
            <button onclick="changeProductStock('${pid}', 1)" class="btn btn-ghost btn-sm" style="padding:2px 8px;font-size:12px;border:1px solid rgba(255,255,255,0.1)" title="Increase Stock">
              +
            </button>
            <button onclick="promptSetStock('${pid}', ${p.stock})" class="btn btn-secondary btn-sm" style="padding:2px 8px;font-size:10px" title="Set Exact Stock">
              Set
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function changeProductStock(pid, delta) {
  if (!PRODUCTS[pid]) return;
  const currentStock = PRODUCTS[pid].stock || 0;
  const newStock = Math.max(0, currentStock + delta);
  await saveProductStock(pid, newStock);
}

async function promptSetStock(pid, currentStock) {
  const input = prompt(`Enter new stock count for ${pid}:`, currentStock);
  if (input === null) return;
  const num = parseInt(input, 10);
  if (!isNaN(num) && num >= 0) {
    await saveProductStock(pid, num);
  }
}

async function saveProductStock(pid, newStock) {
  try {
    const resp = await fetch(`/api/products/${pid}/stock`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stock: newStock })
    });
    if (resp.ok) {
      if (PRODUCTS[pid]) PRODUCTS[pid].stock = newStock;
      renderInventoryTable();
      renderProductGrid();
      logTerminal('ok', `[INVENTORY] Updated stock for ${pid} → ${newStock} units`);
    } else {
      const err = await resp.json();
      alert(`Error updating stock: ${err.detail || 'Request failed'}`);
    }
  } catch (err) {
    alert(`Network error updating stock: ${err.message}`);
  }
}

async function handleAddNewProduct(e) {
  e.preventDefault();
  const id = document.getElementById('new-prod-id')?.value.trim();
  const name = document.getElementById('new-prod-name')?.value.trim();
  const retail = parseFloat(document.getElementById('new-prod-retail')?.value);
  const floor = parseFloat(document.getElementById('new-prod-floor')?.value);
  const stock = parseInt(document.getElementById('new-prod-stock')?.value, 10) || 1;
  const badge = document.getElementById('new-prod-badge')?.value.trim() || 'Vault Drop';
  const image = document.getElementById('new-prod-image')?.value.trim() || 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80';
  const desc = document.getElementById('new-prod-desc')?.value.trim();

  if (!id || !name || isNaN(retail) || isNaN(floor)) {
    alert('Please fill in all required product fields with valid values.');
    return;
  }

  try {
    const resp = await fetch('/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id,
        name,
        description: desc,
        retail_price: retail,
        floor_price: floor,
        stock,
        badge,
        image
      })
    });

    if (resp.ok) {
      PRODUCTS[id] = {
        name,
        price: retail,
        floor,
        stock,
        badges: [[badge, 'red']],
        desc,
        image
      };

      document.getElementById('add-product-panel').style.display = 'none';
      document.getElementById('form-add-product').reset();

      renderInventoryTable();
      renderProductGrid();

      logTerminal('ok', `[CATALOG] Deployed new vault product drop: ${id} (${name})`);
      alert(`🎉 Product ${name} (${id}) deployed to live catalog!`);
    } else {
      const err = await resp.json();
      alert(`Error creating product: ${err.detail || 'Failed'}`);
    }
  } catch (err) {
    alert(`Network error creating product: ${err.message}`);
  }
}

// ============================================================
//  STOREFRONT PRODUCT GRID (8 LUXURY ITEMS)
// ============================================================
async function renderProductGrid() {
  const container = document.getElementById('product-grid');
  if (!container) return;

  let catalogData = PRODUCTS;
  try {
    const resp = await fetch('/api/catalog');
    if (resp.ok) {
      const data = await resp.json();
      if (data.products && Object.keys(data.products).length > 0) {
        Object.entries(data.products).forEach(([pid, p]) => {
          if (catalogData[pid]) {
            catalogData[pid].name = p.name || catalogData[pid].name;
            catalogData[pid].price = p.retail_price || catalogData[pid].price;
            catalogData[pid].stock = p.stock ?? catalogData[pid].stock;
            catalogData[pid].desc = p.description || catalogData[pid].desc;
          } else {
            catalogData[pid] = {
              name: p.name,
              price: p.retail_price,
              floor: p.floor_price,
              stock: p.stock,
              badges: [[p.badge || 'Verified', 'emerald']],
              desc: p.description,
              image: 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80'
            };
          }
        });
      }
    }
  } catch (_) {}

  container.innerHTML = Object.entries(catalogData).map(([pid, p]) => {
    const badgesHtml = (p.badges || [['Verified Authentic', 'emerald']]).map(([label, colorKey]) => {
      const c = BADGE_COLORS[colorKey] || BADGE_COLORS.emerald;
      return `<span style="background:${c.bg};color:${c.color};border:1px solid ${c.border};padding:2px 8px;border-radius:100px;font-size:10px;font-weight:700;letter-spacing:0.04em">${esc(label)}</span>`;
    }).join(' ');

    return `
      <div class="product-card glass" style="border-radius:16px;overflow:hidden;display:flex;flex-direction:column;transition:all 0.25s ease;border:1px solid rgba(255,255,255,0.07)">
        <div style="position:relative;height:210px;overflow:hidden;background:#0d0d12">
          <img src="${p.image}" alt="${esc(p.name)}" style="width:100%;height:100%;object-fit:cover;transition:transform 0.4s ease" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'"/>
          <div style="position:absolute;top:12px;left:12px;display:flex;gap:6px;flex-wrap:wrap">
            ${badgesHtml}
          </div>
          <div style="position:absolute;bottom:10px;right:12px;background:rgba(0,0,0,0.7);backdrop-filter:blur(6px);padding:3px 8px;border-radius:6px;font-family:var(--font-mono);font-size:10px;color:var(--text-secondary)">
            Stock: ${p.stock}
          </div>
        </div>
        <div style="padding:18px;display:flex;flex-direction:column;flex:1;justify-content:space-between">
          <div>
            <div style="font-family:var(--font-mono);font-size:11px;color:var(--indigo-bright);margin-bottom:4px">${pid}</div>
            <h3 style="font-size:15px;font-weight:700;line-height:1.35;margin-bottom:8px;color:var(--text-primary)">${esc(p.name)}</h3>
            <p style="font-size:12px;color:var(--text-secondary);line-height:1.5;margin-bottom:14px">${esc(p.desc)}</p>
          </div>
          <div>
            <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px">
              <div>
                <span style="font-size:10px;color:var(--text-muted);display:block">RETAIL VALUE</span>
                <span style="font-size:18px;font-weight:800;color:var(--text-primary)">₹${Number(p.price).toLocaleString('en-IN')}</span>
              </div>
              <span style="font-size:11px;color:var(--emerald);font-weight:600">✓ In Vault</span>
            </div>
            <button onclick="startNegotiationForProduct('${pid}', '${esc(p.name)}')" class="btn btn-primary" style="width:100%;justify-content:center;font-size:12px;padding:9px 12px">
              <i data-lucide="message-square" style="width:14px;height:14px"></i>
              Negotiate with AI Concierge
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  lucide.createIcons();
}

function startNegotiationForProduct(productId, productName) {
  showPage('page-chat');
  const input = document.getElementById('chat-input');
  if (input) {
    input.value = `Tell me about the ${productName} (${productId}). What is the best price?`;
    input.focus();
  }
}
function initLocation() {
  updateLocationUI();

  document.getElementById('btn-detect-location')?.addEventListener('click', detectUserLocation);
  document.getElementById('btn-manual-location')?.addEventListener('click', promptManualLocation);
}

function updateLocationUI() {
  const el = document.getElementById('delivery-location-display');
  if (el) {
    el.textContent = userDeliveryLocation;
  }
}

function detectUserLocation() {
  const btn = document.getElementById('btn-detect-location');
  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser. Please enter your city manually.');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:12px;height:12px"></i> Requesting…`;
    lucide.createIcons();
  }

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      logTerminal('info', `[LOCATION] Geolocation permitted: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);

      try {
        // Reverse geocoding using open client-side endpoint
        const res = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`);
        if (res.ok) {
          const locData = await res.json();
          const city = locData.city || locData.locality || locData.principalSubdivision || 'India';
          const state = locData.principalSubdivision || '';
          const postcode = locData.postcode ? ` (${locData.postcode})` : '';
          userDeliveryLocation = `${city}${state && state !== city ? ', ' + state : ''}${postcode}`;
        } else {
          userDeliveryLocation = `Lat: ${lat.toFixed(2)}, Lon: ${lon.toFixed(2)} (India)`;
        }
      } catch (_) {
        userDeliveryLocation = `India (Coordinates: ${lat.toFixed(2)}°N, ${lon.toFixed(2)}°E)`;
      }

      localStorage.setItem('kv_delivery_location', userDeliveryLocation);
      updateLocationUI();
      logTerminal('ok', `[LOCATION] Destination locked: 📍 ${userDeliveryLocation}`);

      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="check" style="width:12px;height:12px;color:var(--emerald)"></i> Detected`;
        setTimeout(() => {
          btn.innerHTML = `<i data-lucide="crosshair" style="width:12px;height:12px"></i> Detect Location`;
          lucide.createIcons();
        }, 3000);
      }
      lucide.createIcons();
    },
    (error) => {
      logTerminal('warn', `[LOCATION] Geolocation permission denied or failed: ${error.message}`);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="crosshair" style="width:12px;height:12px"></i> Detect Location`;
        lucide.createIcons();
      }
      promptManualLocation();
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
  );
}

function promptManualLocation() {
  const city = prompt('Enter your delivery city / postal code in India:', userDeliveryLocation.replace('India (Standard Courier)', ''));
  if (city && city.trim()) {
    userDeliveryLocation = city.trim();
    localStorage.setItem('kv_delivery_location', userDeliveryLocation);
    updateLocationUI();
    logTerminal('ok', `[LOCATION] Destination updated manually: 📍 ${userDeliveryLocation}`);
  }
}

// ============================================================
//  CLOCK
// ============================================================
function initClock() {
  const tick = () => {
    const el = document.getElementById('live-clock');
    if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false });
  };
  tick();
  setInterval(tick, 1000);
}

// ============================================================
//  SESSION
// ============================================================
function initSession() {
  updateSessionUI();
  document.getElementById('btn-reset')?.addEventListener('click', resetSession);
}

function updateSessionUI() {
  const pill = document.getElementById('session-pill');
  const short = document.getElementById('session-short');
  if (pill) pill.style.display = 'inline-flex';
  if (short) short.textContent = sessionId.slice(0, 16) + '…';
}

async function resetSession() {
  try {
    await fetch('/api/reset-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '', session_id: sessionId })
    });
  } catch (_) {}
  sessionId = generateSessionId();
  currentCheckout = null;
  chatHistory = [];
  updateSessionUI();
  resetChatUI();
  setSentinel('idle');
  logTerminal('info', `[SESSION] Reset — new session: ${sessionId}`);
}

function resetChatUI() {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  msgs.innerHTML = `
    <div class="msg-wrap-agent">
      <div class="agent-avatar" style="width:30px;height:30px;border-radius:8px;flex-shrink:0">
        <i data-lucide="bot" style="width:14px;height:14px"></i>
      </div>
      <div class="chat-bubble bubble-agent">
        <strong style="color:var(--indigo-bright)">KicksVault AI</strong>
        <p style="margin-top:4px">Session reset. How can I help you today?</p>
      </div>
    </div>`;
  lucide.createIcons();
  document.getElementById('guardrail-alert').style.display = 'none';
  document.getElementById('checkout-panel').style.display = 'none';
  document.getElementById('stage-badge').textContent = 'Stage: Idle';
}

// ============================================================
//  NAVIGATION
// ============================================================
function initNav() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => showPage(btn.dataset.target));
  });
}

function showPage(pageId) {
  if (pageId === 'page-merchant' && currentUser.role !== 'admin') {
    const confirmSwitch = confirm("🛡️ Merchant HUD is an Admin-only view.\n\nWould you like to switch to Merchant Administrator mode to inspect live telemetry, stock controls, and payment simulators?");
    if (confirmSwitch) {
      loginAs('admin', 'Merchant Administrator', 'admin@kicksvault.in');
    } else {
      return;
    }
  }

  document.querySelectorAll('.page').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(pageId)?.classList.add('active');
  document.querySelector(`[data-target="${pageId}"]`)?.classList.add('active');
  setTimeout(() => lucide.createIcons(), 60);
}

function seedAndNavigate(prodId, prodName) {
  showPage('page-chat');
  setTimeout(() => {
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = `I'm interested in the ${prodName}. What's your best price?`;
      sendMessage();
    }
  }, 100);
}

// ============================================================
//  CHAT
// ============================================================
function initChat() {
  document.getElementById('send-btn')?.addEventListener('click', sendMessage);
  document.getElementById('chat-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  document.querySelectorAll('.chip').forEach(c => {
    c.addEventListener('click', () => {
      const input = document.getElementById('chat-input');
      if (input) { input.value = c.dataset.prompt; sendMessage(); }
    });
  });

  // Pay via Razorpay Sandbox Button Trigger
  document.getElementById('checkout-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    if (currentCheckout) {
      openRazorpaySandboxModal(currentCheckout);
    } else {
      appendSystem('⚠ Please negotiate and lock in an agreed price with the AI Concierge first.');
    }
  });

  document.getElementById('sim-success-chat')?.addEventListener('click', () => {
    currentCheckout ? simulateDirect('success') : appendSystem('⚠ Complete a negotiation first to get a payment link.');
  });
  document.getElementById('sim-failure-chat')?.addEventListener('click', () => {
    currentCheckout ? simulateDirect('failure') : appendSystem('⚠ Complete a negotiation first to get a payment link.');
  });

  initRazorpayModal();
}

function initRazorpayModal() {
  document.getElementById('btn-close-rzp')?.addEventListener('click', closeRazorpaySandboxModal);

  document.querySelectorAll('.rzp-method-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.rzp-method-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const method = btn.dataset.method;
      updateRazorpayMethodUI(method);
    });
  });

  document.getElementById('btn-rzp-pay-confirm')?.addEventListener('click', () => {
    closeRazorpaySandboxModal();
    if (currentCheckout) {
      simulateDirect('success');
      appendSystem(`🎉 Payment Authorized! Razorpay Sandbox has confirmed the capture of ₹${Number(currentCheckout.amount).toLocaleString('en-IN')}. Order Receipt generated.`);
    }
  });

  document.getElementById('btn-rzp-sim-fail')?.addEventListener('click', () => {
    closeRazorpaySandboxModal();
    if (currentCheckout) {
      simulateDirect('failure');
    }
  });
}

function updateRazorpayMethodUI(method) {
  const container = document.getElementById('rzp-method-content');
  if (!container) return;

  if (method === 'upi') {
    container.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <i data-lucide="check" style="width:12px;height:12px;color:var(--emerald)"></i>
        <span style="color:var(--text-primary);font-weight:600">Simulated Instant UPI Transfer</span>
      </div>
      <div>Virtual VPA: <span style="font-family:var(--font-mono);color:var(--cyan)">collector@okhdfcbank</span></div>
      <div style="margin-top:4px">Destination: <span style="color:var(--text-primary)">📍 ${esc(userDeliveryLocation)}</span></div>
    `;
  } else if (method === 'card') {
    container.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <i data-lucide="credit-card" style="width:12px;height:12px;color:var(--indigo-bright)"></i>
        <span style="color:var(--text-primary);font-weight:600">Razorpay Test Card (4111 •••• •••• 4444)</span>
      </div>
      <div>Expiry: <span style="font-family:var(--font-mono);color:var(--cyan)">12/28</span> · CVV: <span style="font-family:var(--font-mono);color:var(--cyan)">999</span></div>
      <div style="margin-top:4px">3D-Secure Sandbox: <span style="color:var(--emerald)">Auto-OTP Verified</span></div>
    `;
  } else if (method === 'netbanking') {
    container.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <i data-lucide="landmark" style="width:12px;height:12px;color:var(--amber)"></i>
        <span style="color:var(--text-primary);font-weight:600">HDFC / ICICI / SBI / Axis Sandbox</span>
      </div>
      <div>Corporate Gateway: <span style="font-family:var(--font-mono);color:var(--cyan)">KicksVault Instant Clearing</span></div>
      <div style="margin-top:4px">Status: <span style="color:var(--emerald)">High-Availability Rail</span></div>
    `;
  }
  lucide.createIcons();
}

function openRazorpaySandboxModal(checkoutData) {
  if (!checkoutData) return;
  const prod = PRODUCTS[checkoutData.product_id] || {};

  const modal = document.getElementById('razorpay-modal');
  const img = document.getElementById('rzp-item-img');
  const name = document.getElementById('rzp-item-name');
  const orderId = document.getElementById('rzp-item-order-id');
  const price = document.getElementById('rzp-item-price');
  const btnAmount = document.getElementById('rzp-btn-amount');
  const loc = document.getElementById('rzp-item-location');

  if (img) img.src = prod.image || 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=200&q=80';
  if (name) name.textContent = prod.name || checkoutData.product_id;
  if (orderId) orderId.textContent = checkoutData.order_id || `order_${Date.now()}`;
  const formattedPrice = `₹${Number(checkoutData.amount).toLocaleString('en-IN')}`;
  if (price) price.textContent = formattedPrice;
  if (btnAmount) btnAmount.textContent = formattedPrice;
  if (loc) loc.textContent = `📍 ${userDeliveryLocation}`;

  if (modal) modal.style.display = 'flex';
  lucide.createIcons();
}

function closeRazorpaySandboxModal() {
  const modal = document.getElementById('razorpay-modal');
  if (modal) modal.style.display = 'none';
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = (input?.value || '').trim();
  if (!text || isSending) return;
  input.value = '';
  isSending = true;
  document.getElementById('send-btn').disabled = true;

  appendUser(text);
  showTyping();
  setSentinel('eval');
  logMini(`[USER] ${text.slice(0, 80)}`);

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        location: userDeliveryLocation,
        history: chatHistory
      })
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    // Maintain multi-turn conversation memory
    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'assistant', content: data.reply });

    hideTyping();
    appendAgent(data.reply);
    updateStageBadge(data.negotiation_stage);
    logMini(`[AGENT] ${data.reply.slice(0, 80)}${data.reply.length > 80 ? '…' : ''}`);

    if (data.delivery_location && data.delivery_location !== userDeliveryLocation) {
      userDeliveryLocation = data.delivery_location;
      localStorage.setItem('kv_delivery_location', userDeliveryLocation);
      updateLocationUI();
    }

    if (data.guardrail_triggered) {
      showGuardrailAlert(`🛡️ Vault Sentinel: Best available collector pricing locked in at ₹${Number(data.agreed_price).toLocaleString('en-IN')}.`);
      setSentinel('enforced');
      logTerminal('warn', `[SENTINEL] Vault reserve enforced — product: ${data.product_id} · final: ₹${data.agreed_price}`);
    } else {
      setSentinel('idle');
    }

    if (data.checkout_url) {
      renderCheckoutCard(data);
      logTerminal('ok', `[PAYMENT LINK] Created — ₹${data.agreed_price} · ${data.product_id}`);
      logTerminal('ok', `[DESTINATION] Priority delivery routed to: 📍 ${userDeliveryLocation}`);
      logTerminal('ok', `[URL] ${data.checkout_url}`);
    }

  } catch (err) {
    hideTyping();
    appendSystem(`⚠ Error: ${err.message}`);
    logTerminal('fail', `[ERROR] Chat API: ${err.message}`);
    setSentinel('idle');
  } finally {
    isSending = false;
    document.getElementById('send-btn').disabled = false;
    input?.focus();
  }
}

function renderCheckoutCard(data) {
  const prodId = data.product_id || 'PROD_001';
  const prod = PRODUCTS[prodId] || {};
  currentCheckout = {
    order_id: `order_chat_${Date.now()}`,
    product_id: prodId,
    amount: data.agreed_price,
    checkout_url: data.checkout_url
  };

  const imgEl = document.getElementById('checkout-img');
  if (imgEl) imgEl.src = prod.image || '';

  const nameEl = document.getElementById('checkout-product-name');
  if (nameEl) nameEl.textContent = prod.name || prodId;

  const priceEl = document.getElementById('checkout-price');
  if (priceEl) priceEl.textContent = `₹${Number(data.agreed_price).toLocaleString('en-IN')}`;

  const linkEl = document.getElementById('checkout-link');
  if (linkEl) linkEl.href = data.checkout_url || '#';

  const guardEl = document.getElementById('checkout-guardrail');
  if (guardEl) guardEl.style.display = data.guardrail_triggered ? 'flex' : 'none';

  document.getElementById('checkout-panel').style.display = 'block';
}

// ============================================================
//  BUBBLE HELPERS
// ============================================================
function appendUser(text) {
  const msgs = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap-user';
  wrap.innerHTML = `<div class="chat-bubble bubble-user"><p>${esc(text)}</p></div>`;
  msgs.appendChild(wrap);
  scrollBottom(msgs);
}

function appendAgent(text) {
  const msgs = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap-agent';
  const formatted = esc(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
  wrap.innerHTML = `
    <div class="agent-avatar" style="width:30px;height:30px;border-radius:8px;flex-shrink:0">
      <i data-lucide="bot" style="width:14px;height:14px"></i>
    </div>
    <div class="chat-bubble bubble-agent"><p>${formatted}</p></div>`;
  msgs.appendChild(wrap);
  scrollBottom(msgs);
  lucide.createIcons();
}

function appendSystem(text) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'bubble-system';
  div.textContent = text;
  msgs.appendChild(div);
  scrollBottom(msgs);
}

function showTyping() {
  const msgs = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = 'typing-wrap';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `
    <div class="agent-avatar" style="width:30px;height:30px;border-radius:8px;flex-shrink:0">
      <i data-lucide="bot" style="width:14px;height:14px"></i>
    </div>
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  msgs.appendChild(wrap);
  scrollBottom(msgs);
  lucide.createIcons();
}

function hideTyping() { document.getElementById('typing-indicator')?.remove(); }
function scrollBottom(el) { requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; }); }
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

// ============================================================
//  STAGE BADGE & GUARDRAIL
// ============================================================
function updateStageBadge(stage) {
  const el = document.getElementById('stage-badge');
  if (!el) return;
  const labels = { 0:'Stage: Idle', 1:'Stage 1 — Craftsmanship', 2:'Stage 2 — Mid Offer', 3:'Stage 3 — Closing' };
  el.textContent = labels[stage] ?? 'Stage: Active';
}

function showGuardrailAlert(msg) {
  const el = document.getElementById('guardrail-alert');
  const msgEl = document.getElementById('guardrail-msg');
  if (el) el.style.display = 'flex';
  if (msgEl) msgEl.textContent = msg;
}

// ============================================================
//  SENTINEL
// ============================================================
function setSentinel(state) {
  const el = document.getElementById('sentinel');
  if (!el) return;
  el.className = 'sentinel';
  if (state === 'idle') {
    el.classList.add('sentinel-idle');
    el.textContent = '◎  IDLE — Awaiting Negotiation Activity';
  } else if (state === 'eval') {
    el.classList.add('sentinel-eval');
    el.textContent = '⚡  EVALUATING — Guardrail Sentinel Running…';
  } else if (state === 'enforced') {
    el.classList.add('sentinel-enforced');
    el.textContent = '🛡️  MARGIN GUARDRAIL ENFORCED — Price Clamped to Floor';
  }
}

// ============================================================
//  HUD
// ============================================================
function initHUD() {
  document.getElementById('sim-success-hud')?.addEventListener('click', () => runSim('success'));
  document.getElementById('sim-failure-hud')?.addEventListener('click', () => runSim('failure'));
  document.getElementById('btn-clear-log')?.addEventListener('click', clearLog);
}

function startHUDPoller() { pollOrders(); setInterval(pollOrders, 3000); }

async function pollOrders() {
  try {
    const resp = await fetch('/api/orders');
    if (!resp.ok) return;
    renderOrders(await resp.json());
  } catch (_) {}
}

function renderOrders(orders) {
  const tbody = document.getElementById('orders-tbody');
  if (!tbody) return;
  if (!orders?.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted)">No transactions yet.</td></tr>`;
    return;
  }
  const STATUS_STYLE = {
    created: { dot: 'var(--indigo-bright)', label: 'CREATED' },
    paid:    { dot: 'var(--emerald)',       label: 'PAID' },
    failed:  { dot: 'var(--red)',           label: 'FAILED' }
  };
  tbody.innerHTML = orders.slice().reverse().map(o => {
    const s = STATUS_STYLE[o.status] || STATUS_STYLE.created;
    const ts = (o.paid_at || o.created_at) ? new Date(o.paid_at || o.created_at).toLocaleTimeString() : '—';
    return `<tr>
      <td style="color:var(--text-muted);max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${o.order_id}">${o.order_id}</td>
      <td style="color:var(--text-secondary)">${o.product_id}</td>
      <td style="color:var(--text-primary);font-weight:700">₹${Number(o.amount).toLocaleString('en-IN')}</td>
      <td><span style="display:inline-flex;align-items:center;gap:4px;font-size:9px;font-weight:800;letter-spacing:0.06em">
        <span class="status-dot-sm" style="background:${s.dot}"></span>${s.label}
      </span></td>
      <td style="color:var(--text-muted)">${ts}</td>
    </tr>`;
  }).join('');
}

async function runSim(type) {
  const orderId   = document.getElementById('sim-order-id')?.value.trim()  || `order_sim_${Date.now()}`;
  const amount    = parseFloat(document.getElementById('sim-amount')?.value)  || 24999;
  const productId = document.getElementById('sim-product-id')?.value           || 'PROD_001';
  const custId    = document.getElementById('sim-customer-id')?.value.trim()  || 'cust_simulated';

  const endpoint = type === 'success' ? '/api/simulate-payment' : '/api/simulate-failure';
  logTerminal('info', `[SIM] → ${type.toUpperCase()} · ${endpoint}`);
  logTerminal('info', `[SIM] order=${orderId} product=${productId} amount=₹${amount}`);
  setSentinel(type === 'failure' ? 'enforced' : 'eval');

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Dev-Token': DEV_TOKEN },
      body: JSON.stringify({ order_id: orderId, amount, product_id: productId, customer_id: custId })
    });
    const data = await resp.json();
    if (resp.ok) {
      if (type === 'success') {
        logTerminal('ok',   `[WEBHOOK] ✓ payment_link.paid`);
        logTerminal('ok',   `[HMAC]    ${data.verified_hmac?.slice(0,32)}…`);
        logTerminal('ok',   `[LEDGER]  ${orderId} → STATUS: PAID`);
        setSentinel('idle');
      } else {
        logTerminal('fail', `[WEBHOOK] ✗ payment_link.failed`);
        logTerminal('fail', `[ERROR]   reason=bank_transaction_timeout`);
        logTerminal('fail', `[CODE]    BAD_REQUEST_PAYMENT_TIMED_OUT`);
        logTerminal('warn', `[RECOVERY] Session recovery workflow triggered`);
        logTerminal('ok',   `[HMAC]    ${data.verified_hmac?.slice(0,32)}…`);
      }
      logTerminal('dim', `─────────────────────────────────────`);
    } else {
      logTerminal('fail', `[ERR] ${resp.status} ${data.detail}`);
      setSentinel('idle');
    }
    await pollOrders();
  } catch (err) {
    logTerminal('fail', `[ERR] ${err.message}`);
    setSentinel('idle');
  }
}

async function simulateDirect(type) {
  if (!currentCheckout) return;
  const endpoint = type === 'success' ? '/api/simulate-payment' : '/api/simulate-failure';
  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Dev-Token': DEV_TOKEN },
      body: JSON.stringify({
        order_id: currentCheckout.order_id,
        amount: currentCheckout.amount,
        product_id: currentCheckout.product_id,
        customer_id: `cust_${sessionId.slice(-6)}`
      })
    });
    const data = await resp.json();
    if (resp.ok) {
      const msg = type === 'success'
        ? `✅ Webhook simulated: payment_link.paid — HMAC: ${data.verified_hmac?.slice(0,20)}…`
        : `⚠️ Webhook simulated: payment_link.failed — bank_transaction_timeout`;
      appendSystem(msg);
      logMini(`[WEBHOOK] ${type === 'success' ? 'PAID' : 'FAILED'} — HMAC verified`);
      logTerminal(type === 'success' ? 'ok' : 'fail', `[CHAT SIM] ${type.toUpperCase()} — ${data.verified_hmac?.slice(0,24)}…`);
      await pollOrders();
    } else {
      appendSystem(`⚠ Simulation error: ${data.detail}`);
    }
  } catch (err) {
    appendSystem(`⚠ Simulation failed: ${err.message}`);
  }
}

// ============================================================
//  FAILURE POLLER
// ============================================================
function startFailurePoller() {
  setInterval(async () => {
    try {
      const resp = await fetch(`/api/last-failed-order?session_id=${sessionId}`);
      if (!resp.ok) return;
      const data = await resp.json();
      if (data.has_failure) {
        logTerminal('fail', `[FAILURE DETECTED] ${data.order_id} — recovery workflow pending`);
        appendSystem(`⚠️ Payment failure detected. Send a message to trigger the AI recovery workflow.`);
      }
    } catch (_) {}
  }, 6000);
}

// ============================================================
//  LOGGING
// ============================================================
function logTerminal(level, msg) {
  const el = document.getElementById('webhook-terminal');
  if (!el) return;
  const ts = new Date().toLocaleTimeString('en-IN', { hour12: false });
  const div = document.createElement('div');
  div.className = `log-entry log-${level}`;
  div.textContent = `[${ts}] ${msg}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function logMini(msg) {
  const el = document.getElementById('mini-telemetry');
  if (!el) return;
  const ts = new Date().toLocaleTimeString('en-IN', { hour12: false });
  const div = document.createElement('div');
  div.className = 'log-info log-entry';
  div.textContent = `[${ts}] ${msg}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function clearLog() {
  const el = document.getElementById('webhook-terminal');
  if (!el) return;
  el.innerHTML = `
    <div class="log-dim">[CLEAR] Log cleared by operator</div>
    <div class="log-info">[INIT] HMAC-SHA256 verification: ENABLED</div>`;
}
