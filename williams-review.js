(()=>{
const n=v=>{if(v==null||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null};
const f=(v,d=1)=>n(v)==null?'—':n(v).toFixed(d);
function williamsState(v){v=n(v);if(v==null)return['Unavailable','neutral'];if(v<=-80)return['Fast exhaustion / oversold','bad'];if(v>=-20)return['Fast exhaustion / overbought','warn'];return['Normal range position','neutral']}
const prior=window.renderIndex;
if(typeof prior!=='function')return;
window.renderIndex=function(sym,d){
  prior(sym,d);
  const x=d?.etfs?.[sym]||{};
  const box=document.getElementById(sym.toLowerCase());
  if(!box||typeof window.card!=='function')return;
  const v=n(x.williams_r14),[s,t]=williamsState(v);
  const node=window.card('wr','Williams %R',f(v,1),'Fast exhaustion check - where price sits inside its recent 14-day range.',s,t);
  const cards=[...box.children];
  const rsiIndex=cards.findIndex(el=>(el.textContent||'').includes('RSI'));
  if(rsiIndex>=0&&cards[rsiIndex].nextSibling)box.insertBefore(node,cards[rsiIndex].nextSibling);else box.appendChild(node);
};
})();
