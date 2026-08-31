(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function forceSingleView(){document.querySelector('.view-toggle')?.remove();document.body.classList.add('mode-advanced');document.body.classList.remove('mode-simple');try{localStorage.setItem('marketPulseViewV2','advanced')}catch{}}
function loadSessionOrder(){if(document.querySelector('script[data-session-order]'))return;const s=document.createElement('script');s.src='session-order.js?v=22';s.defer=true;s.dataset.sessionOrder='true';document.head.appendChild(s)}
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='1 · MARKET REGIME';heroEye.dataset.mobileStep='true'}const readPath=document.getElementById('readingPath');if(readPath)readPath.setAttribute('aria-label','Start with the market read, then move into tactical setup, leadership and index detail')}
loadSessionOrder();
window.addEventListener('DOMContentLoaded',()=>{forceSingleView();setTimeout(mobileDefaults,250);setTimeout(()=>{forceSingleView();mobileDefaults()},1400)});window.addEventListener('resize',mobileDefaults);
})();
