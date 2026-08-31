(()=>{
const $=id=>document.getElementById(id);
const n=v=>Number.isFinite(Number(v))?Number(v):null;
const pct=v=>n(v)==null?'—':`${n(v)>=0?'+':''}${n(v).toFixed(1)}%`;
const fmt=(v,d=1)=>n(v)==null?'—':n(v).toFixed(d);

function stateData(d){
  const b=d.breadth||{},s=d.etfs?.SPY||{},q=d.etfs?.QQQ||{},v=n(d.vix?.value),rel=n(d.relative_strength?.qqq_vs_spy_20d);
  const trend=(n(s.distance_ma200)>=0&&n(q.distance_ma200)>=0)?['Healthy','Both indexes remain above their 200-day trends.']:['Under pressure','A major index has lost long-term trend support.'];
  const breadth=n(b.above_200d)>=60?(n(b.above_50d)>=50?['Healthy','Participation is broad enough to support the trend.']:['Mixed','Long-term breadth is healthy, but intermediate participation needs improvement.']):n(b.above_200d)<40?['Weak','Long-term participation has deteriorated materially.']:['Mixed','Long-term participation is neither clearly healthy nor damaged.'];
  const stress=v==null?['Unavailable','Stress data is unavailable.']:v<20?['Low',`VIX ${v.toFixed(1)} keeps the stress backdrop contained.`]:v<30?['Rising',`VIX ${v.toFixed(1)} says investors are paying up for protection.`]:['High',`VIX ${v.toFixed(1)} signals meaningful market stress.`];
  const leadership=rel==null?['Unavailable','Relative leadership is unavailable.']:rel>1?['Growth / Tech leading','QQQ is outperforming SPY over the last 20 sessions.']:rel<-1?['Broad market leading','SPY is outperforming QQQ over the last 20 sessions.']:['Balanced','Neither growth nor the broad market has a decisive leadership edge.'];
  const rs=[n(s.rsi14),n(q.rsi14)].filter(x=>x!=null),wr=[n(s.williams_r14),n(q.williams_r14)].filter(x=>x!=null);
  const momentum=wr.some(x=>x<-80)||rs.some(x=>x<35)?['Oversold','Short-term momentum is stretched enough to raise rebound potential.']:wr.some(x=>x>-20)||rs.some(x=>x>70)?['Overbought','Momentum is strong but becoming stretched.']:rs.some(x=>x<45)?['Soft','Momentum has cooled, but is not at a capitulation extreme.']:['Neutral','Momentum is not sending an extreme signal.'];
  return{trend,breadth,stress,leadership,momentum};
}

function trendCopy(d){
  const s=d.etfs?.SPY||{},q=d.etfs?.QQQ||{},b=d.breadth||{},s50=n(s.distance_ma50),q50=n(q.distance_ma50),s200=n(s.distance_ma200),q200=n(q.distance_ma200),b50=n(b.above_50d);
  if(s200<0||q200<0)return'The primary trend is damaged. In this environment, the 200-day structure matters more than short-term oversold readings. A rebound becomes more credible only if long-term support is reclaimed and breadth improves with it.';
  if(s50<0||q50<0)return`The long-term trend is still intact, but intermediate support is being tested. With 50-day breadth at ${b50==null?'—':b50.toFixed(0)+'%'}, the key question is whether participation stabilizes as SPY and QQQ work around their 50-day trends.`;
  return'The primary structure remains intact. Both SPY and QQQ are above their 50- and 200-day trends, so ordinary weakness should still be treated as a pullback unless breadth or long-term support deteriorates.';
}

function watchCopy(d){
  const b=d.breadth||{},s=d.etfs?.SPY||{},q=d.etfs?.QQQ||{},v=n(d.vix?.value),b50=n(b.above_50d),s50=n(s.distance_ma50),q50=n(q.distance_ma50);
  if(s50<0||q50<0)return['Can intermediate support repair?','A sustained reclaim of the 50-day trend would improve the setup. If 50-day breadth deteriorates further while VIX pushes above 20, the weakness becomes harder to dismiss as a routine pullback.','REPAIR: reclaim the 50-day trend with improving breadth','RISK: weaker breadth plus rising volatility'];
  if(b50!=null&&b50<50)return['Breadth is the tell','The indexes are holding up better than participation underneath them. Improvement in 50-day breadth would validate the rally; continued deterioration would make the market increasingly fragile.','CONFIRM: 50-day breadth turns higher','RISK: indexes hold while participation keeps fading'];
  if(v!=null&&v>=20)return['Stress needs to cool','Price structure is not enough on its own while volatility is elevated. Falling VIX alongside stable breadth would improve the read; rising volatility plus weaker participation would argue that pressure is becoming more serious.','CONFIRM: VIX cools while breadth stabilizes','RISK: volatility rises as participation weakens'];
  return['Watch participation beneath the indexes','The first meaningful warning would be breadth weakening while SPY and QQQ remain near their highs, especially if volatility starts rising. Until those signals align, the primary trend deserves the benefit of the doubt.','CONFIRM: breadth stays broad or improves','RISK: breadth fades before the indexes do'];
}

function leadershipCopy(d){
  const rel=n(d.relative_strength?.qqq_vs_spy_20d),b50=n(d.breadth?.above_50d);
  if(rel==null)return'Leadership data is unavailable.';
  if(rel>1)return`Growth and technology are leading. That is constructive while breadth participates, but it becomes a concentration risk if broader participation fails to keep up${b50!=null?` — current 50-day breadth is ${b50.toFixed(0)}%`:''}.`;
  if(rel<-1)return'The broader market is leading growth and technology. That is usually a healthier form of leadership when breadth is expanding because gains are less dependent on a narrow group of mega-cap stocks.';
  return'Leadership is balanced. The market is not currently being driven by a major style divergence between growth and the broader S&P 500.';
}

function turningReads(d){
  const b=d.breadth||{},pc=d.equity_put_call||{},ad=n(b.ad_ratio),rsi=n(b.rsi_below_30),rprev=n(b.rsi_below_30_prev),tr=n(b.trin),tprev=n(b.trin_prev),pp=n(pc.percentile_60d),raw=n(pc.value);
  const stress=[ad!=null&&ad<.7,rsi!=null&&rsi>=20,tr!=null&&tr>=1.3,pp!=null&&pp>=75].filter(Boolean).length;
  const improving=Number(ad!=null&&ad>1.1)+Number(rsi!=null&&rprev!=null&&rprev>=10&&rsi<rprev-2)+Number(tr!=null&&tprev!=null&&tr<tprev&&tr<1.2);
  let stage=['NORMAL','No coordinated turning-point signal','Internals are not showing a broad washout or meaningful reversal confirmation. The primary market regime should carry more weight than short-term tactical signals.','Nothing tactical is demanding action. Watch for several internals to deteriorate together before treating weakness as a washout.'];
  if(stress>=3)stage=['CAPITULATION WATCH','Selling may be becoming exhaustive','Several internals are flashing stress at the same time. That can happen near tradable lows, but an extreme reading is not the same thing as a reversal.','The next evidence should come from buyers: improving A/D breadth and TRIN moving back toward 1 would matter more than another oversold reading.'];
  else if(stress>=2)stage=['STRESS BUILDING','The tape is moving toward an exhaustion setup','More than one internal measure is deteriorating. Conditions are getting more interesting tactically, but buyers have not supplied enough confirmation yet.','Watch whether stress broadens into capitulation or begins to normalize. Do not confuse “more oversold” with “turn confirmed.”'];
  else if(improving>=2)stage=['STABILIZATION','Early evidence that pressure is easing','Breadth and/or volume pressure are improving after weakness. This is the transition that should occur before an oversold condition is treated as a potential short-term turn.','Confirmation improves if participation keeps broadening while TRIN normalizes and elevated defensive positioning begins to ease.'];
  const adRead=ad==null?['Building','Advance/decline data is still building.','Watch whether advancers begin to outnumber decliners.']:ad<.55?['Selling is broad',`${fmt(b.advancers,0)} advancers vs ${fmt(b.decliners,0)} decliners. Sellers have control across the tape, not just in a few large stocks.`,'A/D improving above 1 would be the first sign participation is repairing.']:ad<.85?['Breadth is weak',`${fmt(b.advancers,0)} advancers vs ${fmt(b.decliners,0)} decliners. Participation is tilted negative, but not at a full capitulation extreme.`,'Watch for the ratio to recover above 1 and hold there.']:ad>1.8?['Buyers are broadening out',`${fmt(b.advancers,0)} advancers vs ${fmt(b.decliners,0)} decliners. Buying is broad enough to matter as reversal confirmation.`,'Persistence matters: one strong day is better evidence when followed by continued positive breadth.']:['Balanced',`${fmt(b.advancers,0)} advancers vs ${fmt(b.decliners,0)} decliners. Participation is not giving a strong directional signal.`,'A move decisively above or below 1 would make the breadth message more meaningful.'];
  const rsiRead=rsi==null?['Building','RSI breadth is still building.','Watch the percentage of stocks with RSI below 30.']:rsi>=30?['Broadly washed out',`${fmt(rsi)}% of S&P 500 stocks have RSI below 30. That is broad momentum exhaustion, which raises rebound potential but does not prove a low is in.`,'The better signal is fewer stocks remaining oversold while price and A/D breadth stabilize.']:rsi>=20?['Oversold breadth',`${fmt(rsi)}% of stocks are individually oversold. Selling is broad enough to watch for exhaustion.`,'Watch whether this percentage peaks and starts falling as breadth improves.']:rsi>=10?['Stress is spreading',`${fmt(rsi)}% of stocks have RSI below 30. Weakness is broadening, but it is not yet a market-wide washout.`,'A further surge would indicate broader exhaustion; a reversal lower with stronger A/D would indicate repair.']:['Not broadly oversold',`Only ${fmt(rsi)}% of S&P 500 stocks have RSI below 30. Index weakness is not producing broad momentum exhaustion.`,'A short-term low is less likely to be a classic washout unless this measure rises materially.'];
  const trRead=tr==null?['Building','Volume breadth is still building.','Watch whether declining stocks begin attracting disproportionate volume.']:tr>=2?['Capitulation-like volume',`TRIN is ${fmt(tr,2)}. Declining stocks are attracting disproportionately heavy volume — the kind of pressure that can appear near panic lows.`,'A drop back toward or below 1 while A/D improves would show that selling pressure is actually easing.']:tr>=1.3?['Selling pressure is heavy',`TRIN is ${fmt(tr,2)}. Down-volume is heavier than the issue count alone would suggest. That confirms stress, not a reversal.`,'Normalization toward 1 with better breadth would be constructive.']:tr<=.7?['Buying pressure is strong',`TRIN is ${fmt(tr,2)}. Advancing stocks are carrying disproportionately strong volume.`,'This becomes more useful as reversal confirmation when it follows a genuine washout.']:['Volume pressure is balanced',`TRIN is ${fmt(tr,2)}. Volume is not showing an extreme imbalance between advancing and declining stocks.`,'A sharp spike above 1.3 would confirm heavier selling pressure; a post-washout drop below 1 can confirm returning demand.'];
  const pcRead=raw==null?['Unavailable','Equity put/call data is unavailable.','Wait for current positioning data.']:pp==null?['History building',`Today’s equity put/call ratio is ${fmt(raw,2)}. The percentile needs more history before it can say whether that reading is unusual.`,'The raw ratio gives today’s level; the percentile will tell you how extreme it is versus recent conditions.']:pp>=90?['Fear is unusually high',`The raw ratio is ${fmt(raw,2)}, but the more useful context is that it sits in the ${Math.round(pp)}th percentile of the last 60 sessions. Defensive positioning is genuinely unusual.`,'If fear remains elevated while breadth and TRIN improve, that divergence can support a tactical bottoming case.']:pp>=75?['Hedging is elevated',`Today’s ratio is ${fmt(raw,2)} and ranks in the ${Math.round(pp)}th percentile of the last 60 sessions. Traders are buying more protection than usual, but this is not automatically capitulation.`,'Watch whether positioning reaches a true extreme or begins normalizing as internals improve.']:pp<=20?['Positioning is complacent',`Today’s ratio is ${fmt(raw,2)}, only the ${Math.round(pp)}th percentile of recent readings. The market is using relatively little put protection versus its own recent history.`,'A rapid move into a much higher percentile would signal a meaningful shift in sentiment.']:['Positioning is ordinary',`Today’s ratio is ${fmt(raw,2)}, around the ${Math.round(pp)}th percentile of recent readings. Options positioning is not at a meaningful sentiment extreme.`,'The percentile matters more than the raw ratio when deciding whether fear is truly unusual.'];
  return{stage,adRead,rsiRead,trRead,pcRead,raw,pp,rsi,tr,b};
}

function healthCell(label,role,state){return `<div class="health-cell"><div class="health-cell-head"><span>${label}</span><em class="role-badge ${role.toLowerCase()}">${role}</em></div><strong>${state[0]}</strong><p>${state[1]}</p></div>`;}
function tpCard(label,category,value,read,measure){return `<article class="tp-card"><div class="tp-card-top"><div><span>${label}</span><small>${category}</small></div><strong>${value}</strong></div><h3>${read[0]}</h3><div class="tp-explain"><div><b>WHAT IT MEASURES</b><p>${measure}</p></div><div><b>WHAT TODAY SAYS</b><p>${read[1]}</p></div><div class="tp-watch"><b>WHAT WOULD CONFIRM A TURN</b><p>${read[2]}</p></div></div></article>`;}

function addPath(){
  if($('readingPath'))return;
  const hero=document.querySelector('.premium-hero');
  hero?.insertAdjacentHTML('afterend','<nav id="readingPath" class="reading-path" aria-label="Recommended dashboard reading order"><span class="path-item"><b>1</b>Regime</span><span class="path-arrow">→</span><span class="path-item"><b>2</b>Health</span><span class="path-arrow">→</span><span class="path-item"><b>3</b>Changed</span><span class="path-arrow">→</span><span class="path-item"><b>4</b>Watch</span><span class="path-arrow">→</span><span class="path-item"><b>5</b>Turning Points</span><span class="path-arrow">→</span><span class="path-item"><b>6</b>Breadth</span><span class="path-arrow">→</span><span class="path-item"><b>7</b>Stress</span><span class="path-arrow">→</span><span class="path-item"><b>8</b>Leadership</span><span class="path-arrow">→</span><span class="path-item"><b>9</b>Index Detail</span></nav>');
}

function ensureSections(d){
  document.querySelector('.view-toggle')?.remove();
  const intel=document.querySelector('.intelligence-section'),breadth=document.querySelector('.breadth-module'),workspace=document.querySelector('.asset-workspace');
  if(!$('marketHealthGuide')){
    const s=stateData(d);
    const html=`<section id="marketHealthGuide" class="guide-section"><div class="guide-heading"><div><div class="section-step"><b>2</b> MARKET HEALTH</div><h2>Does the evidence support the regime?</h2></div><p>Start with structure. Breadth and stress confirm it. Leadership and momentum refine the read but should not overrule it.</p></div><div class="role-legend"><span><b>PRIMARY</b> Defines the regime</span><span><b>CONFIRM</b> Tests its quality</span><span><b>SUPPORTING</b> Adds context</span></div><div class="health-grid">${healthCell('TREND','PRIMARY',s.trend)}${healthCell('BREADTH','PRIMARY',s.breadth)}${healthCell('STRESS','CONFIRM',s.stress)}${healthCell('LEADERSHIP','SUPPORTING',s.leadership)}${healthCell('MOMENTUM','SUPPORTING',s.momentum)}</div><div class="trend-brief"><div class="brief-role">PRIMARY REGIME EVIDENCE</div><h3>Trend first</h3><p id="combinedTrendCopy"></p><div class="trend-table-wrap"><table class="trend-table"><thead><tr><th>Index</th><th>20D tactical</th><th>50D intermediate</th><th>200D primary</th></tr></thead><tbody><tr><th>SPY</th><td id="gSpy20">—</td><td id="gSpy50">—</td><td id="gSpy200">—</td></tr><tr><th>QQQ</th><td id="gQqq20">—</td><td id="gQqq50">—</td><td id="gQqq200">—</td></tr></tbody></table></div><div class="trend-note"><b>How to use this:</b> the 200-day trend anchors regime, the 50-day trend flags intermediate damage or repair, and the 20-day trend is tactical context only.</div></div></section>`;
    intel?.insertAdjacentHTML('beforebegin',html);
  }
  if(!$('guideWatch')){
    intel?.insertAdjacentHTML('afterend','<section id="guideWatch" class="guide-section"><div class="guide-heading"><div><div class="section-step"><b>4</b> WATCH NEXT</div><h2>What would actually change the thesis?</h2></div><p>This is the decision point. Focus on conditions that can alter the read — not every daily wiggle.</p></div><article class="guide-watch"><div class="insight-label">KEY DECISION POINT</div><h3 id="guideWatchHeadline">Loading…</h3><p id="guideWatchText"></p><div class="watch-scenarios"><span id="watchConfirm">—</span><span id="watchRisk">—</span></div></article></section>');
  }
  if(!$('turningPointInternals')){
    const html=`<section id="turningPointInternals" class="guide-section turning-points"><div class="guide-heading"><div><div class="section-step"><b>5</b> TURNING POINT INTERNALS</div><h2>Is selling exhausting — and are buyers starting to return?</h2></div><p>Short-term evidence only. Extremes can identify opportunity, but confirmation has to come from improving participation and volume.</p></div><div class="tp-principle"><strong>How experienced investors use this</strong><p>Weakness → stress → capitulation → stabilization → confirmation. “Oversold” is a condition, not a buy signal.</p></div><article class="tp-summary"><div class="tp-stage-row"><span>TURNING POINT READ</span><strong id="tpStage">NORMAL</strong></div><h3 id="tpSummaryTitle">Building the internal read…</h3><p id="tpSummaryText"></p><div class="tp-next"><b>WHAT MATTERS NEXT</b><p id="tpNextText"></p></div></article><div class="tp-sequence"><span>1 · Participation</span><b>→</b><span>2 · Exhaustion</span><b>→</b><span>3 · Volume pressure</span><b>→</b><span>4 · Sentiment extreme</span></div><div id="tpGrid" class="tp-grid"></div><div class="pc-explainer"><strong>Raw put/call vs percentile</strong><p>The raw put/call ratio tells you today’s options positioning. The percentile tells you whether that reading is actually unusual versus the last 60 sessions. For turning points, the percentile is usually the more useful context.</p></div></section>`;
    ($('guideWatch')||breadth)?.insertAdjacentHTML($('guideWatch')?'afterend':'beforebegin',html);
  }
  if(!$('guideLeadership')){
    workspace?.querySelector('.asset-switcher-wrap')?.insertAdjacentHTML('beforebegin','<section id="guideLeadership" class="guide-section"><div class="guide-heading"><div><div class="section-step"><b>8</b> LEADERSHIP</div><h2>Who is carrying the market?</h2></div><p>Supporting context: leadership tells you whether gains are broadening or becoming concentrated. It is not a second regime system.</p></div><div class="leadership-guide"><div class="leadership-value"><span>QQQ VS SPY · 20D</span><strong id="guideLeadState">—</strong><small id="guideLeadValue">—</small></div><div class="leadership-copy"><div class="brief-role">SUPPORTING EVIDENCE</div><p id="guideLeadCopy"></p></div></div></section>');
  }
  const step=(node,num,label)=>{if(node&&!node.querySelector('.section-step')){const head=node.querySelector('.module-header>div,.intelligence-heading,.asset-switcher-wrap>div');if(head)head.insertAdjacentHTML('afterbegin',`<div class="section-step"><b>${num}</b> ${label}</div>`)}};
  step(intel,3,'WHAT CHANGED');step(breadth,6,'BREADTH');step(workspace?.querySelector('.shared-context'),7,'STRESS');
  const switcher=workspace?.querySelector('.asset-switcher-wrap');if(switcher&&!switcher.querySelector('.section-step'))switcher.querySelector('div')?.insertAdjacentHTML('afterbegin','<div class="section-step"><b>9</b> INDEX DETAIL</div>');
}

function render(d){
  const s=stateData(d),cells=[...document.querySelectorAll('#marketHealthGuide .health-cell')];
  [s.trend,s.breadth,s.stress,s.leadership,s.momentum].forEach((x,i)=>{if(cells[i]){cells[i].querySelector('strong').textContent=x[0];cells[i].querySelector('p').textContent=x[1]}});
  $('combinedTrendCopy').textContent=trendCopy(d);
  const sp=d.etfs?.SPY||{},q=d.etfs?.QQQ||{};
  $('gSpy20').textContent=pct(sp.distance_ma20);$('gSpy50').textContent=pct(sp.distance_ma50);$('gSpy200').textContent=pct(sp.distance_ma200);$('gQqq20').textContent=pct(q.distance_ma20);$('gQqq50').textContent=pct(q.distance_ma50);$('gQqq200').textContent=pct(q.distance_ma200);
  const [wh,wt,wc,wr]=watchCopy(d);$('guideWatchHeadline').textContent=wh;$('guideWatchText').textContent=wt;$('watchConfirm').textContent=wc;$('watchRisk').textContent=wr;
  const rel=n(d.relative_strength?.qqq_vs_spy_20d);$('guideLeadState').textContent=s.leadership[0];$('guideLeadValue').textContent=rel==null?'Relative strength unavailable':`${rel>=0?'+':''}${rel.toFixed(2)} percentage points over 20 sessions`;$('guideLeadCopy').textContent=leadershipCopy(d);
  const t=turningReads(d);$('tpStage').textContent=t.stage[0];$('tpSummaryTitle').textContent=t.stage[1];$('tpSummaryText').textContent=t.stage[2];$('tpNextText').textContent=t.stage[3];
  $('tpGrid').innerHTML=[
    tpCard('A/D BREADTH','PARTICIPATION',n(t.b.ad_ratio)==null?'—':`${fmt(t.b.advancers,0)} / ${fmt(t.b.decliners,0)}`,t.adRead,'How broadly stocks are advancing versus declining. It tells you whether the index move is supported by the underlying tape.'),
    tpCard('RSI BREADTH','EXHAUSTION',t.rsi==null?'—':`${fmt(t.rsi)}%`,t.rsiRead,'The share of S&P 500 stocks with RSI below 30. This measures how widespread short-term momentum exhaustion has become.'),
    tpCard('S&P 500 TRIN','VOLUME PRESSURE',t.tr==null?'—':fmt(t.tr,2),t.trRead,'An Arms-style ratio using S&P 500 advancers, decliners and volume. It asks whether disproportionate volume is hitting declining or advancing stocks.'),
    tpCard('PUT/CALL PERCENTILE','SENTIMENT EXTREME',t.pp==null?'—':`${Math.round(t.pp)}th`,t.pcRead,'Where today’s equity put/call ratio ranks versus the last 60 sessions. This separates ordinary hedging from genuinely unusual fear or complacency.')
  ].join('');
}

function hideMovingAverageCards(){document.querySelectorAll('.technical-details .card').forEach(card=>{const name=(card.querySelector('.name')?.textContent||'').toLowerCase();if(name.includes('distance from 20-day')||name.includes('distance from 50-day')||name.includes('distance from 200-day'))card.classList.add('redundant-ma-card')})}

function reorder(){
  const main=document.querySelector('main'),hero=document.querySelector('.premium-hero'),path=$('readingPath'),health=$('marketHealthGuide'),intel=document.querySelector('.intelligence-section'),watch=$('guideWatch'),turn=$('turningPointInternals'),daily=$('dailyHabit'),breadth=document.querySelector('.breadth-module'),workspace=document.querySelector('.asset-workspace');
  if(!main||!hero)return;
  let anchor=hero;for(const node of [path,health,intel,watch,turn,daily,breadth,workspace])if(node){anchor.after(node);anchor=node}
  if(workspace){const shared=workspace.querySelector('.shared-context'),stress=workspace.querySelector('.stress-module'),lead=$('guideLeadership'),switcher=workspace.querySelector('.asset-switcher-wrap'),spy=$('panelSPY'),qqq=$('panelQQQ'),alerts=workspace.querySelector('.alerts-module');for(const node of [shared,stress,lead,switcher,spy,qqq,alerts])if(node)workspace.appendChild(node)}
}

async function boot(){
  try{const r=await fetch(`data/market_context.json?v=${Date.now()}`,{cache:'no-store'});if(!r.ok)return;const d=await r.json();addPath();ensureSections(d);render(d);setTimeout(()=>{hideMovingAverageCards();reorder();render(d)},250);setTimeout(()=>{hideMovingAverageCards();reorder();render(d)},1200)}catch(e){console.warn('Guide layer:',e)}
}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',()=>setTimeout(boot,150));else setTimeout(boot,150);
document.getElementById('refresh')?.addEventListener('click',()=>setTimeout(boot,900));
})();
