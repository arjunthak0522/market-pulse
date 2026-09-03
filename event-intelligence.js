(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labelize = (s) => String(s || '').replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase());
  const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0));

  const FAMILY_HELP = {
    trend:'Is the broad market trend supportive or deteriorating?',
    breadth:'How widely are stocks participating in the move?',
    volatility:'Is options-market stress becoming unusually elevated?',
    credit:'Are corporate credit markets showing stress?',
    rates:'Are Treasury yields or the curve moving unusually enough to matter?',
    leadership:'Is market leadership broad, narrow, or rotating?',
    cross_asset:'Are the dollar, oil, or gold confirming a meaningful cross-asset move?',
    sentiment:'Are traders becoming unusually fearful or complacent?',
    positioning_options:'Are options hedging and positioning proxies unusually stressed?',
    macro_calendar:'Is scheduled macro-event risk unusually concentrated?',
    liquidity:'Are financial conditions and system liquidity becoming supportive or restrictive?',
    earnings:'Is the earnings calendar unusually concentrated with market-moving reports?',
    technical_extremes:'Are SPY or QQQ near meaningful overbought or oversold extremes?'
  };

  function zone(score) {
    const s = Number(score);
    if (!Number.isFinite(s)) return {label:'Quiet', cls:'quiet', text:'Not currently prominent in the ranked scan.'};
    if (s >= 80) return {label:'Extreme', cls:'extreme', text:'Far from a normal backdrop and demanding attention.'};
    if (s >= 60) return {label:'High', cls:'high', text:'Clearly unusual versus a normal backdrop.'};
    if (s >= 40) return {label:'Elevated', cls:'elevated', text:'Meaningfully unusual and worth monitoring.'};
    if (s >= 20) return {label:'Watch', cls:'watch', text:'Somewhat unusual, but not an extreme condition.'};
    return {label:'Quiet', cls:'quiet', text:'Close enough to normal that it should stay visually quiet.'};
  }

  function driverCard(row, i) {
    const score = Number(row.importance);
    const z = zone(score);
    return `<article class="event-driver ${i===0?'event-driver-primary':''} ${z.cls}">
      <div class="event-driver-head">
        <div><span class="event-rank">0${i+1}</span><span class="event-family">${esc(row.label || labelize(row.family))}</span></div>
        <span class="event-zone ${z.cls}">${z.label}</span>
      </div>
      <div class="event-visual" aria-label="${esc(row.label || labelize(row.family))} unusualness ${score.toFixed(0)} out of 100">
        <div class="event-track"><i style="width:${clamp(score)}%"></i><b style="left:${clamp(score)}%"></b></div>
        <div class="event-track-labels"><span>Normal</span><span>More unusual</span></div>
      </div>
      <div class="event-score-copy"><strong>${score.toFixed(0)} / 100 unusualness</strong><span>${esc(z.text)}</span></div>
      <p>${esc(row.summary || 'Active market condition.')}</p>
    </article>`;
  }

  function allFamilyCard(name, rankedMap) {
    const row = rankedMap.get(name);
    const label = labelize(name);
    if (!row) {
      return `<article class="event-family-card quiet">
        <div class="event-family-card-head"><strong>${esc(label)}</strong><span class="event-zone quiet">Quiet</span></div>
        <p>${esc(FAMILY_HELP[name] || 'Market condition monitored by Event Intelligence.')}</p>
        <div class="event-family-status"><i></i><span>Available and scanned - not unusual enough to rank among the active drivers.</span></div>
      </article>`;
    }
    const score = Number(row.importance);
    const z = zone(score);
    return `<article class="event-family-card ${z.cls}">
      <div class="event-family-card-head"><strong>${esc(label)}</strong><span class="event-zone ${z.cls}">${z.label}</span></div>
      <p>${esc(FAMILY_HELP[name] || row.summary || 'Market condition monitored by Event Intelligence.')}</p>
      <div class="event-family-mini">
        <div class="event-track"><i style="width:${clamp(score)}%"></i><b style="left:${clamp(score)}%"></b></div>
        <div><strong>${score.toFixed(0)} / 100 unusualness</strong><span>${esc(z.text)}</span></div>
      </div>
    </article>`;
  }

  function render(data) {
    const cov = data?.coverage || {};
    $('eventCoverage').textContent = `${cov.available ?? 0}/${cov.total ?? 13} families scanned`;
    const rows = data?.top_events || [];
    $('eventDrivers').innerHTML = rows.map(driverCard).join('');

    const rankedMap = new Map(rows.map(r => [r.family, r]));
    const families = data?.families || [];
    $('eventAllFamilies').innerHTML = families.map(name => allFamilyCard(name, rankedMap)).join('');
    $('eventNote').textContent = 'Unusualness shows how far a condition stands out now. It does not measure expected return or signal quality.';
  }

  function wireExpand() {
    const button = $('eventExpand');
    const panel = $('eventAllFamilies');
    if (!button || !panel) return;
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!open));
      panel.hidden = open;
      button.querySelector('span').textContent = open ? 'View all 13 market drivers' : 'Hide all 13 market drivers';
      button.querySelector('b').textContent = open ? '↓' : '↑';
    });
  }

  async function load() {
    try {
      const r = await fetch(`data/event_snapshot.json?v=${Date.now()}`, {cache:'no-store'});
      if (!r.ok) throw new Error('event snapshot unavailable');
      render(await r.json());
    } catch (err) {
      $('eventCoverage').textContent = 'Event Intelligence unavailable';
      $('eventDrivers').innerHTML = '<div class="event-unavailable">The dashboard is not filling missing event inputs with placeholders.</div>';
      console.warn(err);
    }
  }

  wireExpand();
  load();
  $('refresh')?.addEventListener('click', load);
})();
