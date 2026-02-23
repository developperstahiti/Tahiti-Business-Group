/* ================================================================
   TAHITI BUSINESS GROUPE — Frontend JS Jour 3
   Lazy loading · Scroll fluide · Toasts · Interactions
   ================================================================ */

'use strict';

// ── Toast notification ─────────────────────────────────────────
function showToast(msg, type = 'info') {
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span style="font-size:1.1em;font-weight:700">${icons[type] || 'ℹ'}</span> ${msg}`;
  document.body.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateX(120px)';
    t.style.transition = 'all .3s ease';
    setTimeout(() => t.remove(), 300);
  }, 3800);
}

// ── Lazy image loading (IntersectionObserver) ──────────────────
function initLazyImages() {
  const imgs = document.querySelectorAll('img[data-src]');
  if (!imgs.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        img.onload = () => img.classList.add('loaded');
        observer.unobserve(img);
      }
    });
  }, { rootMargin: '200px 0px' });

  imgs.forEach(img => observer.observe(img));
}

// ── Auto-dismiss Django messages ───────────────────────────────
function initAutoDismissMessages() {
  const container = document.querySelector('#django-messages');
  if (!container) return; // Pas de messages, rien à faire
  setTimeout(() => {
    container.style.transition = 'opacity .5s';
    container.style.opacity = '0';
    setTimeout(() => container.remove(), 500);
  }, 5000);
}

// ── Card entrance animation ────────────────────────────────────
function initCardAnimations() {
  const cards = document.querySelectorAll('.ad-card');
  if (!cards.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, i * 40);
        observer.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -40px 0px' });

  cards.forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity .4s ease, transform .4s ease';
    observer.observe(card);
  });
}

// ── Photo gallery ──────────────────────────────────────────────
function initPhotoGallery() {
  const mainPhoto = document.getElementById('mainPhoto');
  if (!mainPhoto) return;
  document.querySelectorAll('.photo-thumb').forEach(thumb => {
    thumb.addEventListener('click', () => {
      mainPhoto.style.opacity = '0';
      setTimeout(() => {
        mainPhoto.src = thumb.src;
        mainPhoto.style.opacity = '1';
        mainPhoto.style.transition = 'opacity .25s';
      }, 150);
      document.querySelectorAll('.photo-thumb').forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
  });
}

// ── Search form auto-submit on category change ─────────────────
function initSearchAutoSubmit() {
  const catSelect = document.querySelector('nav select[name="categorie"]');
  if (catSelect) {
    catSelect.addEventListener('change', () => catSelect.closest('form').submit());
  }
}

// ── Scroll to top button ───────────────────────────────────────
function initScrollToTop() {
  const btn = document.createElement('button');
  btn.innerHTML = '↑';
  btn.className = 'fixed bottom-6 left-6 w-10 h-10 bg-white border border-gray-200 shadow-lg rounded-full text-gray-500 hover:text-blue-600 hover:border-blue-300 transition text-lg font-bold z-40 opacity-0 pointer-events-none';
  btn.setAttribute('aria-label', 'Retour en haut');
  document.body.appendChild(btn);

  window.addEventListener('scroll', () => {
    if (window.scrollY > 400) {
      btn.style.opacity = '1';
      btn.style.pointerEvents = 'auto';
    } else {
      btn.style.opacity = '0';
      btn.style.pointerEvents = 'none';
    }
  }, { passive: true });

  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ── Format number inputs ───────────────────────────────────────
function initPrixInput() {
  const prixInput = document.querySelector('input[name="prix"]');
  const labelInput = document.querySelector('input[name="prix_label"]');
  if (!prixInput || !labelInput) return;

  prixInput.addEventListener('input', () => {
    const val = parseInt(prixInput.value);
    if (!isNaN(val) && val > 0 && !labelInput.value) {
      labelInput.placeholder = `${val.toLocaleString('fr-FR')} XPF`;
    } else if (val === 0 && !labelInput.value) {
      labelInput.placeholder = 'Gratuit';
    }
  });
}

// ── Smooth section reveals ────────────────────────────────────
function initSectionReveals() {
  const sections = document.querySelectorAll('section, .bg-white.border');
  if (!sections.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05 });
  sections.forEach(s => observer.observe(s));
}

// ── Main init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initLazyImages();
  initAutoDismissMessages();
  initCardAnimations();
  initPhotoGallery();
  initSearchAutoSubmit();
  initScrollToTop();
  initPrixInput();
  initSectionReveals();
  initFormSpinners();
  initFavorisCards();

  // Keyboard shortcut: / → focus search
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      const search = document.querySelector('input[name="q"]');
      if (search) { search.focus(); search.select(); }
    }
  });
});

// ── Form loading spinners ──────────────────────────────────────
function initFormSpinners() {
  document.querySelectorAll('form').forEach(form => {
    const btn = form.querySelector('button[type="submit"]');
    if (!btn || btn.dataset.noSpinner) return;
    form.addEventListener('submit', function() {
      if (!form.checkValidity()) return;
      const orig = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="btn-spinner"></span> Envoi\u2026';
      // Safety reset after 10s
      setTimeout(() => { btn.disabled = false; btn.innerHTML = orig; }, 10000);
    });
  });
}

// ── Favoris (localStorage) ─────────────────────────────────────
const FAV_KEY = 'tbg_favoris';

function getFavoris() {
  try { return JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); }
  catch { return []; }
}

function initFavorisCards() {
  document.querySelectorAll('[data-fav-pk]').forEach(btn => {
    if (btn.closest('.fav-btn')) return; // detail page handled separately
    const pk = String(btn.dataset.favPk);
    if (getFavoris().includes(pk)) btn.classList.add('fav-active');
    btn.addEventListener('click', function(e) {
      e.preventDefault(); e.stopPropagation();
      const list = getFavoris();
      const idx  = list.indexOf(pk);
      if (idx >= 0) {
        list.splice(idx, 1);
        btn.classList.remove('fav-active');
        showToast('Retiré des favoris', 'info');
      } else {
        list.push(pk);
        btn.classList.add('fav-active');
        showToast('Ajouté aux favoris \u2764\ufe0f', 'success');
      }
      localStorage.setItem(FAV_KEY, JSON.stringify(list));
    });
  });
}

// ── Admin stats link in slide menu (for staff) ─────────────────
// (handled server-side via is_staff check in template)

