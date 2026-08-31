(()=>{
const ET='America/New_York';
function sessionPhase(now=new Date()){
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:ET,weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now);
  const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));
  const weekday=['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday);
  if(!weekday)return'closed';
  const mins=Number(p.hour)*60+Number(p.minute);
  if(mins<570)return'pre';
  if(mins<960)return'open';
  return'after';
}
function ensurePolish(){
  if(document.getElementById('briefingQaPolish'))return;
  const s=document.createElement('style');
  s.id='briefingQaPolish';
  s.textContent=`
    #premiumStateStrip,#regimeEvidence{display:none!important}
    .premium-hero .hero-grid{grid-template-columns:1fr!important;gap:0!important}
    .premium-hero .hero-chart{display:none!important}
    .premium-hero{padding:16px 18px!important}
    .premium-hero .regime-thesis{max-width:880px!important}
    @media(max-width:720px){
      .premium-hero{padding:13px 14px!important}
      .premium-hero .regime-display{font-size:28px!important}
      .premium-hero .regime-thesis{margin-top:6px!important}
      .key-readings-grid small{font-size:8.5px!important;line-height:1.28!important}
      .key-readings-grid span{font-size:9.8px!important;line-height:1.15!important}
    }
  `;
  document.head.appendChild(s);
}
function enforceSessionRead(){
  const daily=document.getElementById('dailyHabit');
  const morning=document.getElementById('morningCard');
  const closing=document.getElementById('closingCard');
  if(!daily||!morning||!closing)return;
  const phase=sessionPhase();
  if(phase==='open'){
    morning.hidden=true;
    closing.hidden=true;
    daily.hidden=true;
  }
}
function placeDailyContext(){
  ensurePolish();
  const hero=document.querySelector('.premium-hero');
  const session=document.getElementById('sessionBar');
  const live=document.getElementById('livePulse');
  const daily=document.getElementById('dailyHabit');
  if(!hero)return;
  let anchor=hero;
  for(const node of [session,live,daily]){
    if(node){anchor.after(node);anchor=node;}
  }
  enforceSessionRead();
}
function boot(){
  placeDailyContext();
  setTimeout(placeDailyContext,350);
  setTimeout(placeDailyContext,1100);
  setTimeout(placeDailyContext,1800);
  setInterval(placeDailyContext,10000);
}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',boot);else boot();
window.addEventListener('resize',placeDailyContext);
document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(placeDailyContext,1400));
})();
