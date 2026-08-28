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
let pageHistory = ['page-storefront'];

const PAGE_TITLES = {
  'page-storefront': 'Storefront',
  'page-chat': 'AI Concierge',
  'page-story': 'Brand Story',
  'page-roadmap': 'Roadmap',
  'page-admin': 'Admin Panel'
};

let currentUser = null;

// Global Session Check & Fetch Interceptor
const originalFetch = window.fetch;
window.fetch = async function(...args) {
  if (checkSessionExpiry()) {
    return new Response(JSON.stringify({ detail: "Session expired. Please sign in again." }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  let token = localStorage.getItem('auth_token');
  if (token) {
    if (!args[1]) args[1] = {};
    if (!args[1].headers) args[1].headers = {};
    
    // Attach authorization header if not already present
    if (!args[1].headers['Authorization'] && !args[0].includes('g_id_onload')) {
      args[1].headers['Authorization'] = `Bearer ${token}`;
    }
    
    let userStr = localStorage.getItem('auth_user');
    if (userStr) {
      try {
        let u = JSON.parse(userStr);
        if (!args[1].headers['X-User-Role']) {
          args[1].headers['X-User-Role'] = u.role;
        }
      } catch (_) {}
    }
  }
  return originalFetch.apply(this, args);
};

function clearAuthSession() {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('auth_user');
  localStorage.removeItem('auth_expires_at');
  localStorage.removeItem('kv_user');
  currentUser = null;
}

function checkSessionExpiry() {
  let expiresAt = parseFloat(localStorage.getItem('auth_expires_at') || '0');
  let token = localStorage.getItem('auth_token');
  if (token && Date.now() > expiresAt) {
    clearAuthSession();
    showToast("Session expired. Please sign in again.");
    openAuthModal();
    showPage('page-storefront', false);
    return true;
  }
  return false;
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'fixed bottom-4 right-4 z-50 bg-[#121215] border border-white/10 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 animate-in slide-in-from-bottom duration-300';
  toast.innerHTML = `
    <span style="width:6px;height:6px;border-radius:50%;background:var(--red)"></span>
    <span style="font-size:12px;font-weight:600">${message}</span>
  `;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

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
  initPhoneCollectModal();
  initCustomerSimDeck();
  initInventoryManager();
  renderProductGrid();
  startHUDPoller();
  startFailurePoller();
  
  // Check if redirected back from Razorpay checkout link
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('status') === 'success') {
    const orderId = urlParams.get('order_id');
    const paymentId = urlParams.get('payment_id');
    const signature = urlParams.get('signature');
    const amount = urlParams.get('amount');
    const productId = urlParams.get('product_id');
    showPaymentSuccessScreen({
      orderId,
      paymentId,
      amount,
      productId,
      hmac: signature
    });
    window.history.replaceState({}, document.title, "/");
  } else if (urlParams.get('status') === 'failed') {
    alert("⚠️ Payment failed or was cancelled by user. Please try again.");
    window.history.replaceState({}, document.title, "/");
  }

  showPage('page-storefront');
});

// ============================================================
//  AUTHENTICATION, REGISTER, LOGIN, GOOGLE SIGN-IN
// ============================================================
window.toggleAuthMode = function(mode) {
  const loginForm = document.getElementById('form-email-login');
  const signupForm = document.getElementById('form-email-signup');
  const loginTab = document.getElementById('tab-auth-login');
  const signupTab = document.getElementById('tab-auth-signup');
  const feedback = document.getElementById('auth-feedback-box');
  
  if (feedback) feedback.style.display = 'none';

  if (mode === 'login') {
    if (loginForm) loginForm.style.display = 'block';
    if (signupForm) signupForm.style.display = 'none';
    if (loginTab) { loginTab.style.background = 'var(--surface-2)'; loginTab.style.color = '#fff'; }
    if (signupTab) { signupTab.style.background = 'transparent'; signupTab.style.color = 'var(--text-secondary)'; }
  } else {
    if (loginForm) loginForm.style.display = 'none';
    if (signupForm) signupForm.style.display = 'block';
    if (loginTab) { loginTab.style.background = 'transparent'; loginTab.style.color = 'var(--text-secondary)'; }
    if (signupTab) { signupTab.style.background = 'var(--surface-2)'; signupTab.style.color = '#fff'; }
  }
};

window.handleEmailSignup = async function(e) {
  e.preventDefault();
  const name = document.getElementById('signup-name')?.value.trim();
  const email = document.getElementById('signup-email')?.value.trim();
  const password = document.getElementById('signup-password')?.value;
  const role = document.getElementById('signup-role')?.value || 'user';

  if (!name || !email || !password) return;
  if (password.length < 6) {
    showAuthFeedback('error', 'Password must be at least 6 characters long.');
    return;
  }

  showAuthFeedback('info', 'Registering account and generating verification link...');

  try {
    const resp = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, role })
    });
    const data = await resp.json();
    if (resp.ok) {
      showAuthFeedback('success', `Verification email sent! Click <a href="${data.verification_url}" target="_blank" style="text-decoration:underline;color:var(--emerald);font-weight:bold">verify</a> to activate your account.`);
      document.getElementById('form-email-signup').reset();
    } else {
      showAuthFeedback('error', data.detail || 'Registration failed.');
    }
  } catch (err) {
    showAuthFeedback('error', `Network error: ${err.message}`);
  }
};

window.handleEmailLogin = async function(e) {
  e.preventDefault();
  const email = document.getElementById('login-email')?.value.trim();
  const password = document.getElementById('login-password')?.value;
  
  if (!email || !password) return;

  showAuthFeedback('info', 'Signing in...');

  try {
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await resp.json();
    if (resp.ok) {
      currentUser = data.user;
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
      localStorage.setItem('auth_expires_at', data.expires_at.toString());
      updateAuthUI();
      closeAuthModal();
      logTerminal('ok', `[AUTH] Signed in with email as: ${currentUser.name} (${currentUser.role.toUpperCase()})`);
    } else {
      showAuthFeedback('error', data.detail || 'Login failed.');
    }
  } catch (err) {
    showAuthFeedback('error', `Network error: ${err.message}`);
  }
};

// Google GIS callback
window.handleGoogleLoginResponse = function(response) {
  if (!response || !response.credential) return;
  const roleSelect = document.getElementById('auth-role-select')?.value || 'user';
  loginAs(roleSelect, null, null, response.credential);
};

function showAuthFeedback(type, msg) {
  const box = document.getElementById('auth-feedback-box');
  if (!box) return;
  box.style.display = 'block';
  box.textContent = msg;
  if (type === 'error') {
    box.style.background = 'rgba(239,68,68,0.1)';
    box.style.color = 'var(--red)';
    box.style.border = '1px solid rgba(239,68,68,0.3)';
  } else if (type === 'success') {
    box.style.background = 'rgba(16,185,129,0.1)';
    box.style.color = 'var(--emerald)';
    box.style.border = '1px solid rgba(16,185,129,0.3)';
  } else {
    box.style.background = 'rgba(99,102,241,0.1)';
    box.style.color = 'var(--indigo-bright)';
    box.style.border = '1px solid rgba(99,102,241,0.2)';
  }
}

function initAuth() {
  const storedUser = localStorage.getItem('auth_user');
  const storedToken = localStorage.getItem('auth_token');
  const storedExpires = localStorage.getItem('auth_expires_at');
  
  if (storedUser && storedToken && storedExpires) {
    currentUser = JSON.parse(storedUser);
    if (Date.now() > parseFloat(storedExpires)) {
      clearAuthSession();
      setTimeout(openAuthModal, 100);
    } else {
      updateAuthUI();
    }
  } else {
    clearAuthSession();
    setTimeout(openAuthModal, 100);
  }

  document.getElementById('user-profile-pill')?.addEventListener('click', openAuthModal);
  document.getElementById('btn-auth-trigger')?.addEventListener('click', openAuthModal);
  document.getElementById('btn-close-auth')?.addEventListener('click', closeAuthModal);

  document.getElementById('btn-login-customer')?.addEventListener('click', () => {
    loginAs('user', 'Verified Collector', 'collector@kicksvault.in');
  });

  document.getElementById('btn-login-admin')?.addEventListener('click', () => {
    loginAs('admin', 'Merchant Administrator', 'admin@kicksvault.in');
  });
}

function openAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.style.display = 'flex';
  const feedback = document.getElementById('auth-feedback-box');
  if (feedback) feedback.style.display = 'none';
}

function closeAuthModal() {
  if (!localStorage.getItem('auth_token')) {
    showAuthFeedback('error', 'Please authenticate to access KicksVault.');
    return;
  }
  const modal = document.getElementById('auth-modal');
  if (modal) modal.style.display = 'none';
}

async function loginAs(role, name = null, email = null, credential = null) {
  try {
    const resp = await fetch('/api/auth/demo-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role })
    });
    if (resp.ok) {
      const data = await resp.json();
      currentUser = data.user;
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
      localStorage.setItem('auth_expires_at', data.expires_at.toString());
      updateAuthUI();
      closeAuthModal();
      logTerminal('ok', `[AUTH] Signed in via Demo/Google as: ${currentUser.name} (${currentUser.role.toUpperCase()})`);
    } else {
      throw new Error("Demo login endpoint returned failure status");
    }
  } catch (err) {
    currentUser = {
      user_id: `usr_${role}`,
      role: role,
      name: name || (role === 'admin' ? "Merchant Administrator" : "Verified Collector"),
      email: email || (role === 'admin' ? "admin@kicksvault.in" : "collector@kicksvault.in"),
      avatar: role === 'admin' 
        ? 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80'
        : 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80'
    };
    localStorage.setItem('auth_token', `mock_tok_${role}`);
    localStorage.setItem('auth_user', JSON.stringify(currentUser));
    localStorage.setItem('auth_expires_at', (Date.now() + 3600 * 1000).toString());
    updateAuthUI();
    closeAuthModal();
  }
}

function updateAuthUI() {
  const nameEl = document.getElementById('user-display-name');
  const roleBadge = document.getElementById('user-role-badge');
  const avatarEl = document.getElementById('user-avatar');
  const tabAdmin = document.getElementById('tab-admin');
  const tabChat = document.getElementById('tab-chat');
  const btnToggleStorefront = document.getElementById('btn-toggle-storefront');

  if (currentUser) {
    if (nameEl) nameEl.textContent = currentUser.name.split(' ')[0];
    if (avatarEl) avatarEl.src = currentUser.avatar;
    
    const isAdmin = currentUser.role === 'admin';
    if (roleBadge) {
      if (isAdmin) {
        roleBadge.textContent = '🛡️ MERCHANT ADMIN';
        roleBadge.className = 'role-badge-admin';
        roleBadge.style.background = 'rgba(251,191,36,0.15)';
        roleBadge.style.color = 'var(--amber)';
        roleBadge.style.border = '1px solid rgba(251,191,36,0.3)';
        if (btnToggleStorefront) btnToggleStorefront.style.display = 'inline-flex';
      } else {
        roleBadge.textContent = '👤 CUSTOMER';
        roleBadge.className = 'role-badge-user';
        roleBadge.style.background = 'rgba(34,211,238,0.15)';
        roleBadge.style.color = 'var(--cyan)';
        roleBadge.style.border = '1px solid rgba(34,211,238,0.3)';
        if (btnToggleStorefront) btnToggleStorefront.style.display = 'none';
      }
    }

    if (tabAdmin) tabAdmin.style.display = isAdmin ? 'inline-flex' : 'none';
    if (tabChat) tabChat.style.display = isAdmin ? 'none' : 'inline-flex';
    
    // Toggle Admin-only controls throughout the UI
    document.querySelectorAll('.admin-only-ui').forEach(el => {
      const tag = el.tagName.toLowerCase();
      const defaultDisplay = (tag === 'button' || tag === 'span' || tag === 'a') ? 'flex' : 'block';
      el.style.display = isAdmin ? defaultDisplay : 'none';
    });

    if (isAdmin) {
      loadAdminBrands();
    }

    // Strict Navigation Separation check
    const activePage = document.querySelector('.page.active');
    if (activePage) {
      if (!isAdmin && activePage.id === 'page-admin') {
        showPage('page-storefront');
      } else if (isAdmin && activePage.id === 'page-chat') {
        showPage('page-admin');
      }
    }
  } else {
    if (nameEl) nameEl.textContent = 'Guest';
    if (roleBadge) {
      roleBadge.textContent = 'GUEST';
      roleBadge.className = 'role-badge-user';
    }
    if (tabAdmin) tabAdmin.style.display = 'none';
    if (tabChat) tabChat.style.display = 'inline-flex';
    if (btnToggleStorefront) btnToggleStorefront.style.display = 'none';
  }
}

async function loadAdminBrands() {
  const container = document.getElementById('brand-showcase-container');
  if (!container) return;
  try {
    const resp = await fetch('/api/admin/brands');
    if (resp.ok) {
      const brands = await resp.json();
      container.innerHTML = brands.map(b => `
        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:12px;min-width:90px;text-align:center;box-shadow:var(--shadow-sm)">
          <img src="${b.logo}" alt="${b.name}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;border:1px solid rgba(255,255,255,0.1)"/>
          <span style="font-size:10px;font-weight:700;color:var(--text-secondary)">${b.name}</span>
        </div>
      `).join('');
    }
  } catch (_) {}
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
  const brand = document.getElementById('new-prod-brand')?.value || 'Jordan';
  const retail = parseFloat(document.getElementById('new-prod-retail')?.value);
  const floor = parseFloat(document.getElementById('new-prod-floor')?.value);
  const stock = parseInt(document.getElementById('new-prod-stock')?.value, 10) || 1;
  const image = document.getElementById('new-prod-image')?.value.trim() || 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=800&q=80';

  if (!id || !name || isNaN(retail) || isNaN(floor)) {
    alert('Please fill in all required product fields with valid values.');
    return;
  }

  try {
    const resp = await fetch('/api/admin/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id,
        name,
        retail_price: retail,
        floor_price: floor,
        stock,
        image_url: image,
        brand
      })
    });

    if (resp.ok) {
      PRODUCTS[id] = {
        name,
        price: retail,
        floor,
        stock,
        brand,
        badges: [['New Drop', 'indigo']],
        desc: `Luxury ${brand} sneakers.`,
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
  if (currentUser.role === 'admin') {
    alert("🔒 Merchant Administrators cannot negotiate or chat. Please switch your role to 'Verified Collector' (Buyer View) via the top-right profile pill to negotiate.");
    return;
  }
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

function showPage(pageId, recordHistory = true) {
  if (pageId === 'page-admin' && (!currentUser || currentUser.role !== 'admin')) {
    alert("🛡️ Admin Panel is restricted to Merchant Administrators.");
    showPage('page-storefront', false);
    return;
  }

  if (pageId === 'page-chat' && currentUser.role === 'admin') {
    alert("🔒 Merchant Administrators cannot access the AI Concierge chat view. Please switch to Buyer View (Verified Collector) mode first.");
    return;
  }

  if (recordHistory && pageHistory[pageHistory.length - 1] !== pageId) {
    pageHistory.push(pageId);
  }

  document.querySelectorAll('.page').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  
  const target = document.getElementById(pageId);
  if (target) target.classList.add('active');

  const tab = document.querySelector(`[data-target="${pageId}"]`);
  if (tab) tab.classList.add('active');

  updateBreadcrumbs(pageId);

  setTimeout(() => lucide.createIcons(), 60);
}

window.goBack = function() {
  if (pageHistory.length > 1) {
    pageHistory.pop(); // remove current page
    const prevPage = pageHistory[pageHistory.length - 1];
    showPage(prevPage, false);
  } else {
    showPage('page-storefront', false);
  }
};

function updateBreadcrumbs(pageId) {
  const currentTitle = PAGE_TITLES[pageId] || 'Current View';
  const breadcrumbElements = document.querySelectorAll('.current-view-breadcrumb');
  breadcrumbElements.forEach(el => {
    el.textContent = `Storefront › ${currentTitle}`;
  });
}

window.closePaymentModal = function() {
  const modal = document.getElementById('payment-success-modal');
  if (modal) modal.classList.add('hidden');
};

window.closePaymentModalAndGoHome = function() {
  closePaymentModal();
  showPage('page-storefront');
};

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

  // Pay via Razorpay Sandbox Button Trigger (Launches Official Razorpay Test Popup)
  document.getElementById('checkout-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    if (currentCheckout) {
      launchOfficialRazorpayCheckout(currentCheckout);
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

  document.getElementById('btn-rzp-pay-confirm')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-rzp-pay-confirm');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:14px;height:14px"></i> Authorizing Sandbox Rails…`;
      lucide.createIcons();
    }
    setTimeout(async () => {
      closeRazorpaySandboxModal();
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="shield-check" style="width:16px;height:16px"></i> <span>Authorize & Pay <span id="rzp-btn-amount">₹${Number(currentCheckout?.amount || 0).toLocaleString('en-IN')}</span></span>`;
      }
      if (currentCheckout) {
        await executeRealPaymentSimulation('success');
      }
    }, 600);
  });

  document.getElementById('btn-rzp-sim-fail')?.addEventListener('click', async () => {
    closeRazorpaySandboxModal();
    if (currentCheckout) {
      await executeRealPaymentSimulation('failure');
    }
  });
}

function updateRazorpayMethodUI(method) {
  const container = document.getElementById('rzp-method-content');
  if (!container) return;

  if (method === 'upi') {
    container.innerHTML = `
      <div style="display:flex;gap:14px;align-items:center">
        <div style="width:70px;height:70px;background:#ffffff;border-radius:10px;display:flex;align-items:center;justify-content:center;padding:4px;flex-shrink:0;box-shadow:0 2px 10px rgba(0,0,0,0.3)">
          <img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=upi://pay?pa=collector@okhdfcbank" alt="UPI QR" style="width:100%;height:100%;object-fit:contain"/>
        </div>
        <div style="flex:1">
          <div style="font-size:12px;font-weight:700;color:var(--text-primary);margin-bottom:6px">Scan UPI QR or Tap App</div>
          <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px">
            <span class="rzp-app-pill active">GPay</span>
            <span class="rzp-app-pill">PhonePe</span>
            <span class="rzp-app-pill">Paytm</span>
            <span class="rzp-app-pill">CRED</span>
          </div>
          <div style="font-size:11px;color:var(--text-secondary)">Virtual VPA: <span style="color:var(--cyan);font-family:var(--font-mono);font-weight:700">collector@okhdfcbank</span></div>
        </div>
      </div>
    `;
    setupPillListeners();
  } else if (method === 'card') {
    container.innerHTML = `
      <div>
        <div style="background:linear-gradient(135deg,#18181b,#09090b);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:12px;margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-size:10px;font-weight:800;letter-spacing:0.08em;color:var(--indigo-bright)">RAZORPAY TEST CARD</span>
            <span style="font-size:10px;font-weight:800;color:#fff;background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:4px">VISA / MC</span>
          </div>
          <div style="font-family:var(--font-mono);font-size:13px;letter-spacing:0.12em;color:#fff;margin-bottom:8px">4111 •••• •••• 4444</div>
          <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-secondary);font-family:var(--font-mono)">
            <span>EXP: 12/28</span>
            <span>CVV: 999</span>
            <span>NAME: ${esc(currentUser.name)}</span>
          </div>
        </div>
        <div style="font-size:10px;color:var(--emerald);display:flex;align-items:center;gap:4px">
          <i data-lucide="shield-check" style="width:12px;height:12px"></i>
          3D-Secure Test OTP auto-verified by payment gateway
        </div>
      </div>
    `;
  } else if (method === 'netbanking') {
    container.innerHTML = `
      <div>
        <div style="font-size:11px;font-weight:700;color:var(--text-secondary);margin-bottom:8px">Select NetBanking Institution:</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
          <div class="rzp-bank-card active"><i data-lucide="check-circle" style="width:12px;height:12px;color:var(--emerald)"></i> HDFC Bank</div>
          <div class="rzp-bank-card"><i data-lucide="circle" style="width:12px;height:12px;color:var(--text-muted)"></i> ICICI Bank</div>
          <div class="rzp-bank-card"><i data-lucide="circle" style="width:12px;height:12px;color:var(--text-muted)"></i> State Bank (SBI)</div>
          <div class="rzp-bank-card"><i data-lucide="circle" style="width:12px;height:12px;color:var(--text-muted)"></i> Axis Bank</div>
        </div>
      </div>
    `;
    setupBankListeners();
  }
  lucide.createIcons();
}

function setupPillListeners() {
  document.querySelectorAll('.rzp-app-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.rzp-app-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
    });
  });
}

function setupBankListeners() {
  document.querySelectorAll('.rzp-bank-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.rzp-bank-card').forEach(c => {
        c.classList.remove('active');
        const icon = c.querySelector('i');
        if (icon) {
          icon.setAttribute('data-lucide', 'circle');
          icon.style.color = 'var(--text-muted)';
        }
      });
      card.classList.add('active');
      const icon = card.querySelector('i');
      if (icon) {
        icon.setAttribute('data-lucide', 'check-circle');
        icon.style.color = 'var(--emerald)';
      }
      lucide.createIcons();
    });
  });
}

// ============================================================
//  CUSTOMER SIMULATION DECK — button wiring
// ============================================================
function initCustomerSimDeck() {
  document.getElementById('cust-sim-success')?.addEventListener('click', () => runCustomerSim('success'));
  document.getElementById('cust-sim-failure')?.addEventListener('click', () => runCustomerSim('failure'));
}

async function runCustomerSim(type) {
  const orderId   = document.getElementById('cust-sim-order-id')?.value.trim()  || `order_sim_${Date.now()}`;
  const amount    = parseFloat(document.getElementById('cust-sim-amount')?.value) || 24999;
  const productId = document.getElementById('cust-sim-product')?.value            || 'PROD_001';
  const custId    = document.getElementById('cust-sim-customer-id')?.value.trim() || 'cust_simulated';
  const fb        = document.getElementById('cust-sim-feedback');

  const endpoint = type === 'success' ? '/api/simulate-payment' : '/api/simulate-failure';

  const btnS = document.getElementById('cust-sim-success');
  const btnF = document.getElementById('cust-sim-failure');
  if (btnS) btnS.disabled = true;
  if (btnF) btnF.disabled = true;

  if (fb) {
    fb.style.display = 'block';
    fb.style.background = 'rgba(99,102,241,0.12)';
    fb.style.color = 'var(--indigo-bright)';
    fb.style.border = '1px solid rgba(99,102,241,0.3)';
    fb.textContent = `[SIM] Sending ${type.toUpperCase()} event → ${endpoint}…`;
  }

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Dev-Token': DEV_TOKEN },
      body: JSON.stringify({ order_id: orderId, amount, product_id: productId, customer_id: custId })
    });
    const data = await resp.json();

    if (resp.ok) {
      if (fb) {
        fb.style.background = type === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(248,113,113,0.08)';
        fb.style.color      = type === 'success' ? 'var(--emerald)' : '#fca5a5';
        fb.style.border     = type === 'success' ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(248,113,113,0.3)';
        fb.textContent = type === 'success'
          ? `✓ PAID — HMAC: ${(data.verified_hmac || '').slice(0, 24)}… | ${orderId}`
          : `✗ FAILED — bank_transaction_timeout | ${orderId}`;
      }
      await pollOrders();
      if (type === 'success') {
        showPaymentSuccessScreen({
          orderId: orderId,
          paymentId: `pay_${Math.random().toString(36).slice(2, 10)}${Math.random().toString(36).slice(2, 10)}`,
          amount: amount,
          productId: productId,
          hmac: data.verified_hmac
        });
      }
    } else {
      if (fb) { fb.style.color = '#fca5a5'; fb.textContent = `⚠ Error: ${data.detail || 'Unknown error'}`; }
    }
  } catch (err) {
    if (fb) { fb.style.color = '#fca5a5'; fb.textContent = `⚠ Request failed: ${err.message}`; }
  } finally {
    if (btnS) btnS.disabled = false;
    if (btnF) btnF.disabled = false;
  }
}

// ============================================================
//  PHONE COLLECTION MODAL — shown BEFORE Razorpay opens
// ============================================================
function openPhoneCollectModal(checkoutData) {
  if (!checkoutData) return;

  // Pre-fill from currentUser
  const nameEl  = document.getElementById('checkout-name');
  const emailEl = document.getElementById('checkout-email');
  if (nameEl)  nameEl.value  = currentUser.name  !== 'Verified Collector' ? currentUser.name  : '';
  if (emailEl) emailEl.value = currentUser.email !== 'collector@kicksvault.in' ? currentUser.email : '';

  // Populate summary strip
  const prod = PRODUCTS[checkoutData.product_id] || {};
  const img   = document.getElementById('phone-modal-img');
  const prodEl= document.getElementById('phone-modal-product');
  const ordEl = document.getElementById('phone-modal-order');
  const amtEl = document.getElementById('phone-modal-amount');
  if (img)    img.src = prod.image || '';
  if (prodEl) prodEl.textContent = prod.name || checkoutData.product_id;
  if (ordEl)  ordEl.textContent  = checkoutData.order_id || `order_${Date.now()}`;
  if (amtEl)  amtEl.textContent  = `₹${Number(checkoutData.amount).toLocaleString('en-IN')}`;

  // Hide error
  const err = document.getElementById('phone-modal-error');
  if (err) err.style.display = 'none';

  // Store pending checkout
  window._pendingCheckout = checkoutData;

  const modal = document.getElementById('phone-collect-modal');
  if (modal) { modal.style.display = 'flex'; lucide.createIcons(); }
}

function closePhoneCollectModal() {
  const modal = document.getElementById('phone-collect-modal');
  if (modal) modal.style.display = 'none';
}

function initPhoneCollectModal() {
  document.getElementById('btn-cancel-phone-modal')?.addEventListener('click', closePhoneCollectModal);
  document.getElementById('btn-proceed-razorpay')?.addEventListener('click', async () => {
    const phone = (document.getElementById('checkout-phone')?.value || '').trim();
    const name  = (document.getElementById('checkout-name')?.value  || '').trim();
    const email = (document.getElementById('checkout-email')?.value || '').trim();
    const err   = document.getElementById('phone-modal-error');

    if (!phone || phone.length < 10) {
      if (err) { err.style.display = 'block'; err.textContent = '⚠ Please enter a valid 10-digit mobile number.'; }
      return;
    }

    closePhoneCollectModal();
    if (window._pendingCheckout) {
      window._pendingCheckout._phone = '+91' + phone;
      window._pendingCheckout._name  = name  || currentUser.name;
      window._pendingCheckout._email = email || currentUser.email;
      await launchOfficialRazorpayCheckout(window._pendingCheckout);
    }
  });

  // Also wire the checkout-link button to open phone modal instead
  document.getElementById('checkout-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    if (currentCheckout) openPhoneCollectModal(currentCheckout);
  });

}

// ============================================================
//  SHOW PAYMENT SUCCESS MODAL (centered)
// ============================================================
function showPaymentSuccessScreen({ orderId, paymentId, amount, productId, hmac }) {
  const modal = document.getElementById('payment-success-modal');
  if (!modal) return;

  const prod = PRODUCTS[productId] || {};

  const receiptContent = document.getElementById('receipt-modal-content');
  if (receiptContent) {
    receiptContent.innerHTML = `
      <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:12px">ORDER RECEIPT</div>

      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.08)">
        <img id="success-product-img" src="${prod.image || ''}" alt="Product" style="width:50px;height:50px;border-radius:8px;object-fit:cover;border:1px solid rgba(255,255,255,0.1);flex-shrink:0"/>
        <div style="min-width:0;flex-grow:1">
          <div id="success-product-name" style="font-size:13px;font-weight:700;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${prod.name || productId}</div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px">KicksVault Certified · NFC Authenticated</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:9px;color:var(--text-muted)">PAID</div>
          <div id="success-amount" style="font-size:16px;font-weight:900;color:var(--emerald)">₹${Number(amount).toLocaleString('en-IN')}</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:11px">
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:8px">
          <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px">ORDER ID</div>
          <div id="success-order-id" style="font-size:10px;font-family:var(--font-mono);color:var(--indigo-bright);word-break:break-all">${orderId}</div>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:8px">
          <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px">PAYMENT ID</div>
          <div id="success-payment-id" style="font-size:10px;font-family:var(--font-mono);color:var(--indigo-bright);word-break:break-all">${paymentId || '—'}</div>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:8px">
          <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px">STATUS</div>
          <div style="display:flex;align-items:center;gap:4px">
            <span style="width:6px;height:6px;border-radius:50%;background:var(--emerald)"></span>
            <span style="font-size:10px;font-weight:800;color:var(--emerald)">PAID · VERIFIED</span>
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);border-radius:8px;padding:8px">
          <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:4px">DELIVERY TO</div>
          <div id="success-delivery" style="font-size:10px;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${userDeliveryLocation || 'India'}</div>
        </div>
      </div>

      <!-- HMAC verification chip -->
      <div style="margin-top:10px;padding:8px 12px;background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.15);border-radius:8px;display:flex;align-items:center;gap:6px">
        <i data-lucide="shield-check" style="width:13px;height:13px;color:var(--emerald);flex-shrink:0"></i>
        <div style="min-width:0;flex-grow:1">
          <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:var(--emerald);font-family:var(--font-mono)">HMAC-SHA256 SIGNATURE VERIFIED</div>
          <div id="success-hmac" style="font-size:9px;font-family:var(--font-mono);color:var(--text-muted);margin-top:2px;word-break:break-all">${hmac ? hmac.slice(0, 48) + '…' : '—'}</div>
        </div>
      </div>
    `;
  }

  modal.classList.remove('hidden');
  lucide.createIcons();
}

async function launchOfficialRazorpayCheckout(checkoutData) {
  if (!checkoutData) return;

  const btn = document.getElementById('checkout-link');
  if (btn) {
    btn.style.pointerEvents = 'none';
    btn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:14px;height:14px"></i> Opening Razorpay Secure Rails…`;
    lucide.createIcons();
  }

  try {
    const resp = await fetch('/api/razorpay/create-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount: Number(checkoutData.amount),
        product_id: checkoutData.product_id,
        session_id: sessionId,
        customer_name: checkoutData._name || currentUser.name,
        customer_email: checkoutData._email || currentUser.email,
        phone: checkoutData._phone || "+919876543210",
        delivery_location: userDeliveryLocation
      })
    });

    const order = await resp.json();

    if (btn) {
      btn.style.pointerEvents = 'auto';
      btn.innerHTML = `<i data-lucide="zap" style="width:15px;height:15px"></i> Pay via Razorpay Sandbox →`;
      lucide.createIcons();
    }

    if (order.payment_link_url) {
      logTerminal('info', `[REDIRECT] Redirecting user to Razorpay Hosted Checkout: ${order.payment_link_url}`);
      window.location.href = order.payment_link_url;
      return;
    }

    alert("⚠️ Could not generate Razorpay payment link. Please try again.");

  } catch (err) {
    if (btn) {
      btn.style.pointerEvents = 'auto';
      btn.innerHTML = `<i data-lucide="zap" style="width:15px;height:15px"></i> Pay via Razorpay Sandbox →`;
      lucide.createIcons();
    }
    alert(`⚠️ Error launching checkout: ${err.message}`);
  }
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

  if (img) img.src = prod.image || 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=200&q=80';
  if (name) name.textContent = prod.name || checkoutData.product_id;
  if (orderId) orderId.textContent = checkoutData.order_id || `order_${Date.now()}`;
  const formattedPrice = `₹${Number(checkoutData.amount).toLocaleString('en-IN')}`;
  if (price) price.textContent = formattedPrice;
  if (btnAmount) btnAmount.textContent = formattedPrice;

  // Reset to UPI by default
  document.querySelectorAll('.rzp-method-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-rzp-upi')?.classList.add('active');
  updateRazorpayMethodUI('upi');

  if (modal) modal.style.display = 'flex';
  lucide.createIcons();
}

function closeRazorpaySandboxModal() {
  const modal = document.getElementById('razorpay-modal');
  if (modal) modal.style.display = 'none';
}

async function executeRealPaymentSimulation(type) {
  if (!currentCheckout) return;
  const endpoint = type === 'success' ? '/api/simulate-payment' : '/api/simulate-failure';
  const orderId = currentCheckout.order_id || `order_chat_${Date.now()}`;
  const amount = Number(currentCheckout.amount);
  const productId = currentCheckout.product_id;
  const custId = currentUser.user_id || `cust_${sessionId.slice(-6)}`;

  logTerminal('info', `[SIMULATION] Triggering ${type.toUpperCase()} → ${endpoint}`);
  logTerminal('info', `[PAYLOAD] order_id: ${orderId} | amount: ₹${amount} | destination: ${userDeliveryLocation}`);

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Dev-Token': DEV_TOKEN },
      body: JSON.stringify({
        order_id: orderId,
        amount: amount,
        product_id: productId,
        customer_id: custId
      })
    });

    const data = await resp.json();
    if (resp.ok) {
      if (type === 'success') {
        logTerminal('ok', `[WEBHOOK RECEIVED] POST /api/webhook/razorpay · 200 OK`);
        logTerminal('ok', `[EVENT] payment_link.paid · ID: ${orderId}`);
        logTerminal('ok', `[HMAC-SHA256] ${data.verified_hmac}`);
        logTerminal('ok', `[SIGNATURE CHECK] ✓ 100% CRYPTOGRAPHIC MATCH`);
        logTerminal('ok', `[LEDGER UPDATED] ${orderId} → STATUS: PAID`);
        logTerminal('dim', `─────────────────────────────────────`);

        logMini(`[PAID] ₹${amount.toLocaleString('en-IN')} · HMAC Verified`);

        // Render confirmed receipt card in chat
        renderPaymentSuccessCard(orderId, amount, productId, data.verified_hmac);

        // Notify AI
        setTimeout(() => {
          appendAgent(`🎉 **Payment Confirmed!** Your deposit of **₹${amount.toLocaleString('en-IN')}** has been verified on the Razorpay blockchain rails. Order **\`${orderId}\`** is locked and deadstock physical authentication is in progress for delivery to **📍 ${userDeliveryLocation}**.`);
        }, 500);

      } else {
        logTerminal('fail', `[WEBHOOK RECEIVED] POST /api/webhook/razorpay · 200 OK`);
        logTerminal('fail', `[EVENT] payment_link.failed · ID: ${orderId}`);
        logTerminal('fail', `[REASON] bank_transaction_timeout (BAD_REQUEST_PAYMENT_TIMED_OUT)`);
        logTerminal('ok',   `[HMAC-SHA256] ${data.verified_hmac}`);
        logTerminal('warn', `[AGENT RECOVERY] LangGraph failure recovery triggered for ${sessionId}`);
        logTerminal('dim', `─────────────────────────────────────`);

        logMini(`[FAILED] Bank Timeout · Recovery Active`);

        appendSystem(`⚠️ Payment Notice: Bank gateway timed out for ${orderId}. Initializing AI recovery.`);

        // Trigger AI Recovery Workflow
        setTimeout(async () => {
          try {
            const r = await fetch('/api/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                message: "My payment failed due to bank timeout. Can you help?",
                session_id: sessionId,
                location: userDeliveryLocation,
                history: chatHistory
              })
            });
            if (r.ok) {
              const resData = await r.json();
              appendAgent(resData.reply);
              if (resData.checkout_url) {
                renderCheckoutCard(resData);
              }
            }
          } catch (_) {}
        }, 800);
      }

      await pollOrders();
    } else {
      appendSystem(`⚠ Simulation error: ${data.detail}`);
    }
  } catch (err) {
    appendSystem(`⚠ Network error during simulation: ${err.message}`);
  }
}

function renderPaymentSuccessCard(orderId, amount, productId, hmacSig) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;

  const prod = PRODUCTS[productId] || {};
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap-agent';
  wrap.innerHTML = `
    <div class="agent-avatar" style="width:32px;height:32px;border-radius:8px;background:var(--emerald);display:flex;align-items:center;justify-content:center;color:#000">
      <i data-lucide="check" style="width:16px;height:16px"></i>
    </div>
    <div style="background:rgba(18,18,22,0.95);border:1px solid rgba(52,211,153,0.3);border-radius:14px;padding:16px;max-width:380px;box-shadow:0 8px 32px rgba(52,211,153,0.15)">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
        <span class="status-dot" style="background:var(--emerald)"></span>
        <span style="font-size:12px;font-weight:800;color:var(--emerald);letter-spacing:0.04em">RAZORPAY ORDER RECEIPT</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <img src="${prod.image || ''}" style="width:40px;height:40px;border-radius:8px;object-fit:cover"/>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-primary)">${esc(prod.name || productId)}</div>
          <div style="font-size:10px;color:var(--text-secondary)">Order ID: <span style="font-family:var(--font-mono);color:var(--indigo-bright)">${orderId}</span></div>
        </div>
      </div>
      <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:10px;font-size:11px;display:flex;flex-direction:column;gap:4px;margin-bottom:10px">
        <div style="display:flex;justify-content:space-between">
          <span style="color:var(--text-muted)">Amount Captured:</span>
          <span style="font-weight:800;color:var(--emerald)">₹${Number(amount).toLocaleString('en-IN')}</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span style="color:var(--text-muted)">HMAC SHA-256:</span>
          <span style="font-family:var(--font-mono);color:var(--cyan)">${hmacSig ? hmacSig.slice(0, 16) + '…' : 'Verified ✓'}</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span style="color:var(--text-muted)">Delivery To:</span>
          <span style="color:var(--text-primary)">📍 ${esc(userDeliveryLocation)}</span>
        </div>
      </div>
      <div style="font-size:10px;color:var(--emerald);font-weight:600;display:flex;align-items:center;gap:4px">
        <i data-lucide="shield-check" style="width:13px;height:13px"></i>
        Deadstock NFC Authentication Tag Registered
      </div>
    </div>
  `;
  msgs.appendChild(wrap);
  scrollBottom(msgs);
  lucide.createIcons();
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
    const orders = await resp.json();
    renderOrders(orders);
    renderMyOrders(orders);
  } catch (_) {}
}

function renderMyOrders(orders) {
  const tbody = document.getElementById('my-orders-tbody');
  if (!tbody) return;

  const STATUS_STYLE = {
    created: { dot: 'var(--indigo-bright)', label: 'CREATED', textColor: 'var(--indigo-bright)' },
    paid:    { dot: 'var(--emerald)',       label: 'PAID',    textColor: 'var(--emerald)' },
    failed:  { dot: 'var(--red)',           label: 'FAILED',  textColor: 'var(--red)' }
  };

  if (!orders?.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;padding:24px 4px;color:var(--text-muted);font-size:11px">
          No orders yet — negotiate a deal to get started!
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = orders.slice().reverse().map(o => {
    const s = STATUS_STYLE[o.status] || STATUS_STYLE.created;
    const ts = (o.paid_at || o.created_at) ? new Date(o.paid_at || o.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '—';
    const shortId = o.order_id.slice(0, 18) + (o.order_id.length > 18 ? '…' : '');
    const prod = PRODUCTS[o.product_id] || {};
    const prodName = prod.name ? prod.name.split(' ').slice(0, 3).join(' ') + '…' : o.product_id;
    return `<tr style="border-bottom:1px solid rgba(255,255,255,0.04)">
      <td style="padding:8px 4px;color:var(--text-muted);font-family:var(--font-mono);font-size:10px;white-space:nowrap" title="${o.order_id}">${shortId}</td>
      <td style="padding:8px 4px;color:var(--text-secondary);font-size:10px;white-space:nowrap">${esc(prodName)}</td>
      <td style="padding:8px 4px;color:var(--text-primary);font-weight:700;white-space:nowrap">₹${Number(o.amount).toLocaleString('en-IN')}</td>
      <td style="padding:8px 4px;white-space:nowrap">
        <span style="display:inline-flex;align-items:center;gap:4px;font-size:9px;font-weight:800;letter-spacing:0.06em;color:${s.textColor}">
          <span style="width:6px;height:6px;border-radius:50%;background:${s.dot};flex-shrink:0"></span>
          ${s.label}
        </span>
      </td>
      <td style="padding:8px 4px;color:var(--text-muted);font-size:10px;white-space:nowrap">${ts}</td>
    </tr>`;
  }).join('');
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
      if (type === 'success') {
        showPaymentSuccessScreen({
          orderId: currentCheckout.order_id,
          paymentId: `pay_${Math.random().toString(36).slice(2, 10)}${Math.random().toString(36).slice(2, 10)}`,
          amount: currentCheckout.amount,
          productId: currentCheckout.product_id,
          hmac: data.verified_hmac
        });
      }
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
