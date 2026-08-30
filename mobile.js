(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function formatDateToken(token){const m=String(token).match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return token;const d=new Date(`${m[1]}-${m[2]}-${m[3]}T12:00:00Z`);return new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(d)}
function formatHistoricalDates(root=document){const targets=[root.querySelector?.('#analogTitle'),root.querySelector?.('#analogText')].filter(Boolean);for(const el of targets){el.textContent=el.textContent.replace(/\b\d{4}-\d{2}-\d{2}\b/g,formatDateToken)}}
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='1 · MARKET REGIME';heroEye.dataset.mobileStep='true'}const readPath=document.getElementById('readingPath');if(readPath)readPath.setAttribute('aria-label','Start here: Market Regime, then follow the numbered reading order')}
function observeDates(){const target=document.getElementById('analogBox')||document.body;const obs=new MutationObserver(()=>formatHistoricalDates(document));obs.observe(target,{subtree:true,childList:true,characterData:true});formatHistoricalDates(document)}
window.addEventListener('DOMContentLoaded',()=>{setTimeout(()=>{mobileDefaults();observeDates()},250);setTimeout(mobileDefaults,1400)});window.addEventListener('resize',mobileDefaults);
})();
