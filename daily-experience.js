(()=>{
function load(){if(document.querySelector('script[data-agency-hero]'))return;const s=document.createElement('script');s.src='agency-hero.js?v=1';s.defer=true;s.dataset.agencyHero='1';document.body.appendChild(s)}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',load);else load();
})();
