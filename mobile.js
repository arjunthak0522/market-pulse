(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function forceSingleView(){document.querySelector('.view-toggle')?.remove();document.body.classList.add('mode-advanced');document.body.classList.remove('mode-simple');try{localStorage.setItem('marketPulseViewV2','advanced')}catch{}}
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details,.trend-disclosure,.breadth-disclosure,.washout-disclosure,.alerts-disclosure').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='MARKET REGIME';heroEye.dataset.mobileStep='true'}}
window.addEventListener('DOMContentLoaded',()=>{forceSingleView();setTimeout(mobileDefaults,250);setTimeout(()=>{forceSingleView();mobileDefaults()},1400)});window.addEventListener('resize',mobileDefaults);
})();