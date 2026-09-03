(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labelize = (s) => String(s || '').replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase());

  function render(data) {
    const cov = data?.coverage || {};
    $('eventCoverage').textContent = `${cov.available ?? 0}/${cov.total ?? 13} families live`;
    const rows = data?.top_events || [];
    $('eventDrivers').innerHTML = rows.map((row, i) => `
      <article class="event-driver ${i===0?'event-driver-primary':''}">
        <div class="event-rank">0${i+1}</div>
        <div class="event-copy">
          <div class="event-topline"><span>${esc(row.label || labelize(row.family))}</span><strong>${Number(row.importance || 0).toFixed(1)}</strong></div>
          <p>${esc(row.summary || 'Active market condition.')}</p>
        </div>
      </article>`).join('');
    $('eventFamilyLine').textContent = (data?.families || []).map(labelize).join(' · ');
    $('eventNote').textContent = data?.note || '';
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

  load();
  $('refresh')?.addEventListener('click', load);
})();
