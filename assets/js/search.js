(function(){'use strict';
var input=document.getElementById('search-input');
var results=document.querySelector('[data-search-results]');
var fuse=null;

function getIndexURL(){var base=document.querySelector('base');var u=base?base.getAttribute('href'):'/';return u+'index.json';}
function loadIndex(){return fetch(getIndexURL()).then(function(r){return r.json();}).catch(function(){var e=window.location.pathname.split('/')[1];return fetch('/'+(e==='ko'||e==='vi'?e+'/':'')+'index.json').then(function(r){return r.json();});});}
function initFuse(data){fuse=new Fuse(data,{keys:[{name:'title',weight:.4},{name:'description',weight:.3},{name:'tags',weight:.2},{name:'categories',weight:.1}],threshold:.4,includeScore:true,minMatchCharLength:2});}
function render(r){if(!results)return;if(r.length===0){results.innerHTML='<div class="search-empty"><p>No results found. Try different keywords.</p></div>';return;}
var html='';r.forEach(function(res){var i=res.item;html+='<a class="search-result-item" href="'+i.permalink+'">';html+='<span class="search-result-title">'+i.title+'</span>';if(i.description){html+='<p class="search-result-desc">'+i.description+'</p>';}
html+='<span class="search-result-meta">';if(i.section)html+=i.section;if(i.date)html+=' &middot; '+i.date;html+='</span></a>';});results.innerHTML=html;}
if(input&&results){loadIndex().then(function(data){initFuse(data);input.addEventListener('input',function(){var q=this.value.trim();if(q.length<2){results.innerHTML='<div class="search-hint"><p>Type at least 2 characters to search...</p></div>';return;}
var res=fuse.search(q);render(res);});}).catch(function(){results.innerHTML='<div class="search-empty"><p>Search index could not be loaded.</p></div>';});}
})();
