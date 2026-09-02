(() => {
  const ET = "America/New_York";
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

  const getData = async () => {
    const r = await fetch(`data/signal_data.json?live=${Date.now()}`, {cache: "no-store"});
    if (!r.ok) throw new Error("current-session dataset unavailable");
    return r.json();
  };

  const setTopFreshness = (data) => {
    const el = document.getElementById("asOf");
    if (!el) return;
    const status = data.data_status || {};
    const generated = fmtET(status.generated_at || data.generated_at);
    const session = status.session_date || data.market_date || "";
    if (status.market_open) {
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

    const context = card.querySelector(".signal-reading span");
    const state = card.querySelector(".module-state");
    const high = Number(tr.session_high);
    const current = Number(tr.value);
    const tqHigh = Number(tq.session_high);

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
      if (!card.querySelector(".intraday-event")) {
        const insight = card.querySelector(".module-insight");
        const note = document.createElement("div");
        note.className = "intraday-event";
        note.innerHTML = `<strong>Intraday event</strong><span>TRIN reached ${high.toFixed(2)} today${Number.isFinite(current) ? ` before easing to ${current.toFixed(2)}` : ""}.</span>`;
        if (insight) insight.insertAdjacentElement("afterend", note);
      }

      const summary = document.getElementById("stateSummary");
      if (summary && !summary.dataset.intradayTrin) {
        summary.dataset.intradayTrin = "1";
        summary.textContent = `${summary.textContent.replace(/\s+$/, "")} TRIN reached capitulation levels intraday before selling pressure eased.`;
      }
    }
  };

  const patchSignalFreshness = (data) => {
    const ids = ["cpce", "namo", "nymo", "trin", "newlows", "breadth", "vol"];
    ids.forEach((id) => {
      const row = id === "trin" ? data.signals?.trin : data.signals?.[id];
      const card = document.querySelector(`.signal-module.${id}`);
      if (!row || !card) return;
      const topline = card.querySelector(".module-topline");
      if (!topline || topline.querySelector(".freshness-tag")) return;
      const tag = document.createElement("span");
      tag.className = `freshness-tag ${row.freshness || ""}`;
      const label = row.freshness === "intraday" ? "INTRADAY" : row.freshness === "session_close" ? "SESSION CLOSE" : "EOD";
      tag.textContent = label;
      topline.appendChild(tag);
    });
  };

  const patch = async () => {
    try {
      installStyles();
      const data = await getData();
      setTopFreshness(data);
      patchTrin(data);
      patchSignalFreshness(data);
    } catch (err) {
      console.warn("Market Pulse freshness overlay", err);
    }
  };

  const refresh = async () => {
    const button = document.getElementById("refresh");
    if (button) button.click();
    window.setTimeout(patch, 700);
  };

  window.addEventListener("DOMContentLoaded", () => {
    installStyles();
    window.setTimeout(patch, 900);
    timer = window.setInterval(refresh, 60_000);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) refresh();
    });
  });

  window.addEventListener("beforeunload", () => timer && clearInterval(timer));
})();
