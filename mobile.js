(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function forceSingleView(){document.querySelector('.view-toggle')?.remove();document.body.classList.add('mode-advanced');document.body.classList.remove('mode-simple');try{localStorage.setItem('marketPulseViewV2','advanced')}catch{}}
function loadTurningPoints(){if(!document.querySelector('link[data-turning-points]')){const l=document.createElement('link');l.rel='stylesheet';l.href='turning-points.css?v=17';l.dataset.turningPoints='true';document.head.appendChild(l)}if(!document.querySelector('script[data-turning-points]')){const s=document.createElement('script');s.src='turning-points.js?v=17';s.defer=true;s.dataset.turningPoints='true';document.head.appendChild(s)}}
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='1 · MARKET REGIME';heroEye.dataset.mobileStep='true'}const readPath=document.getElementById('readingPath');if(readPath)readPath.setAttribute('aria-label','Start here: Market Regime, then follow the numbered reading order')}
loadTurningPoints();
window.addEventListener('DOMContentLoaded',()=>{forceSingleView();setTimeout(mobileDefaults,250);setTimeout(()=>{forceSingleView();mobileDefaults()},1400)});window.addEventListener('resize',mobileDefaults);
})();
