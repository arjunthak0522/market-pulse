(()=>{
async function prioritize(){
  try{
    const sec=document.getElementById('historicalForwardReturns'),select=document.getElementById('forwardStudySelect');
    if(!sec||!select)return;
    const r=await fetch('data/event_studies.json',{cache:'no-store'});if(!r.ok)return;
    const d=await r.json();
    const studies=d.studies||[],events=[...(d.current_events||[])].sort((a,b)=>(b.priority||0)-(a.priority||0));
    let idle=document.getElementById('historicalIdleNote');
    if(!events.length){
      sec.classList.add('no-active-study');
      if(!idle){idle=document.createElement('div');idle.id='historicalIdleNote';idle.className='historical-idle-note';idle.innerHTML='<strong>No unusual historical setup is active today.</strong> Historical studies stay in the background until a current signal is strong enough to matter.';sec.querySelector('.forward-head')?.after(idle)}
      return;
    }
    sec.classList.remove('no-active-study');idle?.remove();
    const byId=new Map(studies.map(s=>[s.study_id,s]));
    const preferred=events.find(e=>byId.get(e.study_id)?.category==='Breadth cycle')||events.find(e=>byId.get(e.study_id)?.category==='One-week participation')||events[0];
    if(!preferred||select.value===preferred.study_id)return;
    const option=[...select.options].find(o=>o.value===preferred.study_id);if(!option)return;
    select.value=preferred.study_id;select.dispatchEvent(new Event('change',{bubbles:true}));
  }catch(e){console.warn('Historical study priority:',e)}
}
if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',prioritize,{once:true});else prioritize();
document.getElementById('refresh')?.addEventListener('click',prioritize);
})();
