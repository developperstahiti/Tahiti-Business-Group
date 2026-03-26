/**
 * LocationSelector — Sélecteur géographique interactif pour la Polynésie française
 * 3 niveaux : Île → Commune → Quartier
 * Modes : 'filter' (multi-sélection) ou 'form' (mono-sélection)
 */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════════════════════
     DONNÉES DE RÉFÉRENCE
     ═══════════════════════════════════════════════════════════════════════════ */

  const ISLANDS = [
    { id: 'tahiti',    name: 'Tahiti',    type: 'map',      emoji: '\u{1F33A}' },
    { id: 'moorea',    name: 'Moorea',    type: 'map',      emoji: '\u{1F33A}' },
    { id: 'bora-bora', name: 'Bora-Bora', type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'raiatea',   name: 'Raiatea',   type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'tahaa',     name: 'Tahaa',     type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'huahine',   name: 'Huahine',   type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'maupiti',   name: 'Maupiti',   type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'tuamotu',   name: 'Tuamotu',   type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'marquises', name: 'Marquises', type: 'dropdown', emoji: '\u{1F33A}' },
    { id: 'australes', name: 'Australes', type: 'dropdown', emoji: '\u{1F33A}' },
  ];

  const COMMUNES = {
    'tahiti': [
      'Papeete', 'Pirae', 'Arue', 'Mahina', 'Papenoo',
      'Hitiaa O Te Ra', 'Faaone', 'Taiarapu-Est',
      'Taiarapu-Ouest', 'Teva I Uta', 'Papara',
      'Paea', 'Punaauia', "Faa'a"
    ],
    'moorea': ['Afareaitu', 'Papeatoai', 'Haapiti', 'Pao Pao', 'Teavaro', 'Maiao'],
    'bora-bora': ['Anau', 'Faanui', 'Nunue', 'Vaitape'],
    'raiatea': ['Uturoa', 'Avera', 'Fetuna', 'Opoa', 'Taputapuatea', 'Tevaitoa'],
    'tahaa': ['Haamene', 'Hipu', 'Patio', 'Tiva', 'Vaitoare'],
    'huahine': ['Fare', 'Fitii', 'Haapu', 'Maeva', 'Parea'],
    'maupiti': ['Farauru', 'Haranae', 'Vaiea'],
    'tuamotu': [
      'Rangiroa', 'Fakarava', 'Tikehau', 'Manihi', 'Hao', 'Makatea',
      'Arutua', 'Kaukura', 'Gambier (Rikitea)', 'Autre Tuamotu'
    ],
    'marquises': ['Nuku Hiva', 'Hiva Oa', 'Ua Pou', 'Ua Huka', 'Tahuata', 'Fatu Hiva'],
    'australes': ['Rurutu', 'Tubuai', 'Raivavae', 'Rimatara', 'Rapa'],
  };

  const QUARTIERS = {
    'Papeete':         ['Centre-ville', 'Paofai', 'Tipaerui', 'Mamao', 'Fariipiti', 'Fare Ute', 'Motu Uta'],
    'Pirae':           ['Hamuta', 'Orofara', 'Taaone', 'Fautaua'],
    'Arue':            ['Temarii', 'One Tree Hill', 'RDO'],
    'Mahina':          ['Onoiau', 'Vaitupa', 'Mahina centre'],
    'Hitiaa O Te Ra':  ['Hitiaa', 'Mahaena', 'Tiarei', 'Papenoo est'],
    'Papenoo':         ['Papenoo centre', 'Vallee de la Papenoo'],
    'Faaone':          ['Faaone centre'],
    'Taiarapu-Est':    ['Taravao centre', 'Afaahiti', 'Pueu', 'Tautira', 'Vaihiria', 'Faaiti', 'Toahotu', 'Plateau de Taravao'],
    'Taiarapu-Ouest':  ['Teahupoo', 'Vairao', 'Toahotu ouest'],
    'Teva I Uta':      ['Mataiea', 'Papeari'],
    'Papara':          ['Papara centre', 'Atimaono', 'Mara'],
    'Paea':            ['Paea centre', 'Mapumai', 'Orofara Paea'],
    'Punaauia':        ['Outumaoro', 'Oropaa', 'PK18', 'PK20', 'PK21', 'Ah-Sing', 'Manotahi', 'Tamarii'],
    "Faa'a":           ["Faa'a centre", 'Maeva Beach', 'Heiri', 'Vaitea', 'Aeroport', 'Pamatai'],
    // Moorea
    'Afareaitu':       ['Afareaitu centre', 'Maatea', 'Hotutea'],
    'Haapiti':         ['Haapiti centre', 'Atiha', 'Maatea ouest'],
    'Pao Pao':         ["Pao Pao centre", "Cook's Bay", 'Maharepa', 'Pihaena'],
    'Papeatoai':       ["Papeatoai centre", "Opunohu", 'Vallee Opunohu'],
    'Teavaro':         ['Teavaro centre', 'Temae', 'Vaiare'],
  };

  // Correspondance commune-affichage → commune-data (pour le modèle Django)
  const COMMUNE_TO_DATA = {
    'Teva I Uta': 'Teva I Uta',
    'Gambier (Rikitea)': 'Rikitea',
    'Autre Tuamotu': '',
  };

  /* ═══════════════════════════════════════════════════════════════════════════
     HELPERS
     ═══════════════════════════════════════════════════════════════════════════ */

  function slugify(s) {
    return s.toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/['']/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'className') node.className = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === 'html') node.innerHTML = v;
      else if (k === 'text') node.textContent = v;
      else node.setAttribute(k, v);
    });
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(c => {
        if (typeof c === 'string') node.appendChild(document.createTextNode(c));
        else if (c) node.appendChild(c);
      });
    }
    return node;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     CLASSE PRINCIPALE
     ═══════════════════════════════════════════════════════════════════════════ */

  class LocationSelector {
    /**
     * @param {HTMLElement} container — élément conteneur
     * @param {Object} options
     * @param {string}   options.mode     — 'filter' | 'form'
     * @param {string}   options.name     — nom du champ hidden (défaut: 'localisation')
     * @param {Function} options.onChange  — callback(selections)
     * @param {string}   options.staticPrefix — préfixe pour les fichiers statiques SVG
     * @param {Array}    options.initial   — sélections initiales [{island, commune, quartier}]
     */
    constructor(container, options) {
      options = options || {};
      this.container = container;
      this.mode = options.mode || 'filter';
      this.fieldName = options.name || 'localisation';
      this.onChange = options.onChange || function () {};
      this.staticPrefix = options.staticPrefix || '/static/img/';

      // State
      this.selections = [];
      this.level = 1;
      this.currentIsland = null;
      this.currentCommune = null;
      this.isOpen = false;
      this.svgCache = {};

      // Zoom state (for map-based islands)
      this._isZoomed = false;
      this._zoomedCommune = null;
      this._originalViewBox = null;
      this._mapContainer = null;
      this._currentSvg = null;

      // Restore initial selections
      if (options.initial && options.initial.length) {
        this.selections = options.initial.slice();
      }

      this._build();
    }

    /* ─── DOM Construction ─────────────────────────────────────────────── */

    _build() {
      this.container.classList.add('loc-selector');
      this.container.innerHTML = '';

      // Trigger button
      this.trigger = el('button', {
        className: 'loc-selector__trigger',
        type: 'button',
        onClick: () => this.toggle()
      });
      this._renderTrigger();

      // Panel (inline, expands below trigger)
      this.panel = el('div', { className: 'loc-selector__panel' });
      this.panel.style.display = 'none';

      // Breadcrumb
      this.breadcrumb = el('div', { className: 'loc-selector__breadcrumb' });
      this.panel.appendChild(this.breadcrumb);

      // Content
      this.content = el('div', { className: 'loc-selector__content' });
      this.panel.appendChild(this.content);

      // Tags bar (inside panel)
      this.tagsBar = el('div', { className: 'loc-selector__tags' });
      this.panel.appendChild(this.tagsBar);

      // Hidden inputs container
      this.hiddenContainer = el('div', { className: 'loc-selector__hidden' });

      this.container.appendChild(this.trigger);
      this.container.appendChild(this.panel);
      this.container.appendChild(this.hiddenContainer);

      // Close on outside click
      this._onDocClick = (e) => {
        if (this.isOpen && !this.container.contains(e.target)) this.close();
      };
      document.addEventListener('click', this._onDocClick, true);

      // Render initial state
      this._renderTags();
      this._syncHidden();
    }

    /* ─── Open / Close ─────────────────────────────────────────────────── */

    toggle() {
      this.isOpen ? this.close() : this.open();
    }

    open() {
      if (this.isOpen) return;
      this.isOpen = true;
      this.panel.style.display = '';
      this.container.classList.add('loc-selector--open');
      this.level = 1;
      this.currentIsland = null;
      this.currentCommune = null;
      this._renderLevel1();
    }

    close() {
      if (!this.isOpen) return;
      this.isOpen = false;
      this.panel.style.display = 'none';
      this.container.classList.remove('loc-selector--open');
    }

    /* ─── LEVEL 1 — Sélection d'île ───────────────────────────────────── */

    _renderLevel1() {
      this.level = 1;
      this.currentIsland = null;
      this.currentCommune = null;
      this._isZoomed = false;
      this._zoomedCommune = null;
      this._renderBreadcrumb();
      this.content.innerHTML = '';

      var grid = el('div', { className: 'loc-selector__islands' });
      ISLANDS.forEach(function (island) {
        var chip = el('button', {
          className: 'loc-selector__island-chip',
          type: 'button',
          'data-island': island.id,
          onClick: function () { this._selectIsland(island); }.bind(this)
        }, [
          el('span', { className: 'loc-selector__island-emoji', text: island.emoji }),
          el('span', { text: island.name })
        ]);
        grid.appendChild(chip);
      }.bind(this));

      this.content.appendChild(grid);
    }

    /* ─── LEVEL 2 — Carte SVG ou liste ────────────────────────────────── */

    _selectIsland(island) {
      this.currentIsland = island;
      this.level = 2;
      this._isZoomed = false;
      this._zoomedCommune = null;
      this._renderBreadcrumb();
      this.content.innerHTML = '';

      if (island.type === 'map') {
        this._renderMap(island.id);
      } else {
        this._renderDropdown(island.id);
      }
    }

    _renderMap(islandId) {
      var self = this;
      var mapContainer = el('div', { className: 'loc-selector__map-wrap' });

      // Loading indicator
      mapContainer.innerHTML = '<div class="loc-selector__loading">Chargement de la carte...</div>';
      this.content.appendChild(mapContainer);

      // Check cache
      if (this.svgCache[islandId]) {
        this._insertSvg(mapContainer, this.svgCache[islandId], islandId);
        return;
      }

      // Fetch SVG
      var url = this.staticPrefix + islandId + '_map.svg';
      fetch(url)
        .then(function (r) {
          if (!r.ok) throw new Error('SVG not found');
          return r.text();
        })
        .then(function (svgText) {
          self.svgCache[islandId] = svgText;
          self._insertSvg(mapContainer, svgText, islandId);
        })
        .catch(function () {
          // Fallback to dropdown if SVG not available
          mapContainer.innerHTML = '';
          self._renderDropdownInto(mapContainer, islandId);
        });
    }

    _insertSvg(container, svgText, islandId) {
      var self = this;
      container.innerHTML = svgText;

      var svg = container.querySelector('svg');
      if (svg) {
        svg.classList.add('loc-selector__svg');
        svg.removeAttribute('width');
        svg.removeAttribute('height');
      }

      // Store references for zoom
      this._mapContainer = container;
      this._currentSvg = svg;
      this._originalViewBox = svg ? svg.getAttribute('viewBox') : null;
      this._isZoomed = false;
      this._zoomedCommune = null;

      // Bind click / hover on commune zones
      var zones = container.querySelectorAll('.commune-zone');
      zones.forEach(function (zone) {
        var communeName = zone.getAttribute('data-commune');

        // Highlight if already selected
        self._updateZoneStyle(zone, communeName);

        zone.addEventListener('mouseenter', function () {
          if (!self._isSelected(communeName)) {
            zone.style.fillOpacity = '0.85';
            zone.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))';
          }
        });
        zone.addEventListener('mouseleave', function () {
          self._updateZoneStyle(zone, communeName);
        });
        zone.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          // Navigate to quartier chips (text list) — same flow as dropdown islands
          self._selectCommune(communeName, islandId);
        });
      });
    }

    _updateZoneStyle(zone, communeName) {
      if (this._isSelected(communeName)) {
        zone.style.fill = '#0F6E56';
        zone.style.fillOpacity = '1';
        zone.style.stroke = '#ffffff';
        zone.style.strokeWidth = '2';
        zone.style.filter = 'drop-shadow(0 2px 6px rgba(0,0,0,0.3))';
      } else {
        zone.style.fill = '#1D9E75';
        zone.style.fillOpacity = '0.6';
        zone.style.stroke = '#ffffff';
        zone.style.strokeWidth = '1.5';
        zone.style.filter = 'none';
      }
    }

    /* ─── Zoom (carte SVG) ─────────────────────────────────────────────── */

    _zoomToCommune(communeName, islandId) {
      var svg = this._currentSvg;
      if (!svg) return;
      var zone = svg.querySelector('[data-commune="' + communeName + '"]');
      if (!zone) return;

      this._isZoomed = true;
      this._zoomedCommune = communeName;
      this.level = 3;
      this.currentCommune = communeName;
      this._renderBreadcrumb();

      // Calculate zoom target from commune path bounding box
      var bbox = zone.getBBox();
      var pad = Math.max(bbox.width, bbox.height) * 0.2;
      var newVB = (bbox.x - pad) + ' ' + (bbox.y - pad) + ' ' +
                  (bbox.width + 2 * pad) + ' ' + (bbox.height + 2 * pad);

      // Animate viewBox
      this._animateViewBox(svg, svg.getAttribute('viewBox'), newVB, 400);

      // Dim other communes
      var self = this;
      svg.querySelectorAll('.commune-zone').forEach(function (z) {
        if (z.getAttribute('data-commune') !== communeName) {
          z.style.fillOpacity = '0.25';
          z.style.stroke = '#ccc';
        } else {
          z.style.fillOpacity = '0.5';
        }
      });

      // Show quartier layer for this commune after animation starts
      var qSlug = slugify(communeName);
      var qLayer = svg.querySelector('#quartiers-' + qSlug);
      if (qLayer) {
        setTimeout(function () { qLayer.style.display = ''; }, 200);
      }

      // Fade out commune labels
      var labels = svg.querySelector('#labels-layer');
      if (labels) labels.style.display = 'none';

      // Add overlay buttons
      this._addZoomOverlay(communeName, islandId);

      // Bind quartier marker events
      this._bindQuartierMarkers(svg, communeName, islandId);
    }

    _zoomOut() {
      var svg = this._currentSvg;
      if (!svg || !this._isZoomed) return;

      // Animate viewBox back
      this._animateViewBox(svg, svg.getAttribute('viewBox'), this._originalViewBox, 350);

      // Hide quartier layers
      svg.querySelectorAll('.quartier-layer').forEach(function (g) {
        g.style.display = 'none';
      });

      // Show commune labels
      var labels = svg.querySelector('#labels-layer');
      if (labels) labels.style.display = '';

      // Restore commune styles
      var self = this;
      svg.querySelectorAll('.commune-zone').forEach(function (z) {
        z.style.stroke = '#ffffff';
        self._updateZoneStyle(z, z.getAttribute('data-commune'));
      });

      // Remove overlay
      var overlay = this._mapContainer.querySelector('.loc-selector__zoom-overlay');
      if (overlay) overlay.remove();

      this._isZoomed = false;
      this._zoomedCommune = null;
      this.level = 2;
      this.currentCommune = null;
      this._renderBreadcrumb();
    }

    _animateViewBox(svg, fromStr, toStr, duration) {
      var from = fromStr.split(' ').map(Number);
      var to = toStr.split(' ').map(Number);
      var start = null;
      function ease(t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; }
      function step(ts) {
        if (!start) start = ts;
        var t = Math.min((ts - start) / duration, 1);
        var e = ease(t);
        var cur = from.map(function (f, i) { return (f + (to[i] - f) * e).toFixed(1); });
        svg.setAttribute('viewBox', cur.join(' '));
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    _addZoomOverlay(communeName, islandId) {
      var self = this;
      var container = this._mapContainer;
      var existing = container.querySelector('.loc-selector__zoom-overlay');
      if (existing) existing.remove();

      var overlay = el('div', { className: 'loc-selector__zoom-overlay' });

      // Back button
      var islandName = this.currentIsland ? this.currentIsland.name : 'Tahiti';
      overlay.appendChild(el('button', {
        className: 'loc-selector__zoom-back',
        type: 'button',
        html: '\u2190 Retour ' + islandName,
        onClick: function () { self._zoomOut(); }
      }));

      // "Toute commune" button
      var label = 'Tout' + (communeName === "Faa'a" ? 'e ' : ' ') + communeName;
      var touteBtn = el('button', {
        className: 'loc-selector__zoom-toute' + (this._isSelected(communeName) ? ' active' : ''),
        type: 'button',
        text: label,
        onClick: function () {
          self._addSelection({
            island: islandId, commune: communeName,
            quartier: null, label: communeName
          });
          touteBtn.classList.toggle('active', self._isSelected(communeName));
        }
      });
      overlay.appendChild(touteBtn);

      container.appendChild(overlay);
    }

    _bindQuartierMarkers(svg, communeName, islandId) {
      var self = this;
      var qSlug = slugify(communeName);
      var qLayer = svg.querySelector('#quartiers-' + qSlug);
      if (!qLayer) return;

      qLayer.querySelectorAll('.quartier-marker').forEach(function (marker) {
        var qName = marker.getAttribute('data-quartier');
        self._updateMarkerStyle(marker, communeName, qName);

        marker.addEventListener('mouseenter', function () {
          if (!self._isSelectedQuartier(communeName, qName)) {
            marker.setAttribute('r', '7');
            marker.style.fill = '#0A5A42';
          }
        });
        marker.addEventListener('mouseleave', function () {
          self._updateMarkerStyle(marker, communeName, qName);
        });
        marker.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          self._addSelection({
            island: islandId, commune: communeName,
            quartier: qName, label: communeName + ' \u2014 ' + qName
          });
          self._updateMarkerStyle(marker, communeName, qName);
          // Update all markers in this layer
          qLayer.querySelectorAll('.quartier-marker').forEach(function (m) {
            self._updateMarkerStyle(m, communeName, m.getAttribute('data-quartier'));
          });
        });
      });
    }

    _updateMarkerStyle(marker, communeName, qName) {
      if (this._isSelectedQuartier(communeName, qName)) {
        marker.setAttribute('r', '7');
        marker.style.fill = '#FFA500';
        marker.style.stroke = '#fff';
        marker.style.strokeWidth = '1.5';
      } else {
        marker.setAttribute('r', '5');
        marker.style.fill = '#0F6E56';
        marker.style.stroke = '#fff';
        marker.style.strokeWidth = '1.2';
      }
    }

    _renderDropdown(islandId) {
      this._renderDropdownInto(this.content, islandId);
    }

    _renderDropdownInto(container, islandId) {
      var self = this;
      var communes = COMMUNES[islandId] || [];
      var list = el('div', { className: 'loc-selector__commune-list' });

      // Bouton "Toute l'île"
      var island = ISLANDS.find(function (i) { return i.id === islandId; });
      var allBtn = el('button', {
        className: 'loc-selector__commune-chip loc-selector__commune-chip--all',
        type: 'button',
        text: 'Toute ' + (island ? island.name : 'l\'île'),
        onClick: function () {
          self._addSelection({ island: islandId, commune: null, quartier: null, label: island.name });
        }
      });
      list.appendChild(allBtn);

      communes.forEach(function (commune) {
        var isSelected = self._isSelected(commune);
        var chip = el('button', {
          className: 'loc-selector__commune-chip' + (isSelected ? ' loc-selector__commune-chip--active' : ''),
          type: 'button',
          'data-commune': commune,
          text: commune,
          onClick: function () {
            self._selectCommune(commune, islandId);
          }
        });
        list.appendChild(chip);
      });

      container.appendChild(list);
    }

    /* ─── LEVEL 3 — Quartiers ─────────────────────────────────────────── */

    _selectCommune(communeName, islandId) {
      var quartiers = QUARTIERS[communeName];

      // Si pas de quartiers → sélection directe
      if (!quartiers || !quartiers.length) {
        this._addSelection({
          island: islandId,
          commune: communeName,
          quartier: null,
          label: communeName
        });
        return;
      }

      // Afficher les quartiers
      this.level = 3;
      this.currentCommune = communeName;
      this._renderBreadcrumb();
      this.content.innerHTML = '';
      this._renderQuartiers(communeName, islandId);
    }

    _renderQuartiers(communeName, islandId) {
      var self = this;
      var quartiers = QUARTIERS[communeName] || [];
      var list = el('div', { className: 'loc-selector__quartier-list' });

      // Bouton "Toute la commune"
      var allBtn = el('button', {
        className: 'loc-selector__quartier-chip loc-selector__quartier-chip--all'
            + (this._isSelected(communeName) ? ' loc-selector__quartier-chip--active' : ''),
        type: 'button',
        html: 'Tout' + (communeName === "Faa'a" ? 'e ' : ' ') + communeName,
        onClick: function () {
          self._addSelection({
            island: islandId,
            commune: communeName,
            quartier: null,
            label: communeName
          });
          self._renderQuartiers(communeName, islandId);
        }
      });
      list.appendChild(allBtn);

      quartiers.forEach(function (q) {
        var isSelected = self._isSelectedQuartier(communeName, q);
        var chip = el('button', {
          className: 'loc-selector__quartier-chip'
              + (isSelected ? ' loc-selector__quartier-chip--active' : ''),
          type: 'button',
          text: q,
          onClick: function () {
            self._addSelection({
              island: islandId,
              commune: communeName,
              quartier: q,
              label: communeName + ' — ' + q
            });
            self._renderQuartiers(communeName, islandId);
          }
        });
        list.appendChild(chip);
      });

      this.content.appendChild(list);
    }

    /* ─── Sélections ──────────────────────────────────────────────────── */

    _isSelected(communeName) {
      return this.selections.some(function (s) {
        return s.commune === communeName && !s.quartier;
      });
    }

    _isSelectedQuartier(communeName, quartier) {
      return this.selections.some(function (s) {
        return s.commune === communeName && s.quartier === quartier;
      });
    }

    _isSelectedAny(communeName) {
      return this.selections.some(function (s) {
        return s.commune === communeName;
      });
    }

    _addSelection(sel) {
      if (this.mode === 'form') {
        // Mono-sélection : remplace tout
        this.selections = [sel];
        this._afterChange();
        this.close();
        return;
      }

      // Multi-sélection (filter mode)
      // Vérifie si déjà sélectionné
      var existing = this.selections.findIndex(function (s) {
        return s.commune === sel.commune && s.quartier === sel.quartier;
      });
      if (existing >= 0) {
        // Désélectionner
        this.selections.splice(existing, 1);
      } else {
        // Si on sélectionne toute la commune, retirer les quartiers individuels
        if (!sel.quartier && sel.commune) {
          this.selections = this.selections.filter(function (s) {
            return s.commune !== sel.commune;
          });
        }
        // Si on sélectionne un quartier, retirer la commune entière si sélectionnée
        if (sel.quartier) {
          this.selections = this.selections.filter(function (s) {
            return !(s.commune === sel.commune && !s.quartier);
          });
        }
        this.selections.push(sel);
      }
      this._afterChange();
    }

    _removeSelection(index) {
      this.selections.splice(index, 1);
      this._afterChange();
    }

    clearAll() {
      this.selections = [];
      this._afterChange();
    }

    _afterChange() {
      this._renderTrigger();
      this._renderTags();
      this._syncHidden();
      this.onChange(this.selections);

      // Rafraîchir les styles des zones SVG si le panel est ouvert
      if (this.isOpen && this.currentIsland) {
        var self = this;

        // Update commune zone styles (only when not zoomed)
        if (!this._isZoomed) {
          var zones = this.content.querySelectorAll('.commune-zone');
          zones.forEach(function (z) {
            var name = z.getAttribute('data-commune');
            self._updateZoneStyle(z, name);
          });
        }

        // Update quartier marker styles when zoomed
        if (this._isZoomed && this._currentSvg && this._zoomedCommune) {
          var qSlug = slugify(this._zoomedCommune);
          var qLayer = this._currentSvg.querySelector('#quartiers-' + qSlug);
          if (qLayer) {
            qLayer.querySelectorAll('.quartier-marker').forEach(function (m) {
              self._updateMarkerStyle(m, self._zoomedCommune, m.getAttribute('data-quartier'));
            });
          }
          // Update "Toute commune" button
          var touteBtn = this._mapContainer && this._mapContainer.querySelector('.loc-selector__zoom-toute');
          if (touteBtn) {
            touteBtn.classList.toggle('active', this._isSelected(this._zoomedCommune));
          }
        }

        // Rafraîchir les chips communes
        var chips = this.content.querySelectorAll('.loc-selector__commune-chip[data-commune]');
        chips.forEach(function (chip) {
          var name = chip.getAttribute('data-commune');
          if (self._isSelectedAny(name)) {
            chip.classList.add('loc-selector__commune-chip--active');
          } else {
            chip.classList.remove('loc-selector__commune-chip--active');
          }
        });
      }
    }

    /* ─── Breadcrumb ──────────────────────────────────────────────────── */

    _renderBreadcrumb() {
      var self = this;
      this.breadcrumb.innerHTML = '';

      // Toujours : lien Polynésie
      var polyLink = el('button', {
        className: 'loc-selector__bc-link',
        type: 'button',
        text: 'Polynesie',
        onClick: function () { self._renderLevel1(); }
      });
      this.breadcrumb.appendChild(polyLink);

      if (this.level >= 2 && this.currentIsland) {
        this.breadcrumb.appendChild(el('span', { className: 'loc-selector__bc-sep', text: ' \u203A ' }));
        if (this.level === 2) {
          this.breadcrumb.appendChild(el('span', { className: 'loc-selector__bc-current', text: this.currentIsland.name }));
        } else {
          var islandLink = el('button', {
            className: 'loc-selector__bc-link',
            type: 'button',
            text: this.currentIsland.name,
            onClick: function () { self._selectIsland(self.currentIsland); }
          });
          this.breadcrumb.appendChild(islandLink);
        }
      }

      if (this.level === 3 && this.currentCommune) {
        this.breadcrumb.appendChild(el('span', { className: 'loc-selector__bc-sep', text: ' \u203A ' }));
        this.breadcrumb.appendChild(el('span', { className: 'loc-selector__bc-current', text: this.currentCommune }));
      }

      // Bouton retour
      if (this.level > 1) {
        var backBtn = el('button', {
          className: 'loc-selector__back',
          type: 'button',
          html: '\u2190 Retour',
          onClick: function () {
            if (self.level === 3) {
              self._selectIsland(self.currentIsland);
            } else {
              self._renderLevel1();
            }
          }
        });
        this.breadcrumb.appendChild(backBtn);
      }
    }

    /* ─── Trigger (bouton principal) ──────────────────────────────────── */

    _renderTrigger() {
      if (this.selections.length === 0) {
        this.trigger.innerHTML = '';
        this.trigger.appendChild(el('span', { className: 'loc-selector__placeholder', text: 'Toute la Polynesie...' }));
        this.trigger.appendChild(el('span', { className: 'loc-selector__arrow', html: '\u25BE' }));
        return;
      }

      this.trigger.innerHTML = '';
      var labels = this.selections.map(function (s) { return s.label || s.commune || ''; });
      var text = labels.join(', ');
      if (text.length > 40) text = text.substring(0, 37) + '...';
      this.trigger.appendChild(el('span', { className: 'loc-selector__value', text: text }));
      this.trigger.appendChild(el('span', { className: 'loc-selector__arrow', html: '\u25BE' }));
    }

    /* ─── Tags (sélections) ───────────────────────────────────────────── */

    _renderTags() {
      this.tagsBar.innerHTML = '';
      if (this.selections.length === 0) {
        this.tagsBar.style.display = 'none';
        return;
      }
      this.tagsBar.style.display = '';
      var self = this;

      this.selections.forEach(function (sel, i) {
        var tag = el('span', { className: 'loc-selector__tag' }, [
          document.createTextNode(sel.label || sel.commune || ''),
          el('button', {
            className: 'loc-selector__tag-remove',
            type: 'button',
            html: '\u00D7',
            onClick: function (e) {
              e.stopPropagation();
              self._removeSelection(i);
            }
          })
        ]);
        self.tagsBar.appendChild(tag);
      });

      if (this.selections.length > 1) {
        var clearBtn = el('button', {
          className: 'loc-selector__clear-all',
          type: 'button',
          html: '\u00D7 Tout effacer',
          onClick: function (e) {
            e.stopPropagation();
            self.clearAll();
          }
        });
        this.tagsBar.appendChild(clearBtn);
      }
    }

    /* ─── Hidden inputs (synchronisation formulaire) ──────────────────── */

    _syncHidden() {
      this.hiddenContainer.innerHTML = '';

      if (this.mode === 'form') {
        // Mode formulaire : champs commune, quartier, localisation
        var sel = this.selections[0];
        var commune = sel ? (sel.commune || '') : '';
        var quartier = sel ? (sel.quartier || '') : '';
        var localisation = commune;
        if (quartier) localisation = commune + ' - ' + quartier;

        // Résoudre le nom de commune pour le modèle
        var communeData = COMMUNE_TO_DATA[commune] !== undefined ? COMMUNE_TO_DATA[commune] : commune;

        this.hiddenContainer.appendChild(el('input', { type: 'hidden', name: 'commune', value: communeData }));
        this.hiddenContainer.appendChild(el('input', { type: 'hidden', name: 'quartier', value: quartier }));
        this.hiddenContainer.appendChild(el('input', { type: 'hidden', name: 'localisation', value: localisation }));
      } else {
        // Mode filtre : valeurs séparées par virgule
        var values = this.selections.map(function (s) {
          if (s.quartier) return s.commune + ' - ' + s.quartier;
          if (s.commune) return s.commune;
          return s.label || '';
        }).filter(Boolean);

        this.hiddenContainer.appendChild(
          el('input', { type: 'hidden', name: this.fieldName, value: values.join(',') })
        );
      }
    }

    /* ─── API publique ────────────────────────────────────────────────── */

    getSelections() {
      return this.selections.slice();
    }

    getValue() {
      return this.selections.map(function (s) {
        if (s.quartier) return s.commune + ' - ' + s.quartier;
        if (s.commune) return s.commune;
        return s.label || '';
      }).filter(Boolean);
    }

    setSelections(sels) {
      this.selections = sels.slice();
      this._afterChange();
    }

    destroy() {
      document.removeEventListener('click', this._onDocClick, true);
      this.container.innerHTML = '';
    }
  }

  window.LocationSelector = LocationSelector;

})();
