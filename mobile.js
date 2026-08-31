(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function forceSingleView(){document.querySelector('.view-toggle')?.remove();document.body.classList.add('mode-advanced');document.body.classList.remove('mode-simple');try{localStorage.setItem('marketPulseViewV2','advanced')}catch{}}
function loadSessionOrder(){if(document.querySelector('script[data-session-order]'))return;const s=document.createElement('script');s.src='session-order.js?v=23';s.defer=true;s.dataset.sessionOrder='true';document.head.appendChild(s)}
function loadInvestorLanguage(){if(document.querySelector('script[data-investor-language]'))return;if(!document.querySelector('link[data-investor-language]')){const l=document.createElement('link');l.rel='stylesheet';l.href='investor-language.css?v=23';l.dataset.investorLanguage='true';document.head.appendChild(l)}const s=document.createElement('script');s.src='investor-language.js?v=23';s.defer=true;s.dataset.investorLanguage='true';document.head.appendChild(s)}
function mobileDefaults(){if(!isMobile())return;document.querySelectorAll('.technical-details').forEach(d=>d.open=false);const heroEye=document.querySelector('.premium-hero .eyebrow');if(heroEye&&!heroEye.dataset.mobileStep){heroEye.textContent='MARKET REGIME';heroEye.dataset.mobileStep='true'}}
loadSessionOrder();loadInvestorLanguage();
window.addEventListener('DOMContentLoaded',()=>{forceSingleView();setTimeout(mobileDefaults,250);setTimeout(()=>{forceSingleView();mobileDefaults()},1400)});window.addEventListener('resize',mobileDefaults);
})();