(()=>{
const isMobile=()=>window.matchMedia('(max-width:720px)').matches;
function settle(){
  document.querySelector('.view-toggle')?.remove();
  document.body.classList.add('mode-advanced');
  document.body.classList.remove('mode-simple');
  if(!isMobile())return;
  document.querySelectorAll('.technical-details,.trend-disclosure,.breadth-disclosure,.washout-disclosure,.alerts-disclosure,.event-details').forEach(d=>d.open=false);
}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',settle,{once:true});else settle();
window.addEventListener('resize',settle);
window.addEventListener('market-pulse-rendered',settle);
window.addEventListener('market-guide-ready',settle);
document.getElementById('refresh')?.addEventListener('click',settle);
})();
