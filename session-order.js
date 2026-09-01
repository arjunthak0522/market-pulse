(()=>{
const ET='America/New_York';
function sessionPhase(now=new Date()){
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:ET,weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now);
  const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));
  if(!['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday))return'closed';
  const mins=Number(p.hour)*60+Number(p.minute);
  if(mins<570)return'pre';
  if(mins<960)return'open';
  return'after';
}
function applySessionVisibility(){
  const phase=sessionPhase();
  const daily=document.getElementById('dailyHabit');
  const morning=document.getElementById('morningCard');
  const closing=document.getElementById('closingCard');
  if(!daily||!morning||!closing)return;
  if(phase==='pre'){
    daily.hidden=false;
    morning.hidden=false;
    closing.hidden=true;
  }else if(phase==='after'){
    daily.hidden=false;
    morning.hidden=true;
    closing.hidden=false;
  }else{
    daily.hidden=true;
    morning.hidden=true;
    closing.hidden=true;
  }
}
function boot(){applySessionVisibility()}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
window.addEventListener('focus',applySessionVisibility);
document.getElementById('refresh')?.addEventListener('click',applySessionVisibility);
})();
