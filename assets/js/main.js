(function(){'use strict';

// Reading Progress
var progressBar=document.getElementById('readingProgress');
if(progressBar){
  window.addEventListener('scroll',function(){
    var scrollTop=window.scrollY;
    var docHeight=document.documentElement.scrollHeight-window.innerHeight;
    var progress=docHeight>0?(scrollTop/docHeight)*100:0;
    progressBar.style.width=progress+'%';
  },{passive:true});
}

// Dark Mode
var themeToggle=document.querySelector('.theme-toggle');
var html=document.documentElement;
function getPreferredTheme(){var s=localStorage.getItem('theme');if(s)return s;return window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
function setTheme(t){html.setAttribute('data-theme',t);localStorage.setItem('theme',t);}
if(themeToggle){setTheme(getPreferredTheme());themeToggle.addEventListener('click',function(){var c=html.getAttribute('data-theme');setTheme(c==='dark'?'light':'dark');});window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){if(!localStorage.getItem('theme'))setTheme(e.matches?'dark':'light');});}

// Mobile Nav
var navToggle=document.querySelector('.header-nav-toggle');
var navList=document.querySelector('.header-nav-list');
if(navToggle&&navList){navToggle.addEventListener('click',function(){var e=this.getAttribute('aria-expanded')==='true';this.setAttribute('aria-expanded',!e);navList.classList.toggle('open');});document.addEventListener('click',function(e){if(!navToggle.contains(e.target)&&!navList.contains(e.target)){navToggle.setAttribute('aria-expanded','false');navList.classList.remove('open');}});}

// Copy Link
var copyBtn=document.querySelector('[data-copy-url]');
if(copyBtn){copyBtn.addEventListener('click',function(){var u=this.getAttribute('data-copy-url');if(navigator.clipboard){navigator.clipboard.writeText(u).then(function(){var o=copyBtn.innerHTML;copyBtn.innerHTML='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';setTimeout(function(){copyBtn.innerHTML=o;},2000);});}});}

// Search Overlay
var searchToggle=document.querySelectorAll('[data-search-toggle]');
var searchOverlay=document.querySelector('[data-search-overlay]');
var searchClose=document.querySelector('[data-search-close]');
var searchInput=document.getElementById('search-input');
if(searchToggle.length&&searchOverlay){Array.from(searchToggle).forEach(function(st){st.addEventListener('click',function(){searchOverlay.classList.add('open');if(searchInput)setTimeout(function(){searchInput.focus();},100);document.body.style.overflow='hidden';});});}
function closeSearch(){if(searchOverlay){searchOverlay.classList.remove('open');document.body.style.overflow='';}}
if(searchClose){searchClose.addEventListener('click',closeSearch);}
if(searchOverlay){searchOverlay.addEventListener('click',function(e){if(e.target===this)closeSearch();});}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeSearch();if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();if(searchToggle.length)searchToggle[0].click();}});

// Smooth Scroll Anchors
document.querySelectorAll('a[href^="#"]').forEach(function(a){a.addEventListener('click',function(e){var t=document.querySelector(this.getAttribute('href'));if(t){e.preventDefault();t.scrollIntoView({behavior:'smooth'});}});});

// Heading Anchor Links
document.querySelectorAll('.article-body h2,.article-body h3,.article-body h4').forEach(function(h){if(!h.id)return;var l=document.createElement('a');l.className='anchor-link';l.href='#'+h.id;l.setAttribute('aria-label','Link to this section');l.innerHTML='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';h.appendChild(l);});

// TOC Active State
var tocLinks=document.querySelectorAll('.toc a');
if(tocLinks.length>0){var headings=document.querySelectorAll('.article-body h2,.article-body h3,.article-body h4');var obs=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){tocLinks.forEach(function(l){l.classList.remove('active');if(l.getAttribute('href')==='#'+e.target.id)l.classList.add('active');});}});},{rootMargin:'-80px 0px -80% 0px'});headings.forEach(function(h){obs.observe(h);});}

})();
