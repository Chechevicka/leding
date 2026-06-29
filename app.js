/**
 * NGO Kosmos Tabir — Interactive Landing Page Logic
 * Translations are loaded from content.json at runtime.
 * Contains: Scroll-Reveals, Hero Counters, Modal Handlers, Language Toggle
 */

// ==========================================================================
// GLOBAL STATE
// ==========================================================================
let translations = { en: {}, ua: {} };
let stats = { villages: { value: 0, suffix: '+' }, households: { value: 1000, suffix: '+' }, admin_buildings: { value: 40, suffix: '+' } };
let currentLanguage = 'en';

// ==========================================================================
// LOAD CONTENT FROM content.json
// ==========================================================================
async function loadContent() {
  try {
    const res = await fetch('/content.json?v=' + Date.now());
    if (!res.ok) throw new Error('Failed to load content.json');
    const data = await res.json();
    if (data.translations) translations = data.translations;
    if (data.stats) stats = data.stats;
    return true;
  } catch (e) {
    console.warn('Could not load content.json, using fallback:', e);
    return false;
  }
}

// ==========================================================================
// LANGUAGE / TRANSLATION
// ==========================================================================
function setLanguage(lang) {
  if (lang !== 'en' && lang !== 'ua') return;
  currentLanguage = lang;

  document.getElementById('lang-en').classList.toggle('active', lang === 'en');
  document.getElementById('lang-ua').classList.toggle('active', lang === 'ua');

  const t = translations[lang] || {};
  document.querySelectorAll('[data-i18n]').forEach(elem => {
    const key = elem.getAttribute('data-i18n');
    const val = t[key];
    if (val === undefined) return;
    if (elem.tagName === 'INPUT' || elem.tagName === 'TEXTAREA') {
      elem.setAttribute('placeholder', val);
    } else if (elem.tagName === 'OPTION') {
      elem.textContent = val;
    } else {
      elem.textContent = val;
    }
  });

  localStorage.setItem('kt_lang', lang);
  document.documentElement.lang = lang === 'ua' ? 'uk' : 'en';
}

function initLanguage() {
  const saved = localStorage.getItem('kt_lang');
  if (saved === 'en' || saved === 'ua') {
    setLanguage(saved);
  } else {
    const browserLang = navigator.language || navigator.userLanguage || '';
    setLanguage(browserLang.startsWith('uk') ? 'ua' : 'en');
  }
}

// ==========================================================================
// HERO STAT COUNTERS
// ==========================================================================
function startCounters() {
  // villages
  animateStat('stat-villages', stats.villages.value, stats.villages.suffix || '+');
  // households
  animateStat('stat-households', stats.households.value, stats.households.suffix || '+');
  // admin buildings
  animateStat('stat-admin', stats.admin_buildings.value, stats.admin_buildings.suffix || '+');
}

function animateStat(id, target, suffix) {
  const el = document.getElementById(id);
  if (!el) return;
  const duration = 600;
  let startTime = null;

  function step(timestamp) {
    if (!startTime) startTime = timestamp;
    const progress = Math.min((timestamp - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = Math.floor(eased * target);
    el.textContent = (target === 0 ? '—' : current + suffix);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = (target === 0 ? '—' : target + suffix);
  }
  requestAnimationFrame(step);
}

// Trigger counters when hero stats come into view
let countersStarted = false;
const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !countersStarted) {
      startCounters();
      countersStarted = true;
      statsObserver.disconnect();
    }
  });
}, { threshold: 0.2 });

// ==========================================================================
// SCROLL REVEALS & STICKY HEADER
// ==========================================================================
const revealsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) entry.target.classList.add('active');
  });
}, { threshold: 0.1 });

let scrollTicking = false;
window.addEventListener('scroll', () => {
  if (!scrollTicking) {
    requestAnimationFrame(() => {
      const header = document.getElementById('header');
      if (header) header.classList.toggle('scrolled', window.scrollY > 40);
      scrollTicking = false;
    });
    scrollTicking = true;
  }
}, { passive: true });

// ==========================================================================
// MODAL & PARTNERSHIP CTAs
// ==========================================================================
const modal = document.getElementById('ctaModal');
const modalClose = document.getElementById('modalClose');
const successCloseBtn = document.getElementById('successCloseBtn');
const partnerForm = document.getElementById('partnerForm');
const partnerTypeSelect = document.getElementById('form-type');
const partnerTierInput = document.getElementById('partnerTierInput');
const modalFormContainer = document.getElementById('modalFormContainer');
const modalSuccessContainer = document.getElementById('modalSuccessContainer');

function openModal(tier = 'general') {
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
  if (tier) {
    partnerTierInput.value = tier;
    partnerTypeSelect.value = tier;
  }
  modalFormContainer.style.display = 'block';
  modalSuccessContainer.style.display = 'none';
}

function closeModal() {
  modal.classList.remove('active');
  document.body.style.overflow = '';
  partnerForm.reset();
}

partnerForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const submitBtn = partnerForm.querySelector('button[type="submit"]');
  const originalBtnText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = currentLanguage === 'en' ? 'Sending…' : 'Надсилання…';

  const formData = new FormData(partnerForm);

  fetch('/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(formData).toString()
  })
  .then(r => {
    if (r.ok) {
      modalFormContainer.style.display = 'none';
      modalSuccessContainer.style.display = 'flex';
    } else {
      throw new Error('Form submission failed');
    }
  })
  .catch(() => {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
    alert(currentLanguage === 'en' ? 'Failed to send. Please try again.' : 'Не вдалося надіслати. Спробуйте ще раз.');
  })
  .finally(() => {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
  });
});

// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  // Load remote content first, then apply language
  await loadContent();
  initLanguage();

  // Language toggle
  document.getElementById('langToggle').addEventListener('click', () => {
    setLanguage(currentLanguage === 'en' ? 'ua' : 'en');
  });

  // Mobile hamburger
  const navToggleBtn = document.getElementById('navToggle');
  const navMenu = document.querySelector('.nav-menu');
  if (navToggleBtn && navMenu) {
    navToggleBtn.addEventListener('click', () => navMenu.classList.toggle('open'));
    navMenu.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => navMenu.classList.remove('open'));
    });
  }

  // Proof gallery thumbnails
  const proofThumbs = document.querySelectorAll('.proof-thumb');
  const proofMainImg = document.getElementById('proofMainImg');
  if (proofMainImg) {
    proofThumbs.forEach(thumb => {
      thumb.addEventListener('click', () => {
        proofThumbs.forEach(t => t.classList.remove('active'));
        thumb.classList.add('active');
        proofMainImg.style.opacity = '0.3';
        setTimeout(() => {
          proofMainImg.src = thumb.getAttribute('data-src');
          proofMainImg.style.opacity = '1';
        }, 150);
      });
    });
  }

  // Scroll reveal animations
  document.querySelectorAll('.reveal').forEach(el => revealsObserver.observe(el));

  // Hero stat counters
  const statsRow = document.querySelector('.hero-stats');
  if (statsRow) statsObserver.observe(statsRow);

  // CTA buttons → open modal
  document.querySelectorAll('.open-cta-modal').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tier = e.currentTarget.getAttribute('data-tier') || 'general';
      openModal(tier);
      if (typeof trackEvent === 'function') trackEvent('cta_click', { tier });
    });
  });

  // Modal close
  modalClose.addEventListener('click', closeModal);
  successCloseBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

  // Escape key closes modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) closeModal();
  });
});

// --- Analytics Tracker ---
function trackEvent(event, extraData = {}) {
  const data = {
    event: event,
    language: localStorage.getItem('siteLang') || 'ua',
    referrer: document.referrer,
    ...extraData
  };
  fetch('/api/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).catch(err => console.error('Tracking error:', err));
}

// Track pageview on load
window.addEventListener('DOMContentLoaded', () => {
  let isUnique = false;
  if (!sessionStorage.getItem('visited')) {
    sessionStorage.setItem('visited', 'true');
    isUnique = true;
  }
  trackEvent('pageview', { is_unique: isUnique });
});
