(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='1 · MARKET REGIME';heroEye.dataset.mobileStep='true'}const readPath=document.getElementById('readingPath');if(readPath)readPath.setAttribute('aria-label','Start here: Market Regime, then follow the numbered reading order')}
window.addEventListener('DOMContentLoaded',()=>{setTimeout(mobileDefaults,250);setTimeout(mobileDefaults,1400)});window.addEventListener('resize',mobileDefaults);
})();
