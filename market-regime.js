(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0));

  function bucket(name, row) {
    const score = row?.score;
    if (score == null) {
      return `<div class="regime-bucket"><span>${esc(name)}</span><strong>Unavailable</strong><small>No reliable input</small></div>`;
    }
    return `<div class="regime-bucket"><span>${esc(name)}</span><strong>${esc(row.label || "—")}</strong><small>${Number(score).toFixed(0)}/100</small><div class="regime-bucket-meter"><i style="width:${clamp(score)}%"></i></div></div>`;
  }

  function render(regime) {
    if (!regime || !regime.name) {
      $("regimeName").textContent = "Regime unavailable";
      $("regimeInterpretation").textContent = "Market Pulse does not have enough validated completed-session data to classify the environment.";
      $("regimeConfidence").textContent = "LOW CONFIDENCE";
      $("regimeConfidence").className = "regime-confidence low";
      $("regimeBuckets").innerHTML = `<div class="regime-unavailable">No regime is shown rather than filling missing inputs with placeholders.</div>`;
      return;
    }

    $("regimeName").textContent = regime.name;
    $("regimeInterpretation").textContent = regime.interpretation || "";
    const confidence = String(regime.confidence || "LOW").toUpperCase();
    $("regimeConfidence").textContent = `${confidence} CONFIDENCE`;
    $("regimeConfidence").className = `regime-confidence ${confidence.toLowerCase()}`;

    const meta = [];
    if (regime.transition) meta.push(`<span><strong>Transition:</strong> ${esc(regime.transition)}</span>`);
    if (regime.start_date) meta.push(`<span><strong>Since:</strong> ${esc(regime.start_date)}</span>`);
    if (regime.sessions_in_regime != null) meta.push(`<span><strong>Duration:</strong> ${esc(regime.sessions_in_regime)} session${Number(regime.sessions_in_regime) === 1 ? "" : "s"}</span>`);
    if (regime.coverage) meta.push(`<span><strong>Coverage:</strong> ${esc(regime.coverage.core_available)}/${esc(regime.coverage.core_total)} core buckets</span>`);
    $("regimeMeta").innerHTML = meta.join("");

    const b = regime.buckets || {};
    $("regimeBuckets").innerHTML = [bucket("Trend", b.trend), bucket("Breadth", b.breadth), bucket("Volatility", b.volatility)].join("");
  }

  async function fetchJson(url) {
    const r = await fetch(`${url}?v=${Date.now()}`, {cache:"no-store"});
    if (!r.ok) throw new Error(`${url} unavailable`);
    return r.json();
  }

  async function loadRegime() {
    try {
      const data = await fetchJson("data/signal_data.json");
      if (data.market_regime?.name) {
        render(data.market_regime);
        return;
      }
      const snapshot = await fetchJson("data/regime_snapshot.json");
      render(snapshot.market_regime);
    } catch (err) {
      try {
        const snapshot = await fetchJson("data/regime_snapshot.json");
        render(snapshot.market_regime);
      } catch (snapshotErr) {
        render(null);
        console.warn(err, snapshotErr);
      }
    }
  }

  loadRegime();
  $("refresh")?.addEventListener("click", loadRegime);
})();
