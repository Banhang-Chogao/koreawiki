/**
 * KoreaWiki Smart Search — client-side engine on top of Pagefind.
 *
 * Architecture:
 * 1. Pagefind indexes published article HTML at build time (fuzzy, prefix, multilingual).
 * 2. This module expands synonyms / romanization, parses advanced operators,
 *    re-ranks results (title > alias > tags > body + recency/pin/weight), and
 *    renders a command-palette UI with keyboard-first UX.
 *
 * No backend. Fully static. GitHub Pages + offline after first load.
 */
(function () {
  'use strict';

  var si = document.getElementById('search-input');
  var rl = document.querySelector('[data-search-results-list]');
  var nr = document.querySelector('[data-search-no-results]');
  var es = document.querySelector('[data-search-empty]');
  var fl = document.querySelector('[data-search-filters]');
  var rch = document.querySelector('[data-search-recent]');
  var rcl = document.querySelector('[data-search-recent-list]');
  var ph = document.querySelector('[data-search-popular]');
  var pl = document.querySelector('[data-search-popular-list]');
  var cb = document.querySelector('[data-search-clear]');
  var sortEl = document.querySelector('[data-search-sort]');
  var overlay = document.querySelector('[data-search-overlay]');
  var suggestEl = document.querySelector('[data-search-suggest]');

  if (!si || !rl) return;

  var pf = null;
  var pfLoading = null;
  var currentQuery = '';
  var selectedIndex = -1;
  var activeFilter = 'all';
  var activeSort = 'relevant';
  var resultCache = [];
  var searchGen = 0;
  var composing = false;

  var HISTORY_KEY = 'kw_search_history';
  var CLICKS_KEY = 'kw_search_clicks';
  var MAX_HISTORY = 20;
  var MAX_RESULTS = 40;
  var DEBOUNCE_MS = 50;
  var MIN_CHARS = 1;

  /* Popular seed + frequently-clicked merge */
  var POPULAR_SEED = ['IU', 'BTS', 'K-Drama', 'K-Pop', 'Dispatch', 'TOPIK', 'Netflix', 'Blackpink'];

  /* Synonyms / romanization / multilingual expansion (query-time only).
     Pagefind handles Hangul tokenization; this fills romanization gaps. */
  var SYNONYMS = {
    topik: ['\uD1A0\uD53D', 'TOPIK', 'topik'],
    '\uD1A0\uD53D': ['TOPIK', 'topik', '\uD1A0\uD53D'],
    '\uAC80\uC0C9': ['\uAC80\uC0C9', '\uAC80\uC0C9\uD558\uB2E4', '\uAC80\uC0C9\uAE30', 'search', 'geomsaek', 'gumsaek'],
    geomsaek: ['\uAC80\uC0C9', '\uAC80\uC0C9\uD558\uB2E4', '\uAC80\uC0C9\uAE30', 'search'],
    gumsaek: ['\uAC80\uC0C9', '\uAC80\uC0C9\uD558\uB2E4', '\uAC80\uC0C9\uAE30', 'search'],
    'ti\u1EBFng h\u00E0n': ['korean', '\uD55C\uAD6D\uC5B4', 'ti\u1EBFng H\u00E0n', 'han quoc', 'h\u00E0n qu\u1ED1c'],
    'han quoc': ['\uD55C\uAD6D', 'korea', 'korean', 'h\u00E0n qu\u1ED1c', 'ti\u1EBFng h\u00E0n'],
    'h\u00E0n qu\u1ED1c': ['\uD55C\uAD6D', 'korea', 'korean', 'han quoc'],
    korea: ['\uD55C\uAD6D', '\uD55C\uAD6D', 'h\u00E0n qu\u1ED1c', 'han quoc'],
    '\uD55C\uAD6D': ['korea', 'korean', 'h\u00E0n qu\u1ED1c', 'han quoc'],
    '\uD55C\uAD6D\uC5B4': ['korean', 'ti\u1EBFng h\u00E0n', 'hangugeo'],
    hangugeo: ['\uD55C\uAD6D\uC5B4', 'korean'],
    kpop: ['k-pop', 'K-Pop', '\uCF00\uC774\uD31D'],
    'k-pop': ['kpop', 'K-Pop', '\uCF00\uC774\uD31D'],
    '\uCF00\uC774\uD31D': ['k-pop', 'kpop', 'K-Pop'],
    kdrama: ['k-drama', 'K-Drama', '\uB4DC\uB77C\uB9C8'],
    'k-drama': ['kdrama', 'K-Drama', '\uB4DC\uB77C\uB9C8'],
    '\uB4DC\uB77C\uB9C8': ['k-drama', 'kdrama', 'drama'],
    bts: ['\uBC29\uD0C4\uC18C\uB144\uB2E8', '\uBC29\uD0C4', 'bangtan'],
    '\uBC29\uD0C4\uC18C\uB144\uB2E8': ['BTS', 'bangtan', '\uBC29\uD0C4'],
    bangtan: ['BTS', '\uBC29\uD0C4\uC18C\uB144\uB2E8'],
    blackpink: ['\uBE14\uB799\uD551\uD06C', 'BP'],
    '\uBE14\uB799\uD551\uD06C': ['Blackpink', 'BLACKPINK'],
    iu: ['\uC544\uC774\uC720', 'Lee Ji-eun', '\uC774\uC9C0\uC740'],
    '\uC544\uC774\uC720': ['IU', 'Lee Ji-eun'],
    dispatch: ['\uB514\uC2A4\uD328\uCE58'],
    '\uB514\uC2A4\uD328\uCE58': ['Dispatch'],
    netflix: ['\uB123\uD50C\uB9AD\uC2A4'],
    '\uB123\uD50C\uB9AD\uC2A4': ['Netflix'],
    hybe: ['\uD558\uC774\uBE0C'],
    '\uD558\uC774\uBE0C': ['HYBE'],
  };

  var STOP_WORDS = {
    en: { the: 1, a: 1, an: 1, and: 1, or: 1, of: 1, to: 1, in: 1, for: 1, on: 1, is: 1, at: 1, by: 1, with: 1 },
    vi: { v\u00E0: 1, c\u1EE7a: 1, c\u00E1c: 1, m\u1ED9t: 1, l\u00E0: 1, cho: 1, v\u1EDBi: 1, trong: 1, v\u1EC1: 1 },
    ko: {},
  };

  function basePath() {
    var b = document.documentElement.getAttribute('data-base') || '/';
    if (b.slice(-1) !== '/') b += '/';
    return b;
  }

  function pagefindSrc() {
    return basePath() + 'pagefind/pagefind.js';
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  function escapeHTML(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /* ── Storage: history + clicks ─────────────────────────────── */

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch (e) { return []; }
  }
  function setHistory(h) {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h.slice(0, MAX_HISTORY))); } catch (e) { /* private mode */ }
  }
  function addHistory(q) {
    if (!q || q.length < 1) return;
    var h = getHistory().filter(function (i) { return i.toLowerCase() !== q.toLowerCase(); });
    h.unshift(q);
    setHistory(h);
    renderHistory();
  }
  function clearHistory() {
    setHistory([]);
    renderHistory();
  }
  function removeHistory(q) {
    setHistory(getHistory().filter(function (i) { return i.toLowerCase() !== q.toLowerCase(); }));
    renderHistory();
  }

  function getClicks() {
    try { return JSON.parse(localStorage.getItem(CLICKS_KEY) || '{}'); } catch (e) { return {}; }
  }
  function recordClick(q) {
    if (!q) return;
    var c = getClicks();
    var k = q.toLowerCase();
    c[k] = (c[k] || 0) + 1;
    try { localStorage.setItem(CLICKS_KEY, JSON.stringify(c)); } catch (e) { /* ignore */ }
  }

  function popularList() {
    var clicks = getClicks();
    var scored = Object.keys(clicks).map(function (k) { return { q: k, n: clicks[k] }; });
    scored.sort(function (a, b) { return b.n - a.n; });
    var out = [];
    var seen = {};
    scored.slice(0, 8).forEach(function (s) {
      var label = s.q;
      /* Prefer original casing from history */
      getHistory().forEach(function (h) { if (h.toLowerCase() === s.q) label = h; });
      if (!seen[label.toLowerCase()]) { seen[label.toLowerCase()] = 1; out.push(label); }
    });
    POPULAR_SEED.forEach(function (p) {
      if (out.length >= 8) return;
      if (!seen[p.toLowerCase()]) { seen[p.toLowerCase()] = 1; out.push(p); }
    });
    return out;
  }

  /* ── Empty-state UI ────────────────────────────────────────── */

  function renderHistory() {
    if (!rch || !rcl) return;
    var h = getHistory();
    if (!h.length) { rch.style.display = 'none'; return; }
    rch.style.display = '';
    rcl.innerHTML = '';
    h.forEach(function (q) {
      var e = document.createElement('button');
      e.type = 'button';
      e.className = 'search-history-item';
      e.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
        '<span>' + escapeHTML(q) + '</span>' +
        '<span class="search-history-remove" data-remove aria-label="Remove">&times;</span>';
      e.addEventListener('click', function () { fillAndSearch(q); });
      var rm = e.querySelector('[data-remove]');
      if (rm) rm.addEventListener('click', function (ev) { ev.stopPropagation(); removeHistory(q); });
      rcl.appendChild(e);
    });
  }

  function renderPopular() {
    if (!ph || !pl) return;
    pl.innerHTML = '';
    popularList().forEach(function (q) {
      var e = document.createElement('button');
      e.type = 'button';
      e.className = 'search-history-item';
      e.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
        '<span>' + escapeHTML(q) + '</span>';
      e.addEventListener('click', function () { fillAndSearch(q); });
      pl.appendChild(e);
    });
  }

  function fillAndSearch(q) {
    si.value = q;
    si.focus();
    doSearch(q);
  }

  /* ── Highlight + snippet ──────────────────────────────────── */

  function highlightMultiple(text, terms) {
    if (!text) return '';
    if (!terms || !terms.length) return escapeHTML(text);
    var r = escapeHTML(text);
    var sorted = terms.slice().filter(Boolean).sort(function (a, b) { return b.length - a.length; });
    sorted.forEach(function (t) {
      var re = new RegExp('(' + escapeRegExp(t) + ')', 'gi');
      r = r.replace(re, '<mark class="search-highlight">$1</mark>');
    });
    return r;
  }

  function snippetFromContent(content, terms) {
    if (!content) return '';
    var clean = content.replace(/\s+/g, ' ').trim();
    var bestIdx = -1, bestTerm = '';
    terms.forEach(function (t) {
      if (!t) return;
      var idx = clean.toLowerCase().indexOf(t.toLowerCase());
      if (idx >= 0 && (bestIdx < 0 || idx < bestIdx)) { bestIdx = idx; bestTerm = t; }
    });
    if (bestIdx < 0) {
      return escapeHTML(clean.substring(0, 160)) + (clean.length > 160 ? '\u2026' : '');
    }
    var start = Math.max(0, bestIdx - 50);
    var end = Math.min(clean.length, bestIdx + bestTerm.length + 110);
    var snip = (start > 0 ? '\u2026' : '') + clean.substring(start, end) + (end < clean.length ? '\u2026' : '');
    return highlightMultiple(snip, terms);
  }

  function formatDate(d) {
    if (!d) return '';
    try {
      var p = new Date(d);
      if (isNaN(p.getTime())) return d;
      return p.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch (e) { return d; }
  }

  /* ── Query parsing ─────────────────────────────────────────── */

  function parseQuery(raw) {
    var filters = {};
    var titleOnly = null;
    var before = null;
    var after = null;
    var text = raw;

    var re = /(?:^|\s)(category|tag|author|year|section|lang|language|title|before|after):("([^"]+)"|(\S+))/gi;
    var m;
    var consumed = [];
    while ((m = re.exec(raw)) !== null) {
      var key = m[1].toLowerCase();
      var val = (m[3] != null ? m[3] : m[4]).trim();
      consumed.push(m[0]);
      if (key === 'title') titleOnly = val;
      else if (key === 'before') before = val;
      else if (key === 'after') after = val;
      else if (key === 'language') filters.lang = val;
      else if (key === 'category') filters.category = val;
      else if (key === 'tag') filters.tag = val;
      else if (key === 'section') filters.section = val;
      else if (key === 'author') filters.author = val;
      else if (key === 'year') filters.year = val;
      else if (key === 'lang') filters.lang = val;
    }
    consumed.forEach(function (c) { text = text.replace(c, ' '); });
    text = text.replace(/\s+/g, ' ').trim();

    /* Extract "phrase" segments */
    var phrases = [];
    text = text.replace(/"([^"]+)"/g, function (_, p) { phrases.push(p); return ' '; }).replace(/\s+/g, ' ').trim();

    return { text: text, phrases: phrases, filters: filters, titleOnly: titleOnly, before: before, after: after, raw: raw };
  }

  function expandSynonyms(text) {
    if (!text) return text;
    var lower = text.toLowerCase();
    var extras = [];
    Object.keys(SYNONYMS).forEach(function (k) {
      if (lower === k || lower.indexOf(k) !== -1) {
        SYNONYMS[k].forEach(function (s) {
          if (extras.indexOf(s) === -1 && s.toLowerCase() !== lower) extras.push(s);
        });
      }
    });
    /* Also try whole-query synonym */
    if (SYNONYMS[lower]) {
      SYNONYMS[lower].forEach(function (s) {
        if (extras.indexOf(s) === -1) extras.push(s);
      });
    }
    if (!extras.length) return text;
    /* Pagefind OR via space is AND; run primary query, merge synonym queries later */
    return { primary: text, alts: extras };
  }

  function stripStopWords(text) {
    if (!text) return text;
    var parts = text.split(/\s+/);
    var kept = parts.filter(function (w) {
      var l = w.toLowerCase();
      return !(STOP_WORDS.en[l] || STOP_WORDS.vi[l]);
    });
    return kept.length ? kept.join(' ') : text;
  }

  function termsFromQuery(parsed) {
    var terms = [];
    if (parsed.text) {
      stripStopWords(parsed.text).split(/\s+/).forEach(function (t) {
        if (t && terms.indexOf(t) === -1) terms.push(t);
      });
    }
    parsed.phrases.forEach(function (p) { if (terms.indexOf(p) === -1) terms.push(p); });
    if (parsed.titleOnly && terms.indexOf(parsed.titleOnly) === -1) terms.push(parsed.titleOnly);
    return terms;
  }

  /* ── Pagefind loader ───────────────────────────────────────── */

  function loadPF() {
    if (pf) return Promise.resolve(pf);
    if (pfLoading) return pfLoading;
    pfLoading = new Promise(function (resolve, reject) {
      if (window.pagefind) {
        pf = window.pagefind;
        /* Prefer dynamic import path used by modern pagefind */
        if (typeof pf.init === 'function') {
          pf.init().then(function () { resolve(pf); }).catch(reject);
          return;
        }
        resolve(pf);
        return;
      }
      /* Dynamic import (preferred — works with ES modules in pagefind.js) */
      var src = pagefindSrc();
      import(src).then(function (mod) {
        pf = mod;
        if (typeof pf.init === 'function') {
          return pf.init().then(function () { resolve(pf); });
        }
        resolve(pf);
      }).catch(function () {
        /* Fallback: classic script tag */
        var s = document.createElement('script');
        s.src = src;
        s.async = true;
        s.onload = function () {
          pf = window.pagefind;
          if (pf && typeof pf.init === 'function') {
            pf.init().then(function () { resolve(pf); }).catch(reject);
          } else {
            resolve(pf);
          }
        };
        s.onerror = function () { reject(new Error('Failed to load Pagefind')); };
        document.head.appendChild(s);
      });
    });
    return pfLoading;
  }

  /* ── Ranking ───────────────────────────────────────────────── */

  function scoreItem(item, terms, parsed) {
    var meta = item.meta || {};
    var title = (meta.title || '').toLowerCase();
    var tags = (meta.tags || '').toLowerCase();
    var cats = (meta.categories || '').toLowerCase();
    var desc = (meta.description || '').toLowerCase();
    var content = (item.content || '').toLowerCase();
    var section = (meta.section || '').toLowerCase();
    var score = typeof item._pfScore === 'number' ? item._pfScore * 10 : 0;

    terms.forEach(function (t) {
      if (!t) return;
      var tl = t.toLowerCase();
      if (title === tl) score += 1000;
      else if (title.indexOf(tl) === 0) score += 600;
      else if (title.indexOf(tl) !== -1) score += 400;

      if (tags.split(/,\s*/).indexOf(tl) !== -1) score += 300;
      else if (tags.indexOf(tl) !== -1) score += 200;

      if (cats.toLowerCase().indexOf(tl) !== -1) score += 180;
      if (section === tl) score += 150;
      if (desc.indexOf(tl) === 0) score += 120;
      else if (desc.indexOf(tl) !== -1) score += 80;

      var cidx = content.indexOf(tl);
      if (cidx === 0) score += 60;
      else if (cidx > 0 && cidx < 200) score += 40;
      else if (cidx >= 200) score += 15;
    });

    if (parsed.titleOnly) {
      var to = parsed.titleOnly.toLowerCase();
      if (title.indexOf(to) === -1) score -= 5000;
      else score += 200;
    }

    /* Recency bonus (last ~365 days) */
    if (meta.date) {
      var ageDays = (Date.now() - new Date(meta.date).getTime()) / 86400000;
      if (!isNaN(ageDays) && ageDays >= 0) {
        if (ageDays < 7) score += 80;
        else if (ageDays < 30) score += 50;
        else if (ageDays < 90) score += 25;
        else if (ageDays < 365) score += 10;
      }
    }

    if (meta.pinned === '1' || meta.pinned === 'true') score += 200;
    if (meta.popular === '1' || meta.popular === 'true') score += 100;
    var w = parseFloat(meta.weight);
    if (!isNaN(w) && w > 0) score += w * 10;

    item._rank = score;
    return score;
  }

  function applyClientFilters(items, parsed) {
    return items.filter(function (item) {
      var meta = item.meta || {};
      if (parsed.filters.section && (meta.section || '').toLowerCase() !== parsed.filters.section.toLowerCase()) return false;
      if (parsed.filters.year && String(meta.year || (meta.date || '').slice(0, 4)) !== String(parsed.filters.year)) return false;
      if (parsed.filters.lang && (meta.lang || '').toLowerCase() !== parsed.filters.lang.toLowerCase()) return false;
      if (parsed.filters.author && (meta.author || '').toLowerCase().indexOf(parsed.filters.author.toLowerCase()) === -1) return false;
      if (parsed.filters.tag) {
        var tags = (meta.tags || '').toLowerCase();
        if (tags.indexOf(parsed.filters.tag.toLowerCase()) === -1) return false;
      }
      if (parsed.filters.category) {
        var cats = (meta.categories || '').toLowerCase();
        if (cats.indexOf(parsed.filters.category.toLowerCase()) === -1) return false;
      }
      if (parsed.before && meta.date && meta.date > parsed.before) return false;
      if (parsed.after && meta.date && meta.date < parsed.after) return false;

      /* Reading-time filter via UI dataset */
      var rtFilter = (fl && fl.dataset.readingTime) || '';
      if (rtFilter) {
        var rt = parseInt(meta.reading_time, 10) || 0;
        if (rtFilter === 'short' && rt > 5) return false;
        if (rtFilter === 'medium' && (rt < 5 || rt > 12)) return false;
        if (rtFilter === 'long' && rt < 12) return false;
      }
      return true;
    });
  }

  function sortItems(items) {
    if (activeSort === 'newest') {
      items.sort(function (a, b) {
        return (b.meta && b.meta.date || '').localeCompare(a.meta && a.meta.date || '');
      });
    } else if (activeSort === 'oldest') {
      items.sort(function (a, b) {
        return (a.meta && a.meta.date || '').localeCompare(b.meta && b.meta.date || '');
      });
    } else {
      items.sort(function (a, b) {
        if (b._rank !== a._rank) return b._rank - a._rank;
        return (b.meta && b.meta.date || '').localeCompare(a.meta && a.meta.date || '');
      });
    }
    return items;
  }

  /* ── Search execution ──────────────────────────────────────── */

  function buildPFFilters(parsed) {
    var f = {};
    if (activeFilter && activeFilter !== 'all') f.section = activeFilter;
    if (parsed.filters.section) f.section = parsed.filters.section;
    if (parsed.filters.year) f.year = String(parsed.filters.year);
    if (parsed.filters.lang) f.lang = parsed.filters.lang;
    if (parsed.filters.author) f.author = parsed.filters.author;
    if (parsed.filters.tag) f.tag = parsed.filters.tag;
    if (parsed.filters.category) f.category = parsed.filters.category;
    return Object.keys(f).length ? f : undefined;
  }

  function runPagefindSearch(engine, query, filters) {
    var opts = {};
    if (filters) opts.filters = filters;
    if (activeSort === 'newest') opts.sort = { date: 'desc' };
    if (activeSort === 'oldest') opts.sort = { date: 'asc' };
    return engine.search(query, opts);
  }

  async function collectResults(searchResult, limit) {
    if (!searchResult || !searchResult.results) return [];
    var slice = searchResult.results.slice(0, limit);
    var data = await Promise.all(slice.map(function (r) {
      return r.data().then(function (d) {
        d._pfScore = typeof r.score === 'number' ? r.score : 0;
        return d;
      });
    }));
    return data;
  }

  function mergeByUrl(lists) {
    var map = {};
    lists.forEach(function (list) {
      list.forEach(function (item) {
        var url = item.url;
        if (!map[url] || (item._pfScore || 0) > (map[url]._pfScore || 0)) {
          map[url] = item;
        }
      });
    });
    return Object.keys(map).map(function (k) { return map[k]; });
  }

  function doSearch(query) {
    currentQuery = query;
    if (composing) return;
    var q = (query || '').trim();
    if (q.length < MIN_CHARS) {
      showEmpty();
      renderSuggest('');
      return;
    }

    var gen = ++searchGen;
    var parsed = parseQuery(q);
    var terms = termsFromQuery(parsed);
    var searchText = stripStopWords(parsed.text || parsed.titleOnly || '');
    if (parsed.phrases.length) {
      searchText = (searchText + ' ' + parsed.phrases.join(' ')).trim();
    }
    if (!searchText && !parsed.titleOnly && Object.keys(parsed.filters).length === 0) {
      /* operators only without free text — still search with a broad term if filter set */
      searchText = '';
    }

    var expanded = expandSynonyms(searchText || (parsed.titleOnly || ''));
    var primary = typeof expanded === 'string' ? expanded : expanded.primary;
    var alts = typeof expanded === 'string' ? [] : expanded.alts.slice(0, 3);

    /* Autocomplete suggestions from history/popular while typing */
    renderSuggest(q);

    loadPF().then(function (engine) {
      if (gen !== searchGen) return;
      var filters = buildPFFilters(parsed);
      var queries = [];
      if (primary) queries.push(runPagefindSearch(engine, primary, filters));
      alts.forEach(function (a) { queries.push(runPagefindSearch(engine, a, filters)); });
      /* If only filters (no text), use empty string — Pagefind returns filtered set */
      if (!queries.length) queries.push(runPagefindSearch(engine, '', filters));

      return Promise.all(queries).then(function (results) {
        if (gen !== searchGen) return;
        return Promise.all(results.map(function (r) { return collectResults(r, MAX_RESULTS); }));
      }).then(function (lists) {
        if (gen !== searchGen || !lists) return;
        var merged = mergeByUrl(lists);
        merged = applyClientFilters(merged, parsed);
        merged.forEach(function (item) { scoreItem(item, terms.length ? terms : [primary], parsed); });
        merged = sortItems(merged).slice(0, 20);
        resultCache = merged;
        renderResults(merged, terms.length ? terms : [q]);
      });
    }).catch(function (err) {
      if (gen !== searchGen) return;
      console.warn('[KoreaWiki search]', err);
      showNoResults();
    });
  }

  /* ── Render results ────────────────────────────────────────── */

  function renderResults(data, terms) {
    if (!data.length) { showNoResults(); return; }
    hideEmpty();
    hideNoResults();
    selectedIndex = -1;
    si.setAttribute('aria-expanded', 'true');
    rl.innerHTML = '';
    data.forEach(function (item, i) {
      var e = document.createElement('a');
      e.className = 'search-result-item';
      e.setAttribute('role', 'option');
      e.id = 'search-result-' + i;
      e.href = item.url;
      e.tabIndex = -1;

      var meta = item.meta || {};
      var metaBits = [];
      if (meta.section) metaBits.push(escapeHTML(meta.section));
      if (meta.date) metaBits.push(formatDate(meta.date));
      if (meta.reading_time) metaBits.push(escapeHTML(String(meta.reading_time)) + ' min read');
      if (meta.lang) metaBits.push(escapeHTML(meta.lang.toUpperCase()));

      var hasCover = !!meta.image;
      var title = meta.title ? highlightMultiple(meta.title, terms) : 'Untitled';
      var description = meta.description ? highlightMultiple(meta.description, terms) : '';
      var content = item.content ? snippetFromContent(item.content, terms) : '';

      e.innerHTML =
        '<div class="search-result-content' + (hasCover ? '' : ' search-result-content-full') + '">' +
        (hasCover ? '<img class="search-result-img" src="' + escapeHTML(meta.image) + '" alt="" loading="lazy" width="60" height="60">' : '') +
        '<div class="search-result-text">' +
        '<div class="search-result-title">' + title + '</div>' +
        (description ? '<div class="search-result-desc">' + description + '</div>' : '') +
        (content ? '<div class="search-result-snippet">' + content + '</div>' : '') +
        '<div class="search-result-meta">' + metaBits.join(' \u00B7 ') + '</div>' +
        '</div></div>';

      e.addEventListener('click', function () {
        addHistory(currentQuery);
        recordClick(currentQuery);
      });
      rl.appendChild(e);
    });
  }

  function showEmpty() {
    rl.innerHTML = '';
    if (es) es.hidden = false;
    if (nr) nr.hidden = true;
    si.setAttribute('aria-expanded', 'false');
    selectedIndex = -1;
  }
  function hideEmpty() { if (es) es.hidden = true; }
  function showNoResults() {
    rl.innerHTML = '';
    if (nr) nr.hidden = false;
    if (es) es.hidden = true;
    si.setAttribute('aria-expanded', 'false');
    renderSuggest(currentQuery);
  }
  function hideNoResults() { if (nr) nr.hidden = true; }

  /* ── Autocomplete suggestions ──────────────────────────────── */

  function renderSuggest(q) {
    if (!suggestEl) return;
    if (!q || q.length < 1) {
      suggestEl.hidden = true;
      suggestEl.innerHTML = '';
      return;
    }
    var ql = q.toLowerCase();
    var pool = [];
    getHistory().forEach(function (h) { pool.push({ t: h, k: 'history' }); });
    popularList().forEach(function (p) { pool.push({ t: p, k: 'popular' }); });
    /* Title prefixes from last result set */
    resultCache.forEach(function (item) {
      if (item.meta && item.meta.title) pool.push({ t: item.meta.title, k: 'title' });
      if (item.meta && item.meta.tags) {
        item.meta.tags.split(/,\s*/).forEach(function (tag) {
          if (tag) pool.push({ t: tag, k: 'tag' });
        });
      }
    });

    var seen = {};
    var matches = [];
    pool.forEach(function (p) {
      var tl = p.t.toLowerCase();
      if (seen[tl]) return;
      if (tl.indexOf(ql) === 0 || tl.indexOf(ql) !== -1) {
        seen[tl] = 1;
        matches.push(p);
      }
    });
    matches = matches.slice(0, 6);
    if (!matches.length) {
      suggestEl.hidden = true;
      suggestEl.innerHTML = '';
      return;
    }
    suggestEl.hidden = false;
    suggestEl.innerHTML = matches.map(function (m, i) {
      return '<button type="button" class="search-suggest-item" data-suggest="' + escapeHTML(m.t) + '" data-idx="' + i + '">' +
        '<span class="search-suggest-kind">' + escapeHTML(m.k) + '</span>' +
        '<span>' + highlightMultiple(m.t, [q]) + '</span></button>';
    }).join('');
    suggestEl.querySelectorAll('[data-suggest]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        fillAndSearch(btn.getAttribute('data-suggest'));
      });
    });
  }

  function autocompleteTab() {
    /* Prefer first suggestion, else first result title */
    if (suggestEl && !suggestEl.hidden) {
      var first = suggestEl.querySelector('[data-suggest]');
      if (first) {
        si.value = first.getAttribute('data-suggest');
        doSearch(si.value);
        return true;
      }
    }
    if (resultCache.length && resultCache[0].meta && resultCache[0].meta.title) {
      si.value = resultCache[0].meta.title;
      doSearch(si.value);
      return true;
    }
    return false;
  }

  /* ── Keyboard ──────────────────────────────────────────────── */

  function handleKeydown(e) {
    if (e.key === 'Tab' && !e.shiftKey) {
      if (autocompleteTab()) {
        e.preventDefault();
        return;
      }
    }

    var items = rl.querySelectorAll('.search-result-item');
    var len = items.length;
    if (!len) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, len - 1);
        updateSelection(items);
        break;
      case 'ArrowUp':
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        updateSelection(items);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex < 0) selectedIndex = 0;
        if (selectedIndex >= 0 && selectedIndex < len) {
          addHistory(currentQuery);
          recordClick(currentQuery);
          window.location.href = items[selectedIndex].href;
        }
        break;
      default:
        break;
    }
  }

  function updateSelection(items) {
    items.forEach(function (el, i) {
      el.classList.toggle('selected', i === selectedIndex);
      el.setAttribute('aria-selected', i === selectedIndex ? 'true' : 'false');
      if (i === selectedIndex) el.scrollIntoView({ block: 'nearest' });
    });
    si.setAttribute('aria-activedescendant', selectedIndex >= 0 ? 'search-result-' + selectedIndex : '');
  }

  /* ── Filters / sort ────────────────────────────────────────── */

  function setFilter(filter) {
    activeFilter = filter;
    if (fl) {
      fl.querySelectorAll('.search-filter-btn').forEach(function (b) {
        var on = b.dataset.filter === filter;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }
    if (currentQuery.trim().length >= MIN_CHARS) doSearch(currentQuery);
  }

  function setSort(sort) {
    activeSort = sort;
    if (sortEl) {
      sortEl.querySelectorAll('[data-sort]').forEach(function (b) {
        var on = b.dataset.sort === sort;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
    }
    if (currentQuery.trim().length >= MIN_CHARS) doSearch(currentQuery);
  }

  function initFilters() {
    if (fl) {
      fl.querySelectorAll('.search-filter-btn').forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn.classList.contains('active') ? 'true' : 'false');
        btn.addEventListener('click', function () { setFilter(btn.dataset.filter); });
      });
    }
    if (sortEl) {
      sortEl.querySelectorAll('[data-sort]').forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn.classList.contains('active') ? 'true' : 'false');
        btn.addEventListener('click', function () { setSort(btn.dataset.sort); });
      });
    }
  }

  /* ── Init ──────────────────────────────────────────────────── */

  function init() {
    initFilters();
    renderHistory();
    renderPopular();

    if (cb) cb.addEventListener('click', function (e) {
      e.preventDefault();
      clearHistory();
    });

    var debouncedSearch = debounce(function () {
      doSearch(si.value);
    }, DEBOUNCE_MS);

    si.addEventListener('input', function () {
      if (composing) return;
      var v = si.value.trim();
      if (v.length < MIN_CHARS) {
        showEmpty();
        renderHistory();
        renderSuggest('');
        if (nr) nr.hidden = true;
        return;
      }
      debouncedSearch();
    });

    si.addEventListener('keydown', handleKeydown);
    si.addEventListener('compositionstart', function () { composing = true; });
    si.addEventListener('compositionend', function () {
      composing = false;
      doSearch(si.value);
    });

    /* Prefetch Pagefind after idle so first keystroke is fast */
    var prefetch = function () { loadPF().catch(function () { /* offline / first build */ }); };
    if ('requestIdleCallback' in window) {
      requestIdleCallback(prefetch, { timeout: 2000 });
    } else {
      setTimeout(prefetch, 1200);
    }

    window.__koreaSearch = function () {
      renderHistory();
      renderPopular();
      showEmpty();
      renderSuggest('');
      currentQuery = '';
      selectedIndex = -1;
      rl.innerHTML = '';
      if (si) {
        /* keep previous query for convenience; select it */
        setTimeout(function () { si.focus(); si.select(); }, 50);
      }
    };

    window.__koreaSearchQuery = function (q) {
      if (typeof q === 'string') fillAndSearch(q);
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
