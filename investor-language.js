(()=>{
const MAP={
  '% above 5-day MA':['Very short-term participation','5-day breadth'],
  '% above 20-day MA':['Short-term participation','20-day breadth'],
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
    const m=MAP[raw]; if(!m)return;
    el.textContent=m[0];
    if(!el.parentElement.querySelector('.metric-tech')){
      const small=document.createElement('small');small.className='metric-tech';small.textContent=m[1];el.after(small);
    }
  });
}
function simplifyStatic(){
  document.getElementById('chips')?.remove();
  const breadth=document.querySelector('.breadth-module');
  if(breadth){
    breadth.querySelector('.eyebrow')?.replaceChildren(document.createTextNode('MARKET PARTICIPATION'));
    const h=breadth.querySelector('h2');if(h)h.textContent='How broadly is the market participating?';
    const p=breadth.querySelector('.module-header p');if(p)p.textContent='This shows whether strength or weakness is being confirmed by many stocks, or driven by only a narrow group.';
    const lab=breadth.querySelector('.breadth-viz .insight-label');if(lab)lab.textContent='INTERMEDIATE PARTICIPATION · 60 SESSIONS';
  }
  const tac=document.getElementById('chapterTactical');if(tac){const s=tac.querySelector('span');if(s)s.textContent='SHORT-TERM TURNING POINTS';const b=tac.querySelector('strong');if(b)b.textContent='Is selling becoming exhausted, and are buyers beginning to return?'}
  const tp=document.getElementById('turningPointInternals');if(tp){const step=tp.querySelector('.section-step');if(step)step.textContent='TURNING POINT EVIDENCE';}
  document.querySelectorAll('.tp-card-top span').forEach(el=>{
    const t=el.textContent.trim();
    if(t==='A/D BREADTH')el.textContent='STOCKS RISING VS FALLING';
    if(t==='RSI BREADTH')el.textContent='HOW MANY STOCKS ARE OVERSOLD?';
    if(t==='S&P 500 TRIN')el.textContent='SELLING-VOLUME PRESSURE';
  });
  document.querySelectorAll('.tp-card-top small').forEach(el=>{
    const t=el.textContent.trim();
    if(t==='Participation')el.textContent='Market participation · A/D';
    if(t==='Exhaustion')el.textContent='Oversold breadth · RSI < 30';
    if(t==='Volume pressure')el.textContent='S&P 500 TRIN · Arms-style';
  });
  document.querySelectorAll('.trend-table thead th').forEach(th=>{
    const t=th.textContent.trim();
    if(t==='20D tactical')th.innerHTML='Short-term<br><small>20-day trend</small>';
    if(t==='50D intermediate')th.innerHTML='Intermediate<br><small>50-day trend</small>';
    if(t==='200D regime')th.innerHTML='Long-term<br><small>200-day trend</small>';
  });
  document.querySelectorAll('.history-context-grid article span').forEach(el=>{
    if(el.textContent.trim()==='INTERMEDIATE BREADTH')el.textContent='INTERMEDIATE PARTICIPATION';
    if(el.textContent.trim()==='FEAR URGENCY')el.textContent='NEAR-TERM FEAR';
  });
  document.querySelectorAll('.risk-card-top span').forEach(el=>{
    if(el.textContent.trim()==='VIX TERM STRUCTURE')el.textContent='HOW URGENT IS FEAR?';
    if(el.textContent.trim()==='PUT/CALL POSITIONING')el.textContent='HOW DEFENSIVE ARE TRADERS?';
    if(el.textContent.trim()==='TAIL-RISK DEMAND · SKEW')el.textContent='CRASH-INSURANCE DEMAND';
  });
  const stress=document.querySelector('.stress-module');if(stress){const eye=stress.querySelector('.eyebrow');if(eye)eye.textContent='SELLING STRESS';}
  document.querySelectorAll('.asset-switcher-wrap .eyebrow').forEach(el=>el.textContent='INDEX DETAIL');
}
function run(){simplifyStatic();relabelCards();}
function boot(){run();[300,800,1400,2200].forEach(ms=>setTimeout(run,ms));}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',boot);else boot();
document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(run,1600));
})();