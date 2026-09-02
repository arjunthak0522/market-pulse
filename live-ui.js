(() => {
  const ET = "America/New_York";
  const POLL_MS = 5 * 60_000;
  let timer = null;

  const installStyles = () => {
    if (document.getElementById("liveDataStyles")) return;
    const style = document.createElement("style");
    style.id = "liveDataStyles";
    style.textContent = `
      .freshness-tag{display:inline-flex;align-items:center;margin-left:8px;padding:3px 7px;border:1px solid rgba(255,255,255,.14);border-radius:999px;font-size:9px;font-weight:800;letter-spacing:.09em;color:rgba(235,241,250,.72);vertical-align:middle}
      .freshness-tag.intraday{color:#dff9e8;border-color:rgba(116,227,156,.28);background:rgba(116,227,156,.08)}
      .freshness-tag.session_close{color:#e8eef8;background:rgba(255,255,255,.045)}
      .freshness-tag.eod{color:rgba(235,241,250,.62);background:rgba(255,255,255,.025)}
      .intraday-event{display:flex;gap:10px;align-items:flex-start;margin-top:13px;padding:11px 12px;border-radius:12px;background:rgba(255,151,94,.08);border:1px solid rgba(255,151,94,.22);font-size:12px;line-height:1.42;color:rgba(244,247,252,.84)}
      .intraday-event strong{flex:0 0 auto;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#ffd4bd}
      @media(max-width:640px){.freshness-tag{font-size:8px;padding:3px 6px}.intraday-event{display:block}.intraday-event strong{display:block;margin-bottom:4px}}
    `;
    document.head.appendChild(style);
  };

  const fmtET = (iso) => {
    if (!iso) return "";
    try {
      return new Intl.DateTimeFormat("en-US", {
        timeZone: ET,
        hour: "numeric",
        minute: "2-digit",
        month: "short",
        day: "numeric"
      }).format(new Date(iso));
    } catch (_) {
      return "";
    }
  };

  const liveEndpoint = () => document.querySelector('meta[name="market-pulse-live-endpoint"]')?.content?.trim() || "";

  const getStaticData = async () => {
    const r = await fetch(`data/signal_data.json?live=${Date.now()}`, {cache: "no-store"});
    if (!r.ok) throw new Error("current-session dataset unavailable");
    return r.json();
  };

  const getLiveQuotes = async () => {
    const endpoint = liveEndpoint();
    if (!endpoint) return null;
    const r = await fetch(`${endpoint}${endpoint.includes("?") ? "&" : "?"}t=${Date.now()}`, {cache: "no-store"});
    if (!r.ok) throw new Error(`live relay unavailable (${r.status})`);
    return r.json();
  };

  const mergeLive = (data, live) => {
    if (!live?.quotes) return data;
    const d = structuredClone(data);
    const q = live.quotes;
    const sig = d.signals || {};
    const marketOpen = Boolean(d.data_status?.market_open);
    const quoteFreshness = marketOpen ? "intraday" : "session_close";
    const apply = (id, symbol) => {
      if (!sig[id] || !q[symbol]) return;
      sig[id].value = q[symbol].value;
      sig[id].as_of_timestamp = q[symbol].provider_timestamp || sig[id].as_of_timestamp || live.generated_at;
      sig[id].freshness = quoteFreshness;
    };

    apply("trin", "$TRIN");
    apply("trinq", "$TRINQ");

    if (sig.trin && q["$TRIN"]) {
      sig.trin.session_open = q["$TRIN"].open;
      sig.trin.session_high = q["$TRIN"].high;
      sig.trin.session_low = q["$TRIN"].low;
      const threshold = Number(sig.trin.study?.threshold);
      sig.trin.intraday_extreme_occurred = Number.isFinite(threshold) && Number(q["$TRIN"].high) >= threshold;
    }
    if (sig.trinq && q["$TRINQ"]) {
      sig.trinq.session_open = q["$TRINQ"].open;
      sig.trinq.session_high = q["$TRINQ"].high;
      sig.trinq.session_low = q["$TRINQ"].low;
    }

    if (sig.newlows) {
      if (q["$NYLOW"]) sig.newlows.value = Math.round(q["$NYLOW"].value);
      if (q["$NYHGH"]) sig.newlows.new_highs = Math.round(q["$NYHGH"].value);
      if (q["$NALOW"]) sig.newlows.nasdaq_new_lows = Math.round(q["$NALOW"].value);
      if (q["$NAHGH"]) sig.newlows.nasdaq_new_highs = Math.round(q["$NAHGH"].value);
      sig.newlows.as_of_timestamp = q["$NYLOW"]?.provider_timestamp || sig.newlows.as_of_timestamp || live.generated_at;
      sig.newlows.freshness = quoteFreshness;
    }

    if (sig.breadth) {
      if (q["$SPXA20R"]) sig.breadth.above_20d = q["$SPXA20R"].value;
      if (q["$SPXA50R"]) sig.breadth.above_50d = q["$SPXA50R"].value;
      if (q["$SPXA200R"]) sig.breadth.above_200d = q["$SPXA200R"].value;
      sig.breadth.as_of_timestamp = q["$SPXA20R"]?.provider_timestamp || sig.breadth.as_of_timestamp || live.generated_at;
      sig.breadth.freshness = quoteFreshness;
    }

    if (sig.vol) {
      const vix = Number(q["$VIX"]?.value);
      const vix3m = Number(q["$VIX3M"]?.value);
      const vvix = Number(q["$VVIX"]?.value);
      if (Number.isFinite(vix)) sig.vol.vix = vix;
      if (Number.isFinite(vix3m)) sig.vol.vix3m = vix3m;
      if (Number.isFinite(vix) && Number.isFinite(vix3m) && vix3m !== 0) sig.vol.term_ratio = vix / vix3m;
      if (Number.isFinite(vvix)) sig.vol.vvix = vvix;
      sig.vol.as_of_timestamp = q["$VIX"]?.provider_timestamp || sig.vol.as_of_timestamp || live.generated_at;
      sig.vol.freshness = quoteFreshness;
    }

    const priorStatus = d.data_status || {};
    d.data_status = {
      ...priorStatus,
      ...(marketOpen ? {generated_at: live.generated_at} : {}),
      live_relay: true,
      live_relay_generated_at: live.generated_at
    };
    return d;
  };

  const setTopFreshness = (data, usingLive) => {
    const el = document.getElementById("asOf");
    if (!el) return;
    const status = data.data_status || {};
    const generated = fmtET(status.generated_at || data.generated_at);
    const session = status.session_date || data.market_date || "";
    if (status.market_open && usingLive) {
      el.textContent = `CURRENT MARKET READ · Updated ${generated || "now"} ET · ~5 min cadence`;
    } else if (status.market_open) {
      el.textContent = `INTRADAY MARKET READ · Refreshed ${generated || "now"} ET`;
    } else {
      el.textContent = `SESSION CLOSE · ${session}${generated ? ` · Refreshed ${generated} ET` : ""}`;
    }
  };

  const patchTrin = (data) => {
    const tr = data.signals?.trin || {};
    const tq = data.signals?.trinq || {};
    const card = document.querySelector(".signal-module.trin");
    if (!card) return;

    const reading = card.querySelector(".signal-reading strong");
    const context = card.querySelector(".signal-reading span");
    const state = card.querySelector(".module-state");
    const high = Number(tr.session_high);
    const current = Number(tr.value);
    const tqCurrent = Number(tq.value);
    const tqHigh = Number(tq.session_high);

    if (reading && Number.isFinite(current) && Number.isFinite(tqCurrent)) reading.textContent = `${current.toFixed(2)} / ${tqCurrent.toFixed(2)}`;
    if (context && Number.isFinite(high)) {
      const pieces = ["NYSE / Nasdaq Arms Index", `TRIN high ${high.toFixed(2)}`];
      if (Number.isFinite(tqHigh)) pieces.push(`TRINQ high ${tqHigh.toFixed(2)}`);
      context.textContent = pieces.join(" · ");
    }

    if (tr.intraday_extreme_occurred && state) {
      state.textContent = "Capitulation hit intraday";
      state.classList.remove("normal", "watch");
      state.classList.add("extreme");
      card.classList.remove("normal", "watch");
      card.classList.add("extreme");
      let note = card.querySelector(".intraday-event");
      if (!note) {
        const insight = card.querySelector(".module-insight");
        note = document.createElement("div");
        note.className = "intraday-event";
        if (insight) insight.insertAdjacentElement("afterend", note);
      }
      if (note) note.innerHTML = `<strong>Intraday event</strong><span>TRIN reached ${high.toFixed(2)} today${Number.isFinite(current) ? ` and is now ${current.toFixed(2)}` : ""}.</span>`;
    }
  };

  const patchNewLows = (data) => {
    const nl = data.signals?.newlows;
    const card = document.querySelector(".signal-module.newlows");
    if (!nl || !card) return;
    const reading = card.querySelector(".signal-reading strong");
    const context = card.querySelector(".signal-reading span");
    if (reading) reading.textContent = `${nl.value ?? "—"} lows`;
    if (context) context.textContent = `${nl.new_highs ?? "—"} NYSE highs · ${nl.nasdaq_new_lows ?? "—"} Nasdaq lows`;
  };

  const patchBreadth = (data) => {
    const br = data.signals?.breadth;
    const rows = document.querySelectorAll(".signal-module.breadth .breadth-ladder > div");
    if (!br || rows.length < 4) return;
    const values = [br.above_5d, br.above_20d, br.above_50d, br.above_200d];
    rows.forEach((row, i) => {
      const v = Number(values[i]);
      if (!Number.isFinite(v)) return;
      const strong = row.querySelector("strong");
      const bar = row.querySelector("i");
      if (strong) strong.textContent = `${v.toFixed(0)}%`;
      if (bar) bar.style.width = `${Math.max(2, Math.min(100, v))}%`;
    });
  };

  const patchVol = (data) => {
    const vol = data.signals?.vol;
    const cells = document.querySelectorAll(".signal-module.vol .vol-cell");
    if (!vol || cells.length < 3) return;
    const values = [Number(vol.term_ratio), Number(vol.vvix), Number(vol.skew)];
    const digits = [2, 1, 0];
    cells.forEach((cell, i) => {
      if (!Number.isFinite(values[i])) return;
      const strong = cell.querySelector(".vol-cell-top strong");
      if (strong) strong.textContent = values[i].toFixed(digits[i]);
    });
  };

  const patchSignalFreshness = (data) => {
    const ids = ["cpce", "namo", "nymo", "trin", "newlows", "breadth", "vol"];
    ids.forEach((id) => {
      const row = id === "trin" ? data.signals?.trin : data.signals?.[id];
      const card = document.querySelector(`.signal-module.${id}`);
      if (!row || !card) return;
      const topline = card.querySelector(".module-topline");
      if (!topline) return;
      let tag = topline.querySelector(".freshness-tag");
      if (!tag) {
        tag = document.createElement("span");
        tag.className = "freshness-tag";
        topline.appendChild(tag);
      }
      tag.className = `freshness-tag ${row.freshness || ""}`;
      tag.textContent = row.freshness === "intraday" ? "~5 MIN" : row.freshness === "session_close" ? "SESSION CLOSE" : "EOD";
    });
  };

  const patch = async () => {
    try {
      installStyles();
      const staticData = await getStaticData();
      let live = null;
      try { live = await getLiveQuotes(); } catch (err) { console.warn("Market Pulse live relay", err); }
      const data = mergeLive(staticData, live);
      setTopFreshness(data, Boolean(live?.quotes));
      patchTrin(data);
      patchNewLows(data);
      patchBreadth(data);
      patchVol(data);
      patchSignalFreshness(data);
    } catch (err) {
      console.warn("Market Pulse freshness overlay", err);
    }
  };

  const refresh = () => patch();

  window.addEventListener("DOMContentLoaded", () => {
    installStyles();
    window.setTimeout(patch, 900);
    timer = window.setInterval(refresh, POLL_MS);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) refresh();
    });
  });

  window.addEventListener("beforeunload", () => timer && clearInterval(timer));
})();
