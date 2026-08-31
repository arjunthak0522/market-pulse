(()=>{
function placeDailyContext(){
  const hero=document.querySelector('.premium-hero');
  const session=document.getElementById('sessionBar');
  const live=document.getElementById('livePulse');
  const daily=document.getElementById('dailyHabit');
  if(!hero)return;
  let anchor=hero;
  for(const node of [session,live,daily]){
    if(node){anchor.after(node);anchor=node;}
  }
}
function boot(){
  placeDailyContext();
  setTimeout(placeDailyContext,350);
  setTimeout(placeDailyContext,1100);
  setTimeout(placeDailyContext,1800);
}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',boot);else boot();
window.addEventListener('resize',placeDailyContext);
document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(placeDailyContext,1400));
})();
