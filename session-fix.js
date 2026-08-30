(()=>{
const ET='America/New_York';
const $=id=>document.getElementById(id);
function parts(d=new Date(),tz=ET){const a=new Intl.DateTimeFormat('en-US',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d);return Object.fromEntries(a.map(x=>[x.type,x.value]))}
function ymd(d=new Date(),tz=ET){const p=parts(d,tz);return `${p.year}-${p.month}-${p.day}`}
function dateUTC(y,m,d){return new Date(Date.UTC(y,m-1,d,12))}
function nthWeekday(y,m,weekday,n){const first=dateUTC(y,m,1),shift=(weekday-first.getUTCDay()+7)%7;return dateUTC(y,m,1+shift+7*(n-1))}
function lastWeekday(y,m,weekday){const last=dateUTC(y,m+1,0),shift=(last.getUTCDay()-weekday+7)%7;return dateUTC(y,m,last.getUTCDate()-shift)}
function observed(y,m,d){const x=dateUTC(y,m,d),wd=x.getUTCDay();if(wd===6)x.setUTCDate(x.getUTCDate()-1);if(wd===0)x.setUTCDate(x.getUTCDate()+1);return x}
function easter(y){const a=y%19,b=Math.floor(y/100),c=y%100,d=Math.floor(b/4),e=b%4,f=Math.floor((b+8)/25),g=Math.floor((b-f+1)/3),h=(19*a+b-d-g+15)%30,i=Math.floor(c/4),k=c%4,l=(32+2*e+2*i-h-k)%7,m=Math.floor((a+11*h+22*l)/451),month=Math.floor((h+l-7*m+114)/31),day=((h+l-7*m+114)%31)+1;return dateUTC(y,month,day)}
function key(d){return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`}
function nyseHoliday(dateKey){const y=Number(dateKey.slice(0,4));const e=easter(y),goodFriday=new Date(e);goodFriday.setUTCDate(e.getUTCDate()-2);const dates=[observed(y,1,1),nthWeekday(y,1,1,3),nthWeekday(y,2,1,3),goodFriday,lastWeekday(y,5,1),observed(y,6,19),observed(y,7,4),nthWeekday(y,9,1,1),nthWeekday(y,11,4,4),observed(y,12,25)];return dates.some(x=>key(x)===dateKey)}
function phase(now=new Date()){const p=parts(now),mins=Number(p.hour)*60+Number(p.minute),dateKey=`${p.year}-${p.month}-${p.day}`,weekday=['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday);if(!weekday||nyseHoliday(dateKey))return'closed';if(mins<570)return'pre';if(mins<960)return'open';return'after'}
function formatDateToken(token){const m=String(token).match(/^(\d{4})-(\d{2})-(\d{2})$/);if(!m)return token;const d=new Date(`${m[1]}-${m[2]}-${m[3]}T12:00:00Z`);return new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(d)}
function formatPrecedentDates(){for(const id of['analogTitle','analogText']){const el=$(id);if(el)el.textContent=el.textContent.replace(/\b\d{4}-\d{2}-\d{2}\b/g,formatDateToken)}}
async function confirmedMarketDate(){try{const r=await fetch(`data/market_context.json?v=${Date.now()}`,{cache:'no-store'});if(!r.ok)return null;return (await r.json()).market_date||null}catch{return null}}
async function applyReadVisibility(){const habit=$('dailyHabit'),morning=$('morningTitle')?.closest('article'),closing=$('closingTitle')?.closest('article');if(!habit||!morning||!closing)return;const p=phase(),today=ymd();let showMorning=false,showClosing=false;if(p==='pre'||p==='open')showMorning=true;else if(p==='closed')showClosing=true;else if(p==='after'){const md=await confirmedMarketDate();showClosing=md===today}morning.hidden=!showMorning;closing.hidden=!showClosing;habit.hidden=!(showMorning||showClosing);habit.classList.toggle('single-read',showMorning!==showClosing)}
function observe(){const target=$('analogBox')||document.body;const obs=new MutationObserver(()=>formatPrecedentDates());obs.observe(target,{subtree:true,childList:true,characterData:true});formatPrecedentDates()}
async function refresh(){formatPrecedentDates();await applyReadVisibility()}
window.addEventListener('DOMContentLoaded',()=>{setTimeout(()=>{observe();refresh()},300);setTimeout(refresh,1500)});window.addEventListener('focus',refresh);document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(refresh,1100));setInterval(refresh,60000);
})();
