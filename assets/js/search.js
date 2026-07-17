(function(){'use strict';
var searchOverlay=document.querySelector('[data-search-overlay]');
var searchInput=document.getElementById('search-input');
var searchBody=document.querySelector('[data-search-results]');
var searchClose=document.querySelector('[data-search-close]');
var searchToggle=document.querySelectorAll('[data-search-toggle]');
var pf=null;
var currentResults=[];
var selectedIndex=-1;
var abortController=null;

// --- Load Search History
var HISTORY_KEY='kw_search_history';
var MAX_HISTORY=20;
function getHistory(){try{return JSON.parse(localStorage.getItem(HISTORY_KEY))||[]}catch(e){return[]}}
function addHistory(q){if(!q||q.length<2)return;var h=getHistory();h=h.filter(function(e){return e!==q});h.unshift(q);if(h.length>MAX_HISTORY)h.length=MAX_HISTORY;try{localStorage.setItem(HISTORY_KEY,JSON.stringify(h))}catch(e){}}
function clearHistory(){try{localStorage.removeItem(HISTORY_KEY)}catch(e){}}

// --- Filters state
var filters={category:'',tag:'',year:'',author:'',sort:'relevance'};

// --- Load pagefind
function loadPagefind(){return window.pagefind?Promise.resolve(window.pagefind):new Promise(function(resolve){var check=function(){if(window.pagefind){resolve(window.pagefind);return}setTimeout(check,50)};check()})}

// --- Parse advanced query
function parseQuery(q){
  var clean=q;
  var props={};
  var patterns=[
    {re:/category:(\S+)/g,key:'category'},{re:/tag:(\S+)/g,key:'tag'},
    {re:/author:(\S+)/g,key:'author'},{re:/year:(\d{4})/g,key:'year'},
    {re:/before:(\S+)/g,key:'before'},{re:/after:(\S+)/g,key:'after'},
    {re:/title:(\S+)/g,key:'title'}
  ];
  patterns.forEach(function(p){var m;while((m=p.re.exec(clean))!==null){props[p.key]=m[1];clean=clean.replace(m[0],'').trim()}});
  return{query:clean||'*',filters:props};
}

// --- Render
function esc(s){if(!s)return '';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function highlightText(text,query){
  if(!query||query==='*')return esc(text);
  var words=query.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').split(/\s+/).filter(Boolean);
  if(words.length===0)return esc(text);
  var re=new RegExp('('+words.join('|')+')','gi');
  return esc(text).replace(re,'<mark>$1</mark>');
}
function formatDate(ts){
  if(!ts)return '';
  var d=new Date(ts*1000);
  return d.toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric'});
}

function renderResults(results,query,parsed){
  currentResults=results;
  selectedIndex=-1;
  if(!searchBody)return;
  if(!results||results.length===0){
    var history=getHistory();
    var html='<div class="search-empty">';
    html+='<p>No results found.</p>';
    if(history.length>0){
      html+='<div class="search-suggestions"><h4>Recent searches</h4><ul>';
      history.slice(0,5).forEach(function(h){html+='<li><button class="search-suggestion-btn" data-suggestion="'+esc(h)+'">'+esc(h)+'</button></li>'});
      html+='</ul></div>'}
    html+='</div>';
    searchBody.innerHTML=html;
    Array.from(searchBody.querySelectorAll('.search-suggestion-btn')).forEach(function(btn){btn.addEventListener('click',function(){searchInput.value=this.getAttribute('data-suggestion');searchInput.dispatchEvent(new Event('input',{bubbles:true}))})});
    return;
  }
  var html='<div class="search-results-list">';
  results.forEach(function(r,i){
    var meta=r.meta||{};
    var url=r.url||'#';
    var title=highlightText(meta.title||'Untitled',query);
    var snippet=highlightText((r.excerpt||meta.description||'').substring(0,160),query);
    html+='<a class="search-result-item" href="'+esc(url)+'" data-index="'+i+'">';
    html+='<span class="search-result-title">'+title+'</span>';
    if(snippet)html+='<p class="search-result-desc">'+snippet+'</p>';
    html+='<span class="search-result-meta">';
    var parts=[];
    if(meta.category)parts.push(meta.category);
    if(meta.date)parts.push(formatDate(meta.date));
    if(meta.reading_time)parts.push(meta.reading_time+' min read');
    html+=parts.join(' · ')+'</span></a>';
  });
  html+='</div>';
  searchBody.innerHTML=html;
}

// --- Search
function doSearch(){
  var q=searchInput.value.trim();
  var parsed=parseQuery(q);
  if(parsed.query.length===0||(parsed.query==='*'&&Object.keys(parsed.filters).length===0)){
    var history=getHistory();
    var html='<div class="search-hint">';
    html+='<p>Type to search articles...</p>';
    if(history.length>0){
      html+='<div class="search-suggestions"><h4>Recent searches</h4><ul>';
      history.slice(0,5).forEach(function(h){html+='<li><button class="search-suggestion-btn" data-suggestion="'+esc(h)+'">'+esc(h)+'</button></li>'});
      html+='</ul></div>'}
    html+='<div class="search-shortcuts"><span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span><span><kbd>Enter</kbd> Select</span><span><kbd>Esc</kbd> Close</span></div></div>';
    searchBody.innerHTML=html;
    Array.from(searchBody.querySelectorAll('.search-suggestion-btn')).forEach(function(btn){btn.addEventListener('click',function(){searchInput.value=this.getAttribute('data-suggestion');searchInput.dispatchEvent(new Event('input',{bubbles:true}))})});
    return;
  }
  if(abortController)abortController.abort();
  abortController=new AbortController();
  if(!pf){searchBody.innerHTML='<div class="search-empty"><p>Loading search index...</p></div>';return}
  pf.search(parsed.query,{signal:abortController.signal}).then(function(res){
    var results=res.results.slice(0,50);
    // Apply filters
    if(parsed.filters.category)results=results.filter(function(r){var c=(r.meta&&r.meta.category)||'';return c.toLowerCase()===parsed.filters.category.toLowerCase()});
    if(parsed.filters.tag)results=results.filter(function(r){var t=(r.meta&&r.meta.tags)||'';return t.toLowerCase().indexOf(parsed.filters.tag.toLowerCase())>=0});
    if(parsed.filters.year)results=results.filter(function(r){if(!r.meta||!r.meta.date)return false;var y=new Date(r.meta.date*1000).getFullYear().toString();return y===parsed.filters.year});
    if(parsed.filters.author)results=results.filter(function(r){var a=(r.meta&&r.meta.author)||'';return a.toLowerCase().indexOf(parsed.filters.author.toLowerCase())>=0});
    // Sort by date (newest first) as tiebreaker
    results.sort(function(a,b){var da=a.meta&&a.meta.date?a.meta.date:0;var db=b.meta&&b.meta.date?b.meta.date:0;return db-da});
    renderResults(results,q,parsed);
    addHistory(q);
  }).catch(function(err){if(err.name!=='AbortError')console.error(err)});
}

// --- Debounce
var debounceTimer=null;
function onInput(){
  if(debounceTimer)clearTimeout(debounceTimer);
  debounceTimer=setTimeout(doSearch,50);
}

// --- Keyboard navigation
function onKeydown(e){
  if(!searchOverlay.classList.contains('open'))return;
  var items=searchBody.querySelectorAll('.search-result-item');
  if(e.key==='ArrowDown'){e.preventDefault();selectedIndex=Math.min(selectedIndex+1,items.length-1);updateSelected(items)}
  else if(e.key==='ArrowUp'){e.preventDefault();selectedIndex=Math.max(selectedIndex-1,-1);updateSelected(items)}
  else if(e.key==='Enter'&&selectedIndex>=0){e.preventDefault();var link=items[selectedIndex];if(link)link.click()}
  else if(e.key==='Escape'){closeSearch()}
}
function updateSelected(items){
  items.forEach(function(el,i){el.classList.toggle('selected',i===selectedIndex);if(i===selectedIndex)el.scrollIntoView({block:'nearest'})});
}

// --- Open/Close
function openSearch(){
  searchOverlay.classList.add('open');
  document.body.style.overflow='hidden';
  setTimeout(function(){if(searchInput)searchInput.focus()},100);
  doSearch();
}
function closeSearch(){
  searchOverlay.classList.remove('open');
  document.body.style.overflow='';
  selectedIndex=-1;
  if(searchInput)searchInput.value='';
}
if(searchClose)searchClose.addEventListener('click',closeSearch);
if(searchOverlay)searchOverlay.addEventListener('click',function(e){if(e.target===this)closeSearch()});

// --- Toggle buttons
if(searchToggle.length){Array.from(searchToggle).forEach(function(st){st.addEventListener('click',function(){if(searchOverlay.classList.contains('open'))closeSearch();else openSearch()})})}

// --- Global keyboard shortcut
document.addEventListener('keydown',function(e){
  if(e.key==='Escape')closeSearch();
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();if(searchOverlay.classList.contains('open'))closeSearch();else openSearch()}
  if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)){e.preventDefault();openSearch()}
});

// --- Init
if(searchInput){
  searchInput.addEventListener('input',onInput);
  searchInput.addEventListener('keydown',onKeydown);
  searchInput.addEventListener('focus',function(){if(searchBody)searchBody.style.outline='none'});
}
// Load pagefind after the initial render
function init(){
  loadPagefind().then(function(p){pf=p;if(pf.options){pf.options.baseUrl='/koreawiki/pagefind/'}}).catch(function(){});
  // Preload index after idle
  if('requestIdleCallback' in window){requestIdleCallback(function(){if(pf)pf.preload()})}else{setTimeout(function(){if(pf)pf.preload()},2000)}
}
if(document.readyState==='complete')init();else window.addEventListener('load',init);
})();
