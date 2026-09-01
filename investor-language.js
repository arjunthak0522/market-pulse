(()=>{
const MAP={
  '% above 5-day MA':['One-week participation','5-day breadth'],
  '% above 20-day MA':['One-month participation','20-day breadth'],
  '% above 50-day MA':['Intermediate participation','50-day breadth'],
  '% above 200-day MA':['Long-term participation','200-day breadth'],
  'QQQ vs SPY · 20D':['Growth vs broad-market leadership','QQQ/SPY relative strength'],
  'Distance from 20-day MA':['Short-term trend position','20-day moving average'],
  'Distance from 50-day MA':['Intermediate trend position','50-day moving average'],
  'Distance from 200-day MA':['Long-term trend position','200-day moving average'],
  'RSI (14)':['Momentum stretch','RSI · 14 sessions'],
  'Williams %R (14)':['Fast exhaustion check','Williams %R · 14 sessions'],
  'Bollinger %B':['Price stretch vs normal range','Bollinger %B'],
  'MACD':['Trend momentum','MACD'],
  'ADX (14)':['Trend strength','ADX · 14 sessions'],
  'Equity Put/Call Ratio':['How defensive are traders?','Equity put/call ratio']
};
function plain(s){return String(s||'').replace(/200-day trends?/gi,'long-term trends').replace(/200-day support/gi,'long-term support').replace(/200-day structure/gi,'long-term structure').replace(/50-day trends?/gi,'intermediate trends').replace(/50-day support/gi,'intermediate support').replace(/50-day breadth/gi,'intermediate participation').replace(/20-day trends?/gi,'short-term trends').replace(/5-day trends?/gi,'one-week trends').replace(/\bA\/D\b/gi,'rising-vs-falling balance').replace(/\bTRIN\b/gi,'selling-volume pressure')}
function run(){
  document.querySelectorAll('.card .name').forEach(el=>{
    const raw=(el.dataset.rawLabel||el.textContent||'').trim();
    if(!el.dataset.rawLabel)el.dataset.rawLabel=raw;
    const m=MAP[raw];
    if(!m)return;
    el.textContent=m[0];
    let tech=el.parentElement.querySelector('.metric-tech');
    if(!tech){tech=document.createElement('small');tech.className='metric-tech';el.after(tech)}
    tech.textContent=m[1];
  });
  document.querySelectorAll('.card p').forEach(p=>p.textContent=plain(p.textContent));
  document.querySelectorAll('.risk-card-top span').forEach(el=>{
    const t=el.textContent.trim();
    if(t==='VIX TERM STRUCTURE')el.textContent='HOW URGENT IS FEAR?';
    if(t==='PUT/CALL POSITIONING')el.textContent='HOW DEFENSIVE ARE TRADERS?';
    if(t==='TAIL-RISK DEMAND · SKEW')el.textContent='CRASH-INSURANCE DEMAND';
  });
}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',run,{once:true});else run();
window.addEventListener('market-pulse-rendered',run);
})();
