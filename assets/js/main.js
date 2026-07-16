(function(){'use strict';

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

// Smooth Scroll Anchors (+ open FAQ <details> when jumping to #faq-N)
function openFaqTarget(el){
  if(!el)return;
  var details=el.closest?el.closest('details'):null;
  if(el.tagName&&el.tagName.toLowerCase()==='details')details=el;
  if(details){
    details.open=true;
    // close siblings optional? keep others as-is
  }
}
function scrollToHash(hash){
  if(!hash||hash==='#')return;
  var t=null;
  try{t=document.querySelector(hash);}catch(err){return;}
  if(!t)return;
  openFaqTarget(t);
  t.scrollIntoView({behavior:'smooth',block:'start'});
}
document.querySelectorAll('a[href^="#"]').forEach(function(a){
  a.addEventListener('click',function(e){
    var href=this.getAttribute('href');
    if(!href||href==='#')return;
    var t=null;
    try{t=document.querySelector(href);}catch(err){return;}
    if(!t)return;
    e.preventDefault();
    openFaqTarget(t);
    t.scrollIntoView({behavior:'smooth',block:'start'});
    if(history.pushState)history.pushState(null,'',href);
    else location.hash=href;
  });
});
// Deep-link on load: /article/#faq-2 opens that FAQ
if(location.hash){
  // delay so layout/fonts settle
  setTimeout(function(){scrollToHash(location.hash);},50);
}

// Live stamp: format first-live GitHub time in visitor local timezone
// Output: dd-mm-yyyy hh:mm:ss GMT±N  (commit id stays in markup after |)
(function(){
  function pad(n){return String(n).padStart(2,'0');}
  function gmtLabel(date){
    // getTimezoneOffset: minutes *west* of UTC; flip for GMT+east
    var offMin=-date.getTimezoneOffset();
    var sign=offMin>=0?'+':'-';
    var abs=Math.abs(offMin);
    var h=Math.floor(abs/60);
    var m=abs%60;
    return m?('GMT'+sign+h+':'+pad(m)):('GMT'+sign+h);
  }
  function formatLocal(date){
    return pad(date.getDate())+'-'+pad(date.getMonth()+1)+'-'+date.getFullYear()
      +' '+pad(date.getHours())+':'+pad(date.getMinutes())+':'+pad(date.getSeconds())
      +' '+gmtLabel(date);
  }
  function hydrate(el){
    var iso=el.getAttribute('data-live-iso');
    var unix=el.getAttribute('data-live-unix');
    var d=null;
    if(iso)d=new Date(iso);
    if((!d||isNaN(d.getTime()))&&unix)d=new Date(Number(unix)*1000);
    if(!d||isNaN(d.getTime()))return;
    var timeEl=el.querySelector('[data-live-time]');
    if(timeEl){
      timeEl.textContent=formatLocal(d);
      timeEl.setAttribute('datetime',d.toISOString());
    }
  }
  document.querySelectorAll('[data-live-stamp]').forEach(hydrate);
})();

// Heading Anchor Links
document.querySelectorAll('.article-body h2,.article-body h3,.article-body h4').forEach(function(h){if(!h.id)return;var l=document.createElement('a');l.className='anchor-link';l.href='#'+h.id;l.setAttribute('aria-label','Link to this section');l.innerHTML='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';h.appendChild(l);});

// TOC Active State
var tocLinks=document.querySelectorAll('.toc a');
if(tocLinks.length>0){var headings=document.querySelectorAll('.article-body h2,.article-body h3,.article-body h4');var obs=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){tocLinks.forEach(function(l){l.classList.remove('active');if(l.getAttribute('href')==='#'+e.target.id)l.classList.add('active');});}});},{rootMargin:'-80px 0px -80% 0px'});headings.forEach(function(h){obs.observe(h);});}

// Nav Buttons show/hide on scroll
(function(){
  var btns=document.querySelector('.nav-buttons');
  if(!btns)return;
  var lastScroll=0;
  window.addEventListener('scroll',function(){
    var y=window.scrollY||window.pageYOffset;
    if(y>300){btns.style.opacity='1';btns.style.pointerEvents='auto';}
    else{btns.style.opacity='0';btns.style.pointerEvents='none';}
  },{passive:true});
  // start hidden
  btns.style.opacity='0';btns.style.pointerEvents='none';btns.style.transition='opacity .25s ease';
})();

})();
