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

// ── Lazy image loading (scroll-based for #main-frame compat) ───
function initLazyImages() {
  var scrollEl = document.getElementById('main-frame') || null;

  function loadImg(img) {
    if (!img.dataset.src) return;
    img.src = img.dataset.src;
    img.removeAttribute('data-src');
    img.onload = function() {
      img.classList.add('loaded');
      var p = img.closest('.img-skeleton');
      if (p) p.classList.add('loaded');
    };
    img.onerror = function() {
      var p = img.closest('.img-skeleton');
      if (p) p.innerHTML = '<div class="img-error">📷</div>';
    };
  }

  function check() {
    var imgs = document.querySelectorAll('img[data-src]');
    var viewH = scrollEl ? scrollEl.clientHeight : window.innerHeight;
    imgs.forEach(function(img) {
      if (!img.dataset.src) return;
      var rect = img.getBoundingClientRect();
      if (rect.top < viewH + 300 && rect.bottom > -300) loadImg(img);
    });
  }

  check();
  (scrollEl || window).addEventListener('scroll', check, { passive: true });
  setTimeout(check, 500);
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

// ── Card entrance animation (CSS-only, no IntersectionObserver) ─
function initCardAnimations() {
  // Animation pure CSS pour éviter le bug opacity:0 avec #main-frame
  var cards = document.querySelectorAll('.annonce-card');
  cards.forEach(function(card) { card.classList.add('annonce-card--visible'); });
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
      labelInput.placeholder = 'Prix sur demande';
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

// ── Bouton favori ♡ sur les cards d'annonces (AJAX) ───────────
function initCardFavButtons() {
  document.querySelectorAll('.annonce-card__fav-btn').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      e.preventDefault();
      var authenticated = btn.dataset.authenticated === 'true';
      if (!authenticated) {
        window.location.href = '/users/login/';
        return;
      }
      var pk = btn.dataset.pk;
      // Animation battement de cœur
      btn.classList.remove('annonce-card__fav-btn--beat');
      void btn.offsetWidth; // force reflow pour relancer l'animation
      btn.classList.add('annonce-card__fav-btn--beat');
      btn.addEventListener('animationend', function() {
        btn.classList.remove('annonce-card__fav-btn--beat');
      }, { once: true });
      // Récupération du token CSRF (CSRF_COOKIE_HTTPONLY=True → lecture depuis le DOM)
      var csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
      var csrfToken = csrfEl ? csrfEl.value : '';
      // AJAX vers toggle_enregistrement
      fetch('/annonces/toggle-enregistrement/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ annonce_id: parseInt(pk, 10) }),
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.saved !== undefined) {
          btn.dataset.saved = data.saved ? 'true' : 'false';
          var icon = btn.querySelector('.annonce-card__fav-icon');
          if (data.saved) {
            btn.classList.add('annonce-card__fav-btn--saved');
            if (icon) icon.setAttribute('fill', '#fff');
          } else {
            btn.classList.remove('annonce-card__fav-btn--saved');
            if (icon) icon.setAttribute('fill', 'none');
          }
        }
      })
      .catch(function() {});
    });
  });
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
  initCardFavButtons();

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
    form.addEventListener('submit', function(e) {
      // Si le submit a été annulé (ex: confirm() → Annuler), ne rien faire
      if (e.defaultPrevented) return;
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

// ── Stop propagation for inner links (CSP-compliant) ─────────
// Replaces inline onclick="event.stopPropagation()" on elements
// like seller avatar links inside card wrappers.
document.addEventListener('click', function(e) {
  var el = e.target.closest('.js-stop-propagation');
  if (el) e.stopPropagation();
});

// ── Admin stats link in slide menu (for staff) ─────────────────
// (handled server-side via is_staff check in template)

