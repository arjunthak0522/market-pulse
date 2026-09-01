(()=>{
const $=id=>document.getElementById(id);
const n=v=>v==null||v===''?null:(Number.isFinite(Number(v))?Number(v):null);
const f=(v,d=1)=>n(v)==null?'—':n(v).toFixed(d);
function tone(v,good,bad){return v==null?'neutral':v>=good?'constructive':v<bad?'stress':'caution'}
function ensure(){
  const intel=document.querySelector('.intelligence-section');
  if(!intel)return;
  if(!$('marketHealthGuide'))intel.insertAdjacentHTML('afterend',`<section id="marketHealthGuide" class="guide-section"><div class="guide-heading"><div><div class="eyebrow">MARKET HEALTH</div><h2>What is actually holding the market together?</h2></div><p>Trend, participation and risk pricing carry the most weight. Tactical indicators confirm or challenge that structure.</p></div><div id="healthGrid" class="health-grid"></div><div id="guideWatch" class="guide-watch"><span>WHAT CHANGES THE VIEW</span><h3 id="guideWatchHeadline">Waiting for confirmed data</h3><p id="guideWatchText"></p></div></section>`);
  const health=$('marketHealthGuide');
  if(!$('turningPointInternals'))health.insertAdjacentHTML('afterend',`<section id="turningPointInternals" class="guide-section"><div class="guide-heading"><div><div class="eyebrow">TURNING-POINT INTELLIGENCE</div><h2>Are we approaching an important market turn?</h2></div><p>A turn needs more than one oversold indicator. Market Pulse looks for stress, exhaustion and evidence that buyers are actually returning.</p></div><div class="tp-summary"><span>CURRENT READ</span><h3 id="tpStage">—</h3><p id="tpText"></p><div class="turn-flow"><i>Pressure</i><b>→</b><i>Exhaustion</i><b>→</b><i>Stabilization</i><b>→</b><i>Confirmation</i></div></div><div id="tpGrid" class="tp-grid"></div></section>`);
}
function cell(label,value,copy,cls){return `<article class="health-cell ${cls}"><div class="health-cell-head"><span>${label}</span><em>${label==='PRIMARY TREND'?'PRIMARY':'CONFIRM'}</em></div><strong>${value}</strong><p>${copy}</p></article>`}
function tp(label,tech,value,status,copy,watch){return `<article class="tp-card"><div class="tp-card-top"><div><span>${label}</span><small>${tech}</small></div><strong>${value}</strong></div><h3>${status}</h3><p class="tp-now">${copy}</p><div class="tp-watch"><b>WHAT CONFIRMS</b><p>${watch}</p></div></article>`}
function render(d){
  ensure();
  const b=d.breadth||{},s=d.etfs?.SPY||{},q=d.etfs?.QQQ||{},o=d.options_risk||{};
  const b5=n(b.above_5d),b50=n(b.above_50d),b200=n(b.above_200d),s50=n(s.distance_ma50),q50=n(q.distance_ma50),s200=n(s.distance_ma200),q200=n(q.distance_ma200),v=n(d.vix?.value),pc=n(d.equity_put_call?.value),ad=n(b.ad_ratio),oversold=n(b.rsi_below_30),trin=n(b.trin),cycle=String(d.breadth_cycle?.state||'Unavailable'),cyclePct=n(d.breadth_cycle?.percentile_63d);
  const trendHealthy=b200!=null&&b200>=60&&s200!=null&&q200!=null&&s200>=0&&q200>=0;
  const trendValue=trendHealthy?'Intact':(s200!=null&&q200!=null&&(s200<0||q200<0))?'Damaged':'Mixed';
  const trendCls=trendValue==='Intact'?'constructive':trendValue==='Damaged'?'stress':'caution';
  const partValue=b50==null?'Unavailable':b50>=60?'Broad':b50>=40?'Mixed':'Weak';
  const partCls=tone(b50,60,40);
  const riskValue=v==null?'Unavailable':v<20?'Contained':v<30?'Elevated':'Stressed';
  const riskCls=v==null?'neutral':v<20?'constructive':v<30?'caution':'stress';
  const momVals=[n(s.rsi14),n(q.rsi14)].filter(x=>x!=null),wrVals=[n(s.williams_r14),n(q.williams_r14)].filter(x=>x!=null);
  const stretched=wrVals.some(x=>x<=-80)||momVals.some(x=>x<35),hot=wrVals.some(x=>x>=-20)||momVals.some(x=>x>70);
  const momValue=stretched?'Oversold':hot?'Extended':'Neutral';
  const cycleValue=/recovery|stabil/i.test(cycle)?'Improving':/washout|approach/i.test(cycle)||cyclePct!=null&&cyclePct<=10?'Building':'Low';
  $('healthGrid').innerHTML=[
    cell('PRIMARY TREND',trendValue,trendHealthy?`Long-term participation is ${f(b200,0)}% and both SPY and QQQ remain above long-term support.`:'Price and long-term participation are not fully aligned.',trendCls),
    cell('PARTICIPATION',partValue,`One-week participation ${f(b5,0)}% · intermediate ${f(b50,0)}% · long-term ${f(b200,0)}%.`,partCls),
    cell('RISK PRICING',riskValue,`VIX ${f(v,1)} · equity put/call ${f(pc,2)}.`,riskCls),
    cell('MOMENTUM',momValue,stretched?'Short-term momentum is stretched enough to watch for exhaustion.':'Momentum is not at a major downside exhaustion extreme.',stretched?'caution':'neutral'),
    cell('TURN PRESSURE',cycleValue,`${cycle}${cyclePct==null?'':` · ${f(cyclePct,0)}th percentile`}.`,cycleValue==='Improving'?'constructive':cycleValue==='Building'?'caution':'neutral')
  ].join('');
  let watchHead='Participation beneath the indexes',watchText='The first important warning would be participation deteriorating while SPY or QQQ lose intermediate support.';
  if(s50!=null&&q50!=null&&(s50<0||q50<0)){watchHead='Reclaim intermediate support';watchText='A sustained reclaim of the 50-day structure plus improving participation would repair the setup. A loss of long-term support would make the weakness structural.'}
  else if(b5!=null&&b5<30){watchHead='Watch whether selling exhausts';watchText=`One-week participation is ${f(b5,0)}%. A rebound toward 40-50% would be the first useful sign that selling pressure is easing.`}
  $('guideWatchHeadline').textContent=watchHead;$('guideWatchText').textContent=watchText;
  const stress=[b5!=null&&b5<20,ad!=null&&ad<.55,oversold!=null&&oversold>=20,trin!=null&&trin>=1.3,v!=null&&v>=20].filter(Boolean).length;
  const improving=[ad!=null&&ad>1,cycle.toLowerCase().includes('recovery'),cycle.toLowerCase().includes('stabil')].filter(Boolean).length;
  let stage='NO CONFIRMED TURN',copy='Pressure is not synchronized enough to call a high-quality turning-point setup.';
  if(stress>=3){stage='CAPITULATION WATCH';copy='Several stress measures are extreme together. Reversal potential is rising, but buyers still need to confirm.'}
  else if(/washout|approach/i.test(cycle)||cyclePct!=null&&cyclePct<=10){stage='PRESSURE BUILDING';copy='Breadth momentum is near an extreme. The next improvement in participation matters more than another weak price day.'}
  if(improving>=2){stage='TURN DEVELOPING';copy='Breadth is beginning to repair. Price and intermediate participation still need to confirm the turn.'}
  $('tpStage').textContent=stage;$('tpText').textContent=copy;
  $('tpGrid').innerHTML=[
    tp('ONE-WEEK PARTICIPATION','5-day breadth',b5==null?'—':`${f(b5,0)}%`,b5!=null&&b5<20?'Washout zone':b5!=null&&b5<35?'Broad weakness':'Not extreme',b5==null?'Participation unavailable.':`${f(b5,0)}% of S&P 500 stocks are above their one-week trend.`, 'A rebound toward 40-50% shows buyers broadening out.'),
    tp('STOCKS RISING VS FALLING','Advance/decline ratio',f(ad,2),ad!=null&&ad<.55?'Broad selling':ad!=null&&ad>1.2?'Buyers broadening':'Mixed',`${f(b.advancers,0)} advancers vs ${f(b.decliners,0)} decliners.`, 'An A/D ratio above 1 that persists is constructive.'),
    tp('HOW MANY STOCKS ARE OVERSOLD?','RSI breadth',oversold==null?'—':`${f(oversold,0)}%`,oversold!=null&&oversold>=20?'Broad exhaustion':oversold!=null&&oversold>=10?'Stress spreading':'Not broad', 'This is the share of S&P 500 stocks with RSI below 30.', 'The oversold share peaking while participation improves is stronger than the level alone.'),
    tp('SELLING-VOLUME PRESSURE','TRIN',f(trin,2),trin!=null&&trin>=1.3?'Heavy selling volume':trin!=null&&trin<=.7?'Buying pressure':'Balanced','TRIN compares advancing/declining issues with their volume.', 'Normalization toward 1 alongside improving participation helps confirm stabilization.')
  ].join('');
  window.dispatchEvent(new CustomEvent('market-guide-ready'));
}
async function boot(){try{const r=await fetch('data/market_context.json',{cache:'no-store'});if(!r.ok)return;render(await r.json())}catch(e){console.warn('Market guide:',e)}}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
document.getElementById('refresh')?.addEventListener('click',boot);
})();
