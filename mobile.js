(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function forceSingleView(){document.querySelector('.view-toggle')?.remove();document.body.classList.add('mode-advanced');document.body.classList.remove('mode-simple');try{localStorage.setItem('marketPulseViewV2','advanced')}catch{}}
function loadOptionsRisk(){if(!document.querySelector('link[data-options-risk]')){const l=document.createElement('link');l.rel='stylesheet';l.href='options-risk.css?v=19';l.dataset.optionsRisk='true';document.head.appendChild(l)}if(!document.querySelector('script[data-options-risk]')){const s=document.createElement('script');s.src='options-risk.js?v=19';s.defer=true;s.dataset.optionsRisk='true';document.head.appendChild(s)}}
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='1 · MARKET REGIME';heroEye.dataset.mobileStep='true'}const readPath=document.getElementById('readingPath');if(readPath)readPath.setAttribute('aria-label','Start with the market read, then move into tactical setup, leadership and index detail')}
loadOptionsRisk();
window.addEventListener('DOMContentLoaded',()=>{forceSingleView();setTimeout(mobileDefaults,250);setTimeout(()=>{forceSingleView();mobileDefaults()},1400)});window.addEventListener('resize',mobileDefaults);
})();
