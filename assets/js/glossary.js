/**
 * KoreaWiki Glossary — client-side search over embedded TM display data.
 *
 * Supports: Hangul, Vietnamese, English, romanization, simple typo tolerance,
 * category + initial Hangul filters, instant search, pagination.
 * No backend. Raw TM files are never downloaded.
 */
(function () {
  'use strict';

  var root = document.querySelector('.glossary-page');
  if (!root) return;

  var dataEl = document.getElementById('glossary-data');
  var tbody = root.querySelector('[data-glossary-tbody]');
  var emptyEl = root.querySelector('[data-glossary-empty]');
  var statusEl = root.querySelector('[data-glossary-status]');
  var searchEl = root.querySelector('[data-glossary-search]');
  var clearEl = root.querySelector('[data-glossary-clear]');
  var pagerEl = root.querySelector('[data-glossary-pagination]');
  var countEl = root.querySelector('[data-glossary-count]');

  if (!dataEl || !tbody) return;

  var PAGE_SIZE = 25;
  var DEBOUNCE_MS = 80;

  var entries = [];
  try {
    entries = JSON.parse(dataEl.textContent || '[]');
  } catch (e) {
    entries = [];
  }

  var state = {
    query: '',
    category: 'all',
    hangul: 'all',
    page: 1,
  };

  /* Choseong (initial consonants) for Hangul filter */
  var CHOSEONG = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
    'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
  ];
  /* Map double consonants to single filter chips */
  var CHOSEONG_GROUP = {
    'ㄲ': 'ㄱ', 'ㄸ': 'ㄷ', 'ㅃ': 'ㅂ', 'ㅆ': 'ㅅ', 'ㅉ': 'ㅈ',
  };

  function hangulInitial(ch) {
    if (!ch) return '';
    var code = ch.charCodeAt(0);
    // Hangul syllables AC00–D7A3
    if (code < 0xac00 || code > 0xd7a3) {
      // Already a jamo?
      if (CHOSEONG.indexOf(ch) >= 0) return CHOSEONG_GROUP[ch] || ch;
      return '';
    }
    var idx = Math.floor((code - 0xac00) / 588);
    var jamo = CHOSEONG[idx] || '';
    return CHOSEONG_GROUP[jamo] || jamo;
  }

  function stripDiacritics(s) {
    try {
      return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    } catch (e) {
      return s;
    }
  }

  function normalize(s) {
    return stripDiacritics(String(s || '').toLowerCase()).replace(/\s+/g, ' ').trim();
  }

  /* Levenshtein distance capped for typo tolerance on short tokens */
  function levenshtein(a, b, max) {
    max = max == null ? 2 : max;
    if (a === b) return 0;
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    if (Math.abs(a.length - b.length) > max) return max + 1;
    var prev = new Array(b.length + 1);
    var cur = new Array(b.length + 1);
    var i, j, cost;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      cur[0] = i;
      var rowMin = cur[0];
      for (j = 1; j <= b.length; j++) {
        cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
        if (cur[j] < rowMin) rowMin = cur[j];
      }
      if (rowMin > max) return max + 1;
      var tmp = prev;
      prev = cur;
      cur = tmp;
    }
    return prev[b.length];
  }

  function tokenFuzzyMatch(token, hay) {
    if (!token) return true;
    if (hay.indexOf(token) >= 0) return true;
    // Typo tolerance for Latin tokens length >= 3
    if (!/[\uac00-\ud7a3]/.test(token) && token.length >= 3) {
      var parts = hay.split(/[\s/,·]+/);
      var maxDist = token.length >= 6 ? 2 : 1;
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        if (p.length < 2) continue;
        if (levenshtein(token, p, maxDist) <= maxDist) return true;
        // prefix
        if (p.indexOf(token) === 0 || token.indexOf(p) === 0) return true;
      }
    }
    return false;
  }

  function matchesQuery(entry, q) {
    if (!q) return true;
    var blob = normalize(
      [
        entry.korean,
        entry.vietnamese,
        entry.romanization,
        entry.meaning,
        entry.context,
        entry.example,
        entry.category,
        entry.pos,
        (entry.tags || []).join(' '),
      ].join(' ')
    );
    // Also keep raw Hangul for exact substring (normalize lowercases Latin only meaningfully)
    var rawBlob = [
      entry.korean,
      entry.vietnamese,
      entry.romanization,
      entry.meaning,
      entry.context,
      entry.example,
    ].join(' ');

    var tokens = normalize(q).split(' ').filter(Boolean);
    if (!tokens.length) return true;

    for (var i = 0; i < tokens.length; i++) {
      var t = tokens[i];
      // Hangul / original substring on raw
      if (rawBlob.indexOf(q.split(' ')[i] || t) >= 0) continue;
      if (tokenFuzzyMatch(t, blob)) continue;
      // Hangul token exact in korean
      if ((entry.korean || '').indexOf(q.split(/\s+/)[i]) >= 0) continue;
      return false;
    }
    return true;
  }

  function matchesHangul(entry, filter) {
    if (!filter || filter === 'all') return true;
    var ko = entry.korean || '';
    for (var i = 0; i < ko.length; i++) {
      var init = hangulInitial(ko.charAt(i));
      if (init === filter) return true;
      if (init) break; // first Hangul syllable decides
    }
    // also allow if term starts with the jamo itself
    return ko.charAt(0) === filter;
  }

  function filterEntries() {
    var out = [];
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (state.category !== 'all' && (e.category || 'other') !== state.category) continue;
      if (!matchesHangul(e, state.hangul)) continue;
      if (!matchesQuery(e, state.query)) continue;
      out.push(e);
    }
    return out;
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function highlight(text, q) {
    var t = escapeHtml(text);
    if (!q) return t;
    var tokens = q.trim().split(/\s+/).filter(function (x) { return x.length > 0; });
    tokens.forEach(function (tok) {
      try {
        var re = new RegExp('(' + tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
        t = t.replace(re, '<mark>$1</mark>');
      } catch (err) { /* ignore */ }
    });
    return t;
  }

  function render() {
    var filtered = filterEntries();
    var total = filtered.length;
    var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (state.page > pages) state.page = pages;
    if (state.page < 1) state.page = 1;

    var start = (state.page - 1) * PAGE_SIZE;
    var pageItems = filtered.slice(start, start + PAGE_SIZE);

    tbody.innerHTML = '';
    pageItems.forEach(function (e) {
      var tr = document.createElement('tr');
      var rom = e.romanization
        ? '<div class="glossary-romaja">' + escapeHtml(e.romanization) + '</div>'
        : '';
      tr.innerHTML =
        '<td data-label="Korean"><span class="glossary-ko">' +
        highlight(e.korean, state.query) +
        '</span>' +
        rom +
        '</td>' +
        '<td data-label="Vietnamese"><span class="glossary-vi">' +
        highlight(e.vietnamese, state.query) +
        '</span></td>' +
        '<td data-label="Category"><span class="glossary-cat">' +
        escapeHtml(e.category || 'other') +
        '</span></td>' +
        '<td data-label="Context">' +
        highlight(e.context || e.meaning || '', state.query) +
        '</td>' +
        '<td data-label="Example"><span class="glossary-ex">' +
        highlight(e.example || '', state.query) +
        '</span></td>';
      tbody.appendChild(tr);
    });

    if (emptyEl) emptyEl.hidden = total > 0;
    if (statusEl) {
      statusEl.textContent =
        total === entries.length
          ? total + ' entries'
          : total + ' of ' + entries.length + ' entries';
    }
    if (countEl) countEl.textContent = String(entries.length);

    renderPager(pages, total);
    if (clearEl) clearEl.hidden = !state.query;
  }

  function renderPager(pages, total) {
    if (!pagerEl) return;
    if (pages <= 1) {
      pagerEl.innerHTML = '';
      return;
    }
    var html = '';
    html +=
      '<button type="button" class="glossary-page-btn" data-page="prev"' +
      (state.page <= 1 ? ' disabled' : '') +
      '>‹</button>';

    var windowSize = 5;
    var from = Math.max(1, state.page - Math.floor(windowSize / 2));
    var to = Math.min(pages, from + windowSize - 1);
    from = Math.max(1, to - windowSize + 1);

    if (from > 1) {
      html += '<button type="button" class="glossary-page-btn" data-page="1">1</button>';
      if (from > 2) html += '<span class="glossary-page-gap">…</span>';
    }
    for (var p = from; p <= to; p++) {
      html +=
        '<button type="button" class="glossary-page-btn' +
        (p === state.page ? ' is-active' : '') +
        '" data-page="' +
        p +
        '">' +
        p +
        '</button>';
    }
    if (to < pages) {
      if (to < pages - 1) html += '<span class="glossary-page-gap">…</span>';
      html +=
        '<button type="button" class="glossary-page-btn" data-page="' +
        pages +
        '">' +
        pages +
        '</button>';
    }

    html +=
      '<button type="button" class="glossary-page-btn" data-page="next"' +
      (state.page >= pages ? ' disabled' : '') +
      '>›</button>';
    pagerEl.innerHTML = html;
  }

  /* Events */
  var debounceTimer = null;
  if (searchEl) {
    searchEl.addEventListener('input', function () {
      var val = searchEl.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        state.query = val;
        state.page = 1;
        render();
      }, DEBOUNCE_MS);
    });
  }

  if (clearEl) {
    clearEl.addEventListener('click', function () {
      if (searchEl) searchEl.value = '';
      state.query = '';
      state.page = 1;
      render();
      if (searchEl) searchEl.focus();
    });
  }

  root.querySelectorAll('[data-glossary-category]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      root.querySelectorAll('[data-glossary-category]').forEach(function (b) {
        b.classList.toggle('is-active', b === btn);
      });
      state.category = btn.getAttribute('data-glossary-category') || 'all';
      state.page = 1;
      render();
    });
  });

  root.querySelectorAll('[data-glossary-hangul]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      root.querySelectorAll('[data-glossary-hangul]').forEach(function (b) {
        b.classList.toggle('is-active', b === btn);
      });
      state.hangul = btn.getAttribute('data-glossary-hangul') || 'all';
      state.page = 1;
      render();
    });
  });

  if (pagerEl) {
    pagerEl.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-page]');
      if (!btn || btn.disabled) return;
      var p = btn.getAttribute('data-page');
      if (p === 'prev') state.page -= 1;
      else if (p === 'next') state.page += 1;
      else state.page = parseInt(p, 10) || 1;
      render();
      root.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  render();
})();
