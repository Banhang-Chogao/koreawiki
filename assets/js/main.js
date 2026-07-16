(function(){'use strict';

// Dark Mode
var themeToggle=document.querySelector('[data-theme-toggle]');
var html=document.documentElement;
function getPreferredTheme(){var s=localStorage.getItem('theme');if(s)return s;return window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
function setTheme(t){html.setAttribute('data-theme',t);localStorage.setItem('theme',t);}
if(themeToggle){setTheme(getPreferredTheme());themeToggle.addEventListener('click',function(){var c=html.getAttribute('data-theme');setTheme(c==='dark'?'light':'dark');});window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){if(!localStorage.getItem('theme')){setTheme(e.matches?'dark':'light');}});}

// Mobile Nav
var mobileToggle=document.querySelector('.mobile-nav-toggle');
var mobileNav=document.querySelector('.mobile-nav');
var mobileClose=document.querySelector('.mobile-nav-close');
if(mobileToggle&&mobileNav){mobileToggle.addEventListener('click',function(){mobileNav.classList.add('open');document.body.style.overflow='hidden';});}
if(mobileClose&&mobileNav){mobileClose.addEventListener('click',function(){mobileNav.classList.remove('open');document.body.style.overflow='';});}
if(mobileNav){mobileNav.addEventListener('click',function(e){if(e.target===this){mobileNav.classList.remove('open');document.body.style.overflow='';}});}

// Copy Link
var copyBtn=document.querySelector('[data-copy-url]');
if(copyBtn){copyBtn.addEventListener('click',function(){var u=this.getAttribute('data-copy-url');if(navigator.clipboard){navigator.clipboard.writeText(u).then(function(){var o=copyBtn.innerHTML;copyBtn.innerHTML='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';setTimeout(function(){copyBtn.innerHTML=o;},2000);});}});}

// Search Overlay — command palette open/close, keyboard shortcuts, focus trap
(function(){
  var st=document.querySelectorAll('[data-search-toggle]');
  var so=document.querySelector('[data-search-overlay]');
  var sc=document.querySelector('[data-search-close]');
  var si=document.getElementById('search-input');
  var lastFocus=null;
  var trapHandler=null;

  function focusableIn(root){
    if(!root)return[];
    return Array.prototype.slice.call(root.querySelectorAll(
      'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
    )).filter(function(el){return el.offsetParent!==null||el===si;});
  }

  function enableFocusTrap(){
    disableFocusTrap();
    trapHandler=function(e){
      if(e.key!=='Tab'||!so||!so.classList.contains('open'))return;
      var modal=so.querySelector('.search-modal')||so;
      var nodes=focusableIn(modal);
      if(!nodes.length)return;
      var first=nodes[0],last=nodes[nodes.length-1];
      if(e.shiftKey){
        if(document.activeElement===first){e.preventDefault();last.focus();}
      }else{
        if(document.activeElement===last){e.preventDefault();first.focus();}
      }
    };
    document.addEventListener('keydown',trapHandler,true);
  }

  function disableFocusTrap(){
    if(trapHandler){document.removeEventListener('keydown',trapHandler,true);trapHandler=null;}
  }

  function openSearch(){
    if(!so)return;
    lastFocus=document.activeElement;
    so.classList.add('open');
    so.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
    enableFocusTrap();
    if(window.__koreaSearch)window.__koreaSearch();
    if(si){setTimeout(function(){si.focus();si.select();},50);}
  }

  function closeSearch(){
    if(!so)return;
    so.classList.remove('open');
    so.setAttribute('aria-hidden','true');
    document.body.style.overflow='';
    disableFocusTrap();
    if(si)si.blur();
    if(lastFocus&&typeof lastFocus.focus==='function'){
      try{lastFocus.focus();}catch(e){/* ignore */}
    }
  }

  function isTypingTarget(el){
    if(!el)return false;
    var tag=(el.tagName||'').toLowerCase();
    if(tag==='input'||tag==='textarea'||tag==='select')return true;
    if(el.isContentEditable)return true;
    return false;
  }

  if(st.length&&so){
    Array.from(st).forEach(function(b){b.addEventListener('click',openSearch);});
  }
  if(sc)sc.addEventListener('click',closeSearch);
  if(so){
    so.setAttribute('aria-hidden','true');
    so.addEventListener('click',function(e){if(e.target===so)closeSearch();});
  }

  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&so&&so.classList.contains('open')){
      e.preventDefault();
      closeSearch();
      return;
    }
    if((e.ctrlKey||e.metaKey)&& (e.key==='k'||e.key==='K')){
      e.preventDefault();
      if(so&&so.classList.contains('open'))closeSearch();
      else openSearch();
      return;
    }
    /* "/" opens search when not typing in a field */
    if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){
      if(isTypingTarget(e.target))return;
      if(so&&so.classList.contains('open'))return;
      e.preventDefault();
      openSearch();
    }
  });

  window.__koreaOpenSearch=openSearch;
  window.__koreaCloseSearch=closeSearch;
})();

// Smooth Scroll Anchors
document.querySelectorAll('a[href^="#"]').forEach(function(a){a.addEventListener('click',function(e){var t=document.querySelector(this.getAttribute('href'));if(t){e.preventDefault();t.scrollIntoView({behavior:'smooth'});}});});

// Heading Anchor Links
document.querySelectorAll('.article-body h2,.article-body h3,.article-body h4').forEach(function(h){if(!h.id)return;var l=document.createElement('a');l.className='anchor-link';l.href='#'+h.id;l.setAttribute('aria-label','Link to this section');l.innerHTML='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';h.appendChild(l);});

// TOC Active State
var tocLinks=document.querySelectorAll('.toc a');
if(tocLinks.length>0){var headings=document.querySelectorAll('.article-body h2,.article-body h3,.article-body h4');var obs=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){tocLinks.forEach(function(l){l.classList.remove('active');if(l.getAttribute('href')==='#'+e.target.id)l.classList.add('active');});}});},{rootMargin:'-80px 0px -80% 0px'});headings.forEach(function(h){obs.observe(h);});}

})();
