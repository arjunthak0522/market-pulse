const $=id=>document.getElementById(id);
const n=v=>Number.isFinite(Number(v))?Number(v):null;
const f=(v,d=2)=>n(v)==null?'—':n(v).toFixed(d);
const pct=(v,d=1)=>n(v)==null?'—':n(v).toFixed(d)+'%';

const I={
 b5:['% above 5-day MA','BREADTH · VERY SHORT TERM','How many S&P 500 stocks are above their own 5-day average.','Very low means selling is hitting almost everything, not just a few stocks.',['70%+|Broad strength','50-70%|Healthy','30-50%|Weakening','15-30%|Broadly oversold','Below 15%|Significant washout'],'https://www.barchart.com/stocks/quotes/$S5FD'],
 b20:['% above 20-day MA','BREADTH · SHORT TERM','How many stocks are above roughly one month of trend.','This shows whether short-term weakness is becoming widespread.',['70%+|Broad strength','50-70%|Healthy','30-50%|Weakening','Below 25%|Oversold'],'https://www.barchart.com/stocks/quotes/$S5TW'],
 b50:['% above 50-day MA','BREADTH · INTERMEDIATE','How much of the market is participating in the intermediate trend.','SPY can look fine while this falls, revealing weakness under the surface.',['60%+|Healthy','40-60%|Mixed','30-40%|Weak','Below 30%|Broad damage'],'https://www.barchart.com/stocks/quotes/$S5FI'],
 b200:['% above 200-day MA','BREADTH · LONG TERM','How many S&P 500 stocks remain in long-term uptrends.','This is the big-picture health check.',['60%+|Healthy','40-60%|Mixed','Below 40%|Serious damage'],'https://www.barchart.com/stocks/quotes/$S5TH'],
 rsi:['RSI (14)','MOMENTUM','Is momentum unusually stretched up or down?','Below 30 is oversold. Above 70 is overbought. Use it as confirmation, not prediction.',['Above 70|Overbought','45-55|Neutral','Below 30|Oversold'],'https://www.investopedia.com/terms/r/rsi.asp'],
 wr:['Williams %R (14)','FAST MOMENTUM','Where is price sitting inside its recent 14-day range?','Near -100 means price is near the bottom of its recent range. Near 0 means near the top.',['Above -20|Overbought','-20 to -80|Normal','Below -80|Oversold'],'https://www.investopedia.com/terms/w/williamsr.asp'],
 bb:['Bollinger %B','PRICE STRETCH','Where is price relative to its normal volatility envelope?','0 is the lower Bollinger Band, 0.5 the middle, and 1 the upper band.',['Above 1|Above upper band','0.2-0.8|Normal','Below 0|Below lower band'],'https://www.bollingerbands.com/'],
 macd:['MACD','TREND MOMENTUM','Is medium-term momentum improving or deteriorating?','The relationship between MACD and its signal line matters more than the raw number.',['MACD > signal|Improving','Near signal|Indecisive','MACD < signal|Deteriorating'],'https://www.investopedia.com/terms/m/macd.asp'],
 adx:['ADX (14)','TREND STRENGTH','How strong is the current trend, regardless of direction?','Above about 25 means the trend has substance rather than just noise.',['Above 25|Meaningful trend','20-25|Developing','Below 20|Noisy'],'https://www.investopedia.com/terms/a/adx.asp'],
 ma20:['Distance from 20-day MA','SHORT-TERM TREND','How far is price from its short-term trend?','Positive means above trend. Large distances can also mean price is stretched.',['Above 0%|Above trend','Near 0%|Testing trend','Below 0%|Below trend'],'https://www.fidelity.com/viewpoints/active-investor/moving-averages'],
 ma50:['Distance from 50-day MA','INTERMEDIATE TREND','Is the index above or below its intermediate trend?','The 50-day average is one of the most watched intermediate support gauges.',['Above 0%|Trend intact','Near 0%|Testing support','Below 0%|Deteriorating'],'https://www.fidelity.com/viewpoints/active-investor/moving-averages'],
 ma200:['Distance from 200-day MA','LONG-TERM TREND','Is the index still in a long-term uptrend?','A break below matters much more when long-term breadth is also deteriorating.',['Above 0%|Trend intact','Near 0%|Major test','Below 0%|Warning'],'https://www.fidelity.com/viewpoints/active-investor/moving-averages'],
 vix:['VIX','FEAR','How much near-term volatility is the options market pricing?','Low VIX means calm, not necessarily safety. A spike plus collapsing breadth is more meaningful.',['Below 15|Very calm','15-20|Normal','20-30|Fear rising','30-40|High stress','40+|Panic'],'https://www.cboe.com/tradable-products/vix/'],
 pc:['Equity Put/Call Ratio','POSITIONING','Are traders buying more stock-option puts for protection or calls for upside?','Higher means more protection and caution. Lower means more call activity and optimism.',['Below ~0.60|Optimistic / complacent','0.60-0.80|Normal-ish','0.80-1.00|Caution rising','Above 1.00|Heavy hedging','Above ~1.20|Potential extreme'],'https://www.cboe.com/markets/us/options/market-statistics/daily/']
};

function st(k,v){
 v=n(v); if(v==null)return['Unavailable','neutral'];
 if(k==='b5')return v<15?['Significant washout','bad']:v<30?['Broadly oversold','warn']:v<50?['Short-term weakness','warn']:['Healthy participation','good'];
 if(k==='b20')return v<25?['Oversold','bad']:v<50?['Weakening','warn']:['Healthy','good'];
 if(k==='b50')return v<30?['Broad damage','bad']:v<40?['Weak','warn']:v<60?['Mixed','neutral']:['Healthy','good'];
 if(k==='b200')return v<40?['Long-term damage','bad']:v<60?['Mixed','warn']:['Long-term healthy','good'];
 if(k==='rsi')return v<30?['Oversold','bad']:v>70?['Overbought','warn']:v<45?['Weakening','warn']:v>60?['Strong','good']:['Neutral','neutral'];
 if(k==='wr')return v<-80?['Oversold','bad']:v>-20?['Overbought','warn']:['Normal','neutral'];
 if(k==='bb')return v<0?['Below lower band','bad']:v>1?['Above upper band','warn']:v<.2?['Near lower band','warn']:v>.8?['Near upper band','warn']:['Normal','neutral'];
 if(k==='adx')return v>=25?['Meaningful trend','good']:v>=20?['Trend developing','neutral']:['Weak trend','neutral'];
 if(k==='vix')return v<15?['Very calm','good']:v<20?['Normal','good']:v<30?['Fear rising','warn']:v<40?['High stress','bad']:['Panic','bad'];
 if(k==='pc')return v<.6?['Optimistic / complacent','warn']:v<.8?['Normal-ish','good']:v<1?['Caution rising','warn']:['Heavy hedging / fear','bad'];
 if(k.startsWith('ma'))return v>1?['Above trend','good']:v>=0?['Testing trend','neutral']:['Below trend','warn'];
 return['Neutral','neutral'];
}

function detail(k,val,s,t){
 const i=I[k]; $('dk').textContent=i[1]; $('dt').textContent=i[0]; $('dv').textContent=val; $('ds').textContent=s; $('ds').className='status-pill '+t; $('dm').textContent=i[3];
 $('th').innerHTML=i[4].map(x=>{const[a,b]=x.split('|');return `<div class="threshold"><b>${a}</b><span>${b}</span></div>`}).join(''); $('src').href=i[5]; $('detail').showModal();
}
function card(k,name,val,copy,s,t){
 const b=document.createElement('button'); b.type='button'; b.className='card';
 b.innerHTML=`<div class="card-top"><div class="name">${name}</div><span class="card-arrow" aria-hidden="true">›</span></div><div class="value">${val}</div><div class="status-pill ${t}">${s}</div><p>${copy}</p>`;
 b.onclick=()=>detail(k,val,s,t); return b;
}

function indexSummary(sym,x,d){
 const r=n(x.rsi14), w=n(x.williams_r14), m20=n(x.distance_ma20), m50=n(x.distance_ma50), m200=n(x.distance_ma200), adx=n(x.adx14), v=n(d.vix?.value), pc=n(d.equity_put_call?.value);
 const parts=[];
 if(w!=null&&w<-80) parts.push('short-term momentum is oversold'); else if(r!=null&&r<45) parts.push('momentum is soft'); else if(r!=null&&r>60) parts.push('momentum remains firm'); else parts.push('momentum is neutral');
 if(m50!=null&&m200!=null){
   if(m50>=0&&m200>=0) parts.push('the intermediate and primary trends remain intact');
   else if(m200>=0) parts.push('the long-term trend is intact but shorter-term support is under pressure');
   else parts.push('the primary trend has deteriorated');
 }
 if(adx!=null&&adx>=25) parts.push('trend strength is meaningful rather than just noise');
 let context='';
 if(v!=null&&pc!=null){
   if(v<20&&pc<.8) context='Options markets are still relatively calm, so this reads more like a positioning reset than broad capitulation.';
   else if(v>=30||pc>=1) context='Fear and hedging are elevated, which makes the weakness more significant.';
   else context='Fear is rising, but not yet at panic levels.';
 }
 const lead=sym==='QQQ'?'Nasdaq 100':'S&P 500';
 return `${lead}: ${parts.join(', ')}. ${context}`;
}

function renderIndex(sym,d){
 const x=d.etfs?.[sym]||{}, box=$(sym.toLowerCase()), pr=$(sym.toLowerCase()+'Price'); const change=n(x.change_pct);
 pr.textContent=n(x.price)==null?'--':`$${f(x.price,2)}  ${change>=0?'+':''}${pct(change,2)}`; box.innerHTML='';
 let s,t; [s,t]=st('rsi',x.rsi14); box.appendChild(card('rsi','RSI (14)',f(x.rsi14,1),'Is momentum stretched?',s,t));
 [s,t]=st('wr',x.williams_r14); box.appendChild(card('wr','Williams %R',f(x.williams_r14,1),'Fast short-term overbought/oversold gauge.',s,t));
 [s,t]=st('bb',x.bollinger_pct_b); box.appendChild(card('bb','Bollinger %B',f(x.bollinger_pct_b,2),'Where price sits inside its volatility bands.',s,t));
 const m=n(x.macd),ms=n(x.macd_signal),q=m==null?['Unavailable','neutral']:ms==null?['Positive momentum','good']:m>=ms?['Momentum improving','good']:['Momentum weakening','warn'];
 box.appendChild(card('macd','MACD',f(m,2),'Medium-term momentum confirmation.',q[0],q[1]));
 [s,t]=st('adx',x.adx14); box.appendChild(card('adx','ADX (14)',f(x.adx14,1),'How strong the current trend is.',s,t));
 for(const h of [20,50,200]){const k='ma'+h,v=x['distance_ma'+h]; [s,t]=st(k,v); box.appendChild(card(k,`Distance from ${h}-day MA`,pct(v,2),h===20?'Short-term trend.':h===50?'Intermediate trend.':'Long-term trend.',s,t));}
 $(sym.toLowerCase()+'Summary').textContent=indexSummary(sym,x,d);
}

function render(d){
 const b=d.breadth||{}; const B=[['b5','5-day',b.above_5d],['b20','20-day',b.above_20d],['b50','50-day',b.above_50d],['b200','200-day',b.above_200d]];
 $('ladder').innerHTML=B.map(([k,label,v])=>{const[s,t]=st(k,v);return `<div class="cell ${t}-cell"><div class="eyebrow">${label}</div><div class="v">${pct(v,1)}</div><div class="cell-status">${s}</div></div>`}).join('');
 $('breadth').innerHTML=''; for(const[k,label,v] of B){const[s,t]=st(k,v);$('breadth').appendChild(card(k,'% above '+label+' MA',pct(v,1),'How much of the S&P 500 is above this trend?',s,t));}
 renderIndex('SPY',d); renderIndex('QQQ',d);
 const ctx=$('marketContext'); ctx.innerHTML=''; let s,t;
 [s,t]=st('vix',d.vix?.value); ctx.appendChild(card('vix','VIX',f(d.vix?.value,2),'How much fear the options market is pricing.',s,t));
 [s,t]=st('pc',d.equity_put_call?.value); ctx.appendChild(card('pc','Equity Put/Call',f(d.equity_put_call?.value,2),'Whether traders are buying protection or chasing upside.',s,t));
 const b5=n(b.above_5d),b50=n(b.above_50d),b200=n(b.above_200d),v=n(d.vix?.value),sh=b5==null?'Unknown':b5<15?'Washed out':b5<30?'Oversold':b5<50?'Weak':'Healthy',im=b50==null?'Unknown':b50<30?'Damaged':b50<40?'Weak':b50<60?'Mixed':'Healthy',lg=b200==null?'Unknown':b200<40?'Damaged':b200<60?'Mixed':'Healthy',fe=v==null?'Unknown':v<15?'Very low':v<20?'Normal':v<30?'Rising':v<40?'High':'Extreme';
 let h='Mixed market conditions'; if(b5!=null&&b5<30&&b200>=60)h='Short-term oversold. Long-term trend healthy.'; else if(b5!=null&&b5<15)h='Broad short-term washout developing.'; else if(b50>=60&&b200>=60)h='Broadly healthy market structure.'; else if(b50!=null&&b50<40&&b200<60)h='Breadth deterioration needs attention.';
 $('condition').textContent=h; $('summary').textContent=`Short term is ${sh.toLowerCase()}, intermediate breadth is ${im.toLowerCase()}, long-term breadth is ${lg.toLowerCase()}, and fear is ${fe.toLowerCase()}.`;
 $('chips').innerHTML=[`5-day breadth · ${sh}`,`50-day breadth · ${im}`,`200-day breadth · ${lg}`,`VIX · ${fe}`,`Put/call · ${f(d.equity_put_call?.value,2)}`].map(x=>`<span class="chip">${x}</span>`).join('');
 const dt=d.generated_at?new Date(d.generated_at):null; $('fresh').textContent='Latest saved data · '+(dt&&!isNaN(dt)?dt.toLocaleString():d.market_date||'unknown');
}

function selectIndex(sym){
 const spy=sym==='SPY'; $('panelSPY').hidden=!spy; $('panelQQQ').hidden=spy; $('tabSPY').classList.toggle('active',spy); $('tabQQQ').classList.toggle('active',!spy); $('tabSPY').setAttribute('aria-selected',String(spy)); $('tabQQQ').setAttribute('aria-selected',String(!spy));
}

async function load(){
 const btn=$('refresh'); btn.disabled=true; btn.setAttribute('aria-busy','true');
 try{const r=await fetch('data/market_context.json?v='+Date.now(),{cache:'no-store'}); if(!r.ok)throw Error('Could not load data'); render(await r.json());}
 catch(e){$('fresh').textContent='Data load error · '+e.message;}
 finally{btn.disabled=false;btn.removeAttribute('aria-busy');}
}

$('refresh').onclick=load; $('close').onclick=()=>$('detail').close(); $('detail').addEventListener('click',e=>{if(e.target===$('detail'))$('detail').close()}); $('tabSPY').onclick=()=>selectIndex('SPY'); $('tabQQQ').onclick=()=>selectIndex('QQQ');
if('serviceWorker'in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{}); load();