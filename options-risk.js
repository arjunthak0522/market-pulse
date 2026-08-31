(()=>{
const $=id=>document.getElementById(id);
const n=v=>Number.isFinite(Number(v))?Number(v):null;
const f=(v,d=2)=>n(v)==null?'—':n(v).toFixed(d);

function termRead(r){
  if(r==null)return['Unavailable','Term-structure data is unavailable.','VIX measures roughly one-month implied volatility; VIX3M looks roughly three months out. Comparing them shows whether fear is concentrated right now.'];
  if(r>1)return['Inverted · acute stress',`VIX is ${f(r,2)}× VIX3M. Near-term volatility is priced above the three-month outlook — an unusually urgent form of fear.`,'An inversion is evidence of acute stress, not proof that a market low is already in. Stabilization matters more if the ratio subsequently falls back below 1.'];
  if(r>=.95)return['Nearly flat · caution',`VIX is ${f(r,2)}× VIX3M. Near-term fear has moved close to longer-term volatility expectations, so the curve is losing its normal cushion.`,'A sustained move above 1 would mark genuine inversion. A retreat away from 1 would show that immediate stress is easing.'];
  return['Normal',`VIX is ${f(r,2)}× VIX3M. Near-term volatility remains below the three-month expectation, which is the normal shape of the curve.`,'A move toward 1 would show immediate fear building. Above 1 would signal an inverted, more acute stress regime.'];
}

function skewRead(v,p){
  if(v==null)return['Unavailable','Tail-risk pricing is unavailable.','SKEW measures how much investors are paying for protection against unusually large downside moves.'];
  if(p==null)return['History building',`SKEW is ${f(v,1)}. The value is available, but its one-year percentile is still building.`,'The percentile matters because SKEW is most useful when judged relative to its own recent distribution.'];
  if(p>=90)return['Unusually expensive protection',`SKEW is ${f(v,1)}, in the ${Math.round(p)}th percentile of the last year. Investors are paying unusually high prices for protection against a large downside shock.`,'High SKEW is not a crash forecast. It becomes more concerning when volatility, term structure and breadth deteriorate at the same time.'];
  if(p>=75)return['Tail protection elevated',`SKEW is ${f(v,1)}, in the ${Math.round(p)}th percentile of the last year. Demand for protection against an outsized downside move is above normal.`,'Watch whether this remains elevated while VIX and the term structure also deteriorate. That combination carries more information than SKEW alone.'];
  if(p<=20)return['Tail protection inexpensive',`SKEW is ${f(v,1)}, only the ${Math.round(p)}th percentile of the last year. Investors are paying relatively little for extreme downside protection.`,'Low tail-risk pricing can reflect comfort or complacency; it is not bullish by itself.'];
  return['Normal tail-risk demand',`SKEW is ${f(v,1)}, around the ${Math.round(p)}th percentile of the last year. Crash protection is not unusually expensive or unusually cheap.`,'A move into the upper quartile becomes more notable, especially if other stress measures are worsening too.'];
}

function pcRead(raw,p){
  if(raw==null)return['Unavailable','Current equity put/call positioning is unavailable.'];
  if(p==null)return['History building',`The equity put/call ratio is ${f(raw,2)}. The percentile is still building.`];
  if(p>=90)return['Unusually defensive',`Put/call is ${f(raw,2)}, in the ${Math.round(p)}th percentile of the last 60 sessions. Protection demand is genuinely extreme versus the recent market.`];
  if(p>=75)return['More defensive than usual',`Put/call is ${f(raw,2)}, in the ${Math.round(p)}th percentile of the last 60 sessions. Hedging demand is elevated, but not necessarily capitulation.`];
  if(p<=20)return['Relatively complacent',`Put/call is ${f(raw,2)}, only the ${Math.round(p)}th percentile of the last 60 sessions. Traders are using relatively little downside protection.`];
  return['Ordinary positioning',`Put/call is ${f(raw,2)}, around the ${Math.round(p)}th percentile of the last 60 sessions. Options positioning is not at a meaningful sentiment extreme.`];
}

function vixRead(v){
  if(v==null)return['Unavailable','Current implied volatility is unavailable.'];
  if(v>=30)return['High stress',`VIX is ${f(v,1)}. The market is pricing materially elevated near-term volatility.`];
  if(v>=20)return['Fear rising',`VIX is ${f(v,1)}. Investors are paying more for near-term protection than in a calm market.`];
  if(v<15)return['Very calm',`VIX is ${f(v,1)}. Near-term volatility pricing is subdued. Calm does not guarantee safety, but it does not confirm a risk-off regime.`];
  return['Normal',`VIX is ${f(v,1)}. Near-term volatility pricing remains contained.`];
}

function synthesis(d){
  const v=n(d.vix?.value),o=d.options_risk||{},r=n(o.vix_vix3m_ratio),sp=n(o.skew_percentile_252d),pp=n(d.equity_put_call?.percentile_60d);
  if(r!=null&&r>1&&v!=null&&v>=25)return['Acute options-market stress','Near-term volatility is elevated and the VIX curve is inverted. This is genuine urgency in options pricing rather than ordinary day-to-day nervousness.','Stress is real, but panic conditions can occur before the low. Look for the curve to normalize alongside improving breadth before calling stabilization.'];
  if(v!=null&&v<20&&r!=null&&r<.95&&sp!=null&&sp>=80)return['Calm tape, expensive tail insurance','Ordinary volatility remains subdued and the term structure is normal, but investors are paying unusually high prices for protection against a large downside shock.','This is a useful divergence, not a sell signal. It matters more if VIX rises, the curve flattens and breadth weakens at the same time.'];
  const warnings=Number(v!=null&&v>=20)+Number(r!=null&&r>=.95)+Number(pp!=null&&pp>=75)+Number(sp!=null&&sp>=75);
  if(warnings>=2)return['Risk pricing is deteriorating','More than one options-market measure is showing increased caution. The message is stronger because the evidence is appearing across volatility, positioning and/or tail-risk pricing.','Watch for either confirmation through further deterioration or repair through a lower VIX and a steeper, normal term structure.'];
  if(v!=null&&v<20&&r!=null&&r<.95&&(pp==null||pp<75)&&(sp==null||sp<75))return['Options markets remain calm','Near-term volatility is contained, the VIX curve is normally shaped, and positioning does not show an unusual rush for protection.','There is little options-market confirmation of a major risk-off move right now.'];
  return['Mixed options-risk signals','The options market is not sending one clean message. Some measures show caution while others remain normal.','Treat this as context rather than a standalone market call and let trend and breadth carry more weight.'];
}

function card(label,value,status,copy,learn){return `<article class="risk-card"><div class="risk-card-top"><span>${label}</span><strong>${value}</strong></div><h3>${status}</h3><p>${copy}</p><details><summary>What is this?</summary><p>${learn}</p></details></article>`}

function render(d){
  const host=document.querySelector('.shared-context');if(!host)return;
  const head=host.querySelector('.module-header>div');
  if(head){const eye=head.querySelector('.eyebrow'),h=head.querySelector('h2'),p=head.querySelector('p');if(eye)eye.textContent='STRESS & OPTIONS RISK';if(h)h.textContent='What is the options market pricing beneath the surface?';if(p)p.textContent='Fear level, urgency, positioning and tail-risk demand tell different parts of the same story.'}
  const o=d.options_risk||{},v=n(d.vix?.value),raw=n(d.equity_put_call?.value),pp=n(d.equity_put_call?.percentile_60d),r=n(o.vix_vix3m_ratio),sk=n(o.skew),sp=n(o.skew_percentile_252d);
  const [sh,sc,sw]=synthesis(d),[vs,vc]=vixRead(v),[ts,tc,tl]=termRead(r),[ps,pc]=pcRead(raw,pp),[ss,skc,skl]=skewRead(sk,sp);
  let summary=$('optionsRiskSummary');
  if(!summary){summary=document.createElement('article');summary.id='optionsRiskSummary';summary.className='options-risk-summary';host.querySelector('.context-layout')?.before(summary)}
  summary.innerHTML=`<div class="insight-label">OPTIONS-MARKET READ</div><h3>${sh}</h3><p>${sc}</p><div class="options-risk-watch"><b>WHAT MATTERS NEXT</b><span>${sw}</span></div>`;
  const grid=$('marketContext');if(!grid)return;grid.className='options-risk-grid';
  grid.innerHTML=[
    card('VIX',v==null?'—':f(v,1),vs,vc,'VIX is the market’s estimate of roughly one-month implied volatility. Think of it as the overall level of near-term fear, not a directional forecast.'),
    card('VIX TERM STRUCTURE',r==null?'—':`${f(r,2)}×`,ts,tc,`VIX looks roughly one month ahead; VIX3M looks roughly three months ahead. Their ratio tells us whether fear is concentrated immediately. ${tl}`),
    card('PUT/CALL POSITIONING',pp==null?(raw==null?'—':f(raw,2)):`${Math.round(pp)}th pct`,ps,pc,'The raw equity put/call ratio measures today’s put-versus-call activity. The percentile tells us whether that positioning is actually unusual compared with the last 60 sessions.'),
    card('TAIL-RISK DEMAND · SKEW',sp==null?(sk==null?'—':f(sk,1)):`${Math.round(sp)}th pct`,ss,skc,`SKEW measures how expensive protection is against unusually large downside moves. VIX asks “how much movement?”; SKEW asks “how expensive is crash insurance?” ${skl}`)
  ].join('');
  const viz=host.querySelector('.context-viz');if(viz){const labels=viz.querySelectorAll('.insight-label');if(labels[0])labels[0].textContent='VIX · 60 SESSIONS';if(labels[1])labels[1].style.display='none';const lead=$('leadershipSpark');if(lead)lead.style.display='none'}
  let foot=$('optionsRiskAsOf');if(!foot){foot=document.createElement('p');foot.id='optionsRiskAsOf';foot.className='options-risk-asof';host.appendChild(foot)}
  foot.textContent=o.as_of?`Options-risk data through ${o.as_of}. SKEW percentile uses up to 252 sessions.`:'';
}

async function boot(){try{const r=await fetch(`data/market_context.json?v=${Date.now()}`,{cache:'no-store'});if(!r.ok)return;render(await r.json())}catch(e){console.warn('Options risk:',e)}}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',()=>setTimeout(boot,650));else setTimeout(boot,650);
document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(boot,1300));
})();
