(()=>{
const $=id=>document.getElementById(id);
const n=v=>v===null||v===undefined||v===''?null:(Number.isFinite(Number(v))?Number(v):null);
const MAP={
  '% above 5-day MA':['One-week participation','5-day breadth'],
  '% above 20-day MA':['One-month participation','20-day breadth'],
  '% above 50-day MA':['Intermediate participation','50-day breadth'],
  '% above 200-day MA':['Long-term participation','200-day breadth'],
  'QQQ vs SPY · 20D':['Growth vs broad-market leadership','QQQ vs SPY · 20 sessions'],
  'Distance from 20-day MA':['Short-term trend position','20-day moving average'],
  'Distance from 50-day MA':['Intermediate trend position','50-day moving average'],
  'Distance from 200-day MA':['Long-term trend position','200-day moving average'],
  'RSI (14)':['Momentum stretch','RSI · 14 sessions'],
  'Williams %R (14)':['Fast momentum stretch','Williams %R · 14 sessions'],
  'Bollinger %B':['Price stretch vs normal range','Bollinger %B'],
  'MACD':['Trend momentum','MACD'],
  'ADX (14)':['Trend strength','ADX · 14 sessions'],
  'Equity Put/Call Ratio':['Options positioning','Equity put/call ratio']
};
function relabelCards(){
  document.querySelectorAll('.card .name').forEach(el=>{
    const raw=(el.dataset.rawLabel||el.textContent||'').trim();
    if(!el.dataset.rawLabel)el.dataset.rawLabel=raw;
    const m=MAP[raw];if(!m)return;
    el.textContent=m[0];
    if(!el.parentElement.querySelector('.metric-tech')){const s=document.createElement('small');s.className='metric-tech';s.textContent=m[1];el.after(s)}
  });
  document.querySelectorAll('.card p').forEach(p=>{p.textContent=p.textContent.replace(/5-day average/gi,'one-week trend').replace(/20-day average/gi,'one-month trend').replace(/50-day average/gi,'intermediate trend').replace(/200-day average/gi,'long-term trend')});
}
function hero(){
  $('chips')?.remove();
  const cells=document.querySelectorAll('#premiumStateStrip .state-cell');
  const labels=['PRIMARY TREND','PARTICIPATION','STRESS'];
  cells.forEach((c,i)=>{if(i>2){c.remove();return}const s=c.querySelector('span');if(s)s.textContent=labels[i]});
}
function health(){
  const cells=document.querySelectorAll('#healthGrid .health-cell');
  const labels=['PRIMARY TREND','MARKET PARTICIPATION','MARKET STRESS'];
  cells.forEach((c,i)=>{if(i>2){c.classList.add('supporting-health');return}const s=c.querySelector('.health-cell-head span');if(s)s.textContent=labels[i]});
  document.querySelector('.role-legend')?.classList.add('ux-secondary');
}
function trend(){
  document.querySelectorAll('.trend-table thead th').forEach((th,i)=>{const x=[['INDEX',''],['SHORT TERM','20-day trend'],['INTERMEDIATE','50-day trend'],['LONG TERM','200-day trend']][i];if(x)th.innerHTML=x[0]+(x[1]?`<small>${x[1]}</small>`:'')});
  const table=document.querySelector('.trend-table');
  if(table&&!table.closest('.trend-disclosure')){const d=document.createElement('details');d.className='trend-disclosure';const s=document.createElement('summary');s.textContent='See the trend levels';table.before(d);d.append(s,table)}
}
function participation(){
  const m=document.querySelector('.breadth-module');if(m){const eye=m.querySelector('.eyebrow'),h=m.querySelector('h2'),p=m.querySelector('.module-header p'),lab=m.querySelector('.breadth-viz .insight-label');if(eye)eye.textContent='MARKET PARTICIPATION';if(h)h.textContent='Is the strength or weakness broad across the market?';if(p)p.textContent='This shows whether many S&P 500 stocks are moving with the indexes, or whether only a narrow group is carrying the market.';if(lab)lab.textContent='INTERMEDIATE PARTICIPATION · 60 SESSIONS'}
  const grid=$('breadth');if(grid&&!grid.closest('.breadth-disclosure')){const d=document.createElement('details');d.className='breadth-disclosure';const s=document.createElement('summary');s.textContent='Inspect participation details';grid.before(d);d.append(s,grid)}
}
function turning(){
  document.querySelectorAll('#tpGrid .tp-card').forEach(c=>{const label=c.querySelector('.tp-card-top span'),small=c.querySelector('.tp-card-top small');if(!label)return;const t=label.textContent.trim();if(t==='A/D BREADTH'||t==='DAILY PARTICIPATION BALANCE'){label.textContent='STOCKS RISING VS FALLING';if(small)small.textContent='Advancers vs decliners'}else if(t==='RSI BREADTH'||t==='STOCKS ALREADY OVERSOLD'){label.textContent='HOW MANY STOCKS ARE OVERSOLD?';if(small)small.textContent='Breadth exhaustion'}else if(t==='S&P 500 TRIN'||t==='SELLING-VOLUME PRESSURE'){label.textContent='SELLING-VOLUME PRESSURE';if(small)small.textContent='S&P 500 TRIN · Arms-style'}});
  const tp=$('turningPointInternals'),stress=document.querySelector('.stress-module');
  if(tp&&stress&&!stress.closest('.washout-disclosure')){const d=document.createElement('details');d.className='washout-disclosure';const s=document.createElement('summary');s.textContent='Inspect the washout checklist';stress.before(d);d.append(s,stress);tp.appendChild(d)}
}
function intelligence(){
  const analog=$('analogBox');if(analog)analog.hidden=true;
  const truth=$('regimeHistoryTruth'),historyCard=$('historyContext')?.closest('.intel-card');
  if(truth&&historyCard&&!historyCard.querySelector('.regime-history-inline')){const x=document.createElement('div');x.className='regime-history-inline';const strong=truth.querySelector('strong')?.textContent||'',p=truth.querySelector('p')?.textContent||'';x.innerHTML=`<span>OFFICIAL REGIME HISTORY</span><strong>${strong}</strong><p>${p}</p>`;historyCard.appendChild(x);truth.hidden=true}
}
function options(){
  document.querySelectorAll('.risk-card-top span').forEach(el=>{const t=el.textContent.trim();if(t==='VIX TERM STRUCTURE')el.textContent='HOW URGENT IS FEAR?';if(t==='PUT/CALL POSITIONING')el.textContent='HOW DEFENSIVE ARE TRADERS?';if(t==='TAIL-RISK DEMAND · SKEW')el.textContent='CRASH-INSURANCE DEMAND'});
}
function alerts(){
  const a=document.querySelector('.alerts-module');if(a&&!a.closest('.alerts-disclosure')){const d=document.createElement('details');d.className='alerts-disclosure';const s=document.createElement('summary');s.textContent='Smart alerts · optional';a.before(d);d.append(s,a)}
}
function watch(){
  const h=$('guideWatchHeadline'),p=$('guideWatchText');if(h){const map={'50-day breadth':'Intermediate participation','50-day repair':'Intermediate trend repair','200-day repair':'Long-term trend repair','Volatility normalization':'Fear cooling'};const k=h.textContent.trim();if(map[k])h.textContent=map[k]}
  if(p)p.textContent=p.textContent.replace(/50-day breadth/gi,'intermediate participation').replace(/50-day (average|trend)/gi,'intermediate trend').replace(/200-day (average|trend)/gi,'long-term trend').replace(/20-day (average|trend)/gi,'short-term trend');
}
function morning(d){const t=$('morningText');if(!t)return;const b=d.breadth||{},s=d.etfs?.SPY||{},q=d.etfs?.QQQ||{},b5=n(b.above_5d),b50=n(b.above_50d),v=n(d.vix?.value);let opening=n(s.distance_ma200)<0||n(q.distance_ma200)<0?'The prior close still shows long-term trend damage.':'The prior close still supports the primary uptrend.';let part=b5==null?'Short-term participation is unavailable.':b5<30?`Only ${b5.toFixed(0)}% of S&P 500 stocks are holding above their one-week trend, so selling is broad.`:b5<50?`${b5.toFixed(0)}% of S&P 500 stocks are above their one-week trend, so short-term participation is soft.`:`${b5.toFixed(0)}% of S&P 500 stocks are above their one-week trend, so short-term participation is healthy.`;let next=b50!=null&&b50<50?'Watch whether intermediate participation recovers or keeps fading.':'Watch whether intermediate participation stays healthy and SPY/QQQ hold intermediate support.';if(v!=null&&v>=20)next+=' Volatility is elevated, so further stress matters more.';t.textContent=`${opening} ${part} ${next}`}
function run(d){hero();health();trend();participation();turning();intelligence();options();alerts();watch();relabelCards();morning(d)}
async function boot(){try{const r=await fetch(`data/market_context.json?v=${Date.now()}`,{cache:'no-store'});if(!r.ok)return;const d=await r.json();[0,300,800,1400,2200].forEach(ms=>setTimeout(()=>run(d),ms))}catch(e){console.warn('Investor language:',e)}}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',boot);else boot();
document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(boot,900));
})();