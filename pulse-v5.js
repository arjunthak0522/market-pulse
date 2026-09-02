(() => {
  const $ = (id) => document.getElementById(id);
  const num = (v) => (v == null || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const clamp = (v, a = 0, b = 100) => Math.max(a, Math.min(b, Number(v) || 0));
  const fmtReturn = (v) => v == null ? "—" : `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(1)}%`;

  const pctText = (p, side = "high") => {
    p = num(p);
    if (p == null) return "History building";
    const q = Math.max(1, Math.min(99, Math.round(p)));
    if (side === "low") {
      if (q <= 3) return `Severe washout · bottom ${q}%`;
      if (q <= 10) return `Washout · bottom ${q}%`;
      if (q <= 25) return "Weak versus the past year";
      if (q >= 75) return "Strong versus the past year";
      return "Typical range";
    }
    if (side === "two") {
      if (q <= 3) return `Severe washout · bottom ${q}%`;
      if (q <= 10) return `Washout · bottom ${q}%`;
      if (q >= 97) return `Severe thrust · top ${Math.max(1,100-q)}%`;
      if (q >= 90) return `Thrust · top ${Math.max(1,100-q)}%`;
      if (q <= 25) return "Weak versus the past year";
      if (q >= 75) return "Strong versus the past year";
      return "Typical range";
    }
    if (q >= 97) return `Extreme · top ${Math.max(1,100-q)}%`;
    if (q >= 90) return `Very high · top ${Math.max(1,100-q)}%`;
    if (q >= 75) return "Elevated versus the past year";
    if (q <= 25) return "Low versus the past year";
    return "Typical range";
  };

  const toneFromPct = (p, side = "high") => {
    p = num(p);
    if (p == null) return "normal";
    if (side === "low") return p <= 2.5 ? "severe" : p <= 10 ? "extreme" : p <= 25 ? "watch" : "normal";
    if (side === "two") return p <= 2.5 || p >= 97.5 ? "severe" : p <= 10 || p >= 90 ? "extreme" : p <= 25 || p >= 75 ? "watch" : "normal";
    return p >= 97.5 ? "severe" : p >= 90 ? "extreme" : p >= 75 ? "watch" : "normal";
  };

  function signalModel(data) {
    const s = data.signals || {};
    const cp = s.cpce || {}, na = s.namo || {}, ny = s.nymo || {}, tr = s.trin || {}, tq = s.trinq || {}, nl = s.newlows || {}, br = s.breadth || {}, v = s.vol || {};
    const trinPct = Math.max(num(tr.percentile_252d) ?? 50, num(tq.percentile_252d) ?? 50);
    const volPct = Math.max(num(v.term_percentile_252d) ?? 50, num(v.vvix_percentile_252d) ?? 50, num(v.skew_percentile_252d) ?? 50);
    return [
      {id:"cpce", name:"CPCE", label:"Options fear", question:"Are equity traders getting defensive?", value:num(cp.value)?.toFixed(2) ?? "—", context:`5-day avg ${num(cp.average_5d)?.toFixed(2) ?? "—"}`, pct:num(cp.percentile_252d), side:"high", tone:toneFromPct(cp.percentile_252d,"high"), state:num(cp.percentile_252d)>=90?"Fear extreme":num(cp.percentile_252d)>=75?"Elevated fear":"Normal fear", insight:"Higher readings mean traders are buying more puts relative to calls.", study:cp.study, asOf:cp.as_of},
      {id:"namo", name:"NAMO", label:"Nasdaq breadth", question:"Is Nasdaq breadth washed out or thrusting?", value:num(na.value)?.toFixed(0) ?? "—", context:"Ratio-adjusted McClellan", pct:num(na.percentile_252d), side:"two", tone:toneFromPct(na.percentile_252d,"two"), state:num(na.percentile_252d)<=10?"Nasdaq washout":num(na.percentile_252d)>=90?"Nasdaq thrust":"Normal breadth", insight:"Tracks momentum in Nasdaq advances versus declines.", study:na.study, asOf:na.as_of},
      {id:"nymo", name:"NYMO", label:"NYSE breadth", question:"Is broad-market breadth washed out or thrusting?", value:num(ny.value)?.toFixed(0) ?? "—", context:"Ratio-adjusted McClellan", pct:num(ny.percentile_252d), side:"two", tone:toneFromPct(ny.percentile_252d,"two"), state:num(ny.percentile_252d)<=2.5?"Severe NYSE washout":num(ny.percentile_252d)<=10?"NYSE washout":num(ny.percentile_252d)>=90?"NYSE thrust":"Normal breadth", insight:"Shows whether weakness or recovery is spreading across NYSE issues.", study:ny.study, asOf:ny.as_of},
      {id:"newlows", name:"New High / Low", label:"Internal damage", question:"Is structural damage spreading beneath the indexes?", value:`${nl.value ?? "—"} lows`, context:`${nl.new_highs ?? "—"} highs · ${num(nl.new_low_pct)?.toFixed(1) ?? "—"}% at new lows`, pct:num(nl.percentile_252d), side:"high", tone:toneFromPct(nl.percentile_252d,"high"), state:num(nl.percentile_252d)>=90?"Damage extreme":num(nl.percentile_252d)>=75?"Damage elevated":"Healthy internals", insight:"Expanding 52-week lows separate an ordinary pullback from deeper deterioration.", study:nl.study, asOf:nl.as_of},
      {id:"breadth", name:"Breadth Participation", label:"Participation", question:"How many S&P 500 stocks are actually participating?", value:`${num(br.above_5d)?.toFixed(0) ?? "—"}%`, context:"Above 5-day trend", pct:num(br.percentile_252d), side:"low", tone:toneFromPct(br.percentile_252d,"low"), state:num(br.percentile_252d)<=2.5?"Severe participation washout":num(br.percentile_252d)<=10?"Participation washout":num(br.percentile_252d)<=25?"Weak participation":"Normal participation", insight:"Shows whether index moves are broadly supported or carried by a narrow group.", study:br.study, asOf:br.as_of, ladder:[['5D',br.above_5d],['20D',br.above_20d],['50D',br.above_50d],['200D',br.above_200d]]},
      {id:"trin", name:"TRIN / TRINQ", label:"Capitulation", question:"Is selling becoming indiscriminate?", value:`${num(tr.value)?.toFixed(2) ?? "—"} / ${num(tq.value)?.toFixed(2) ?? "—"}`, context:"NYSE / Nasdaq Arms Index", pct:trinPct, side:"high", tone:toneFromPct(trinPct,"high"), state:trinPct>=90?"Capitulation":"No capitulation", insight:"High readings flag unusually intense selling after adjusting for breadth and volume.", study:tr.study, secondaryStudy:tq.study, asOf:tr.as_of},
      {id:"vol", name:"Volatility Regime", label:"Volatility", question:"Is options-market stress becoming urgent?", value:"3-part read", context:"Term structure · VVIX · SKEW", pct:volPct, side:"high", tone:toneFromPct(volPct,"high"), state:num(v.term_ratio)>=1?"Term structure inverted":num(v.skew_percentile_252d)>=90?"Tail risk elevated":"Volatility contained", insight:"Separates urgent fear, volatility hedging and crash-protection demand.", asOf:v.as_of, vol:v}
    ];
  }

  function statePanel(data) {
    const m = data.market_state || {};
    const d = m.dimensions || {};
    const dim = (key,title,sub) => {
      const score = clamp(d[key]?.score, 0, 100);
      const level = score >= 75 ? "hot" : score >= 45 ? "warm" : "cool";
      return `<div class="pressure-dim ${level}"><div class="pressure-line"><span>${title}</span><strong>${esc(d[key]?.label || "—")}</strong></div><div class="pressure-track"><i style="width:${Math.max(4,score)}%"></i><b style="left:${Math.max(4,Math.min(96,score))}%"></b></div><small>${sub}</small></div>`;
    };
    $("stateName").textContent = m.name || "Reading market state…";
    $("stateSummary").textContent = m.summary || "Synthesizing market internals.";
    $("pressureMap").innerHTML = [
      dim("fear","FEAR","Options positioning"),
      dim("internals","INTERNALS","Breadth participation"),
      dim("capitulation","CAPITULATION","Selling pressure")
    ].join("");
  }

  function changedPanel(data) {
    const rows = (data.what_changed || []).slice(0,3);
    $("changedList").innerHTML = rows.map((x,i) => `<article class="change-row ${i===0?"primary-change":""}"><span class="change-index">0${i+1}</span><div><strong>${esc(x.headline)}</strong><p>${esc(x.detail)}</p></div></article>`).join("");
  }

  function studyTeaser(s) {
    const h = s.study?.horizons?.["21"] || s.study?.horizons?.["60"];
    if (!h) return "";
    return `<div class="precedent-teaser"><div><span>21-DAY HISTORICAL PRECEDENT</span><strong>${fmtReturn(h.median)} median</strong></div><div class="precedent-hit"><strong>${Math.round(h.positive_rate)}%</strong><small>positive · n=${h.n}</small></div></div>`;
  }

  function breadthVisual(s) {
    if (!s.ladder) return "";
    return `<div class="breadth-ladder">${s.ladder.map(([k,v])=>`<div><span>${k}</span><div class="mini-track"><i style="width:${Math.max(2,Math.min(100,num(v)||0))}%"></i></div><strong>${num(v)?.toFixed(0) ?? "—"}%</strong></div>`).join("")}</div>`;
  }

  function volVisual(v) {
    const item = (name,question,value,pct,state) => `<div class="vol-cell"><div class="vol-cell-top"><span>${name}</span><strong>${value}</strong></div><div class="vol-copy"><p>${question}</p><div class="vol-state">${state}</div><small>${pctText(pct,"high")}</small></div></div>`;
    const termPct=num(v.term_percentile_252d), vvixPct=num(v.vvix_percentile_252d), skewPct=num(v.skew_percentile_252d);
    return `<div class="vol-cells">${item("TERM STRUCTURE","Is fear becoming urgent?",num(v.term_ratio)?.toFixed(2)??"—",termPct,num(v.term_ratio)>=1?"Inverted":"Normal curve")}${item("VVIX","Are traders hedging volatility itself?",num(v.vvix)?.toFixed(1)??"—",vvixPct,vvixPct>=90?"Fear-of-fear extreme":vvixPct>=75?"Elevated":"Contained")}${item("SKEW","Are traders paying for crash protection?",num(v.skew)?.toFixed(0)??"—",skewPct,skewPct>=90?"Tail risk extreme":skewPct>=75?"Tail risk elevated":"Contained")}</div>`;
  }

  function signalCard(s, rank) {
    const special = s.id === "vol" ? volVisual(s.vol) : s.id === "breadth" ? breadthVisual(s) : `<div class="signal-reading"><strong>${esc(s.value)}</strong><span>${esc(s.context)}</span></div>`;
    const teaser = s.id !== "vol" && s.tone !== "normal" ? studyTeaser(s) : "";
    const priority = ["severe","extreme"].includes(s.tone) ? `<span class="priority-tag">STANDS OUT</span>` : "";
    return `<article class="signal-module ${s.id} ${s.tone}" data-rank="${rank}">
      <div class="module-topline">${priority}<span class="module-label">${esc(s.label)}</span></div>
      <div class="module-head"><h3>${esc(s.name)}</h3><span class="module-state ${s.tone}">${esc(s.state)}</span></div>
      <div class="module-question">${esc(s.question)}</div>
      ${special}
      <p class="module-insight">${esc(s.insight)}</p>
      <div class="rarity"><span>${esc(pctText(s.pct,s.side))}</span><i><b style="left:${Math.max(2,Math.min(98,num(s.pct)||50))}%"></b></i></div>
      ${teaser}
      <div class="module-actions"><button class="history-action" data-history="${s.id}">View historical study</button><button class="watch-action" data-watch="${s.id}">Watch</button></div>
    </article>`;
  }

  function signalBoard(signals) {
    const weight = {severe:0,extreme:1,watch:2,normal:3};
    const ordered = [...signals].sort((a,b) => weight[a.tone]-weight[b.tone]);
    window.__signals = signals;
    $("signalBoard").innerHTML = ordered.map((s,i)=>signalCard(s,i)).join("");
    document.querySelectorAll("[data-history]").forEach((b) => b.addEventListener("click", () => openHistory(b.dataset.history)));
    document.querySelectorAll("[data-watch]").forEach((b) => b.addEventListener("click", () => toggleWatch(b.dataset.watch)));
    hydrateWatchButtons();
  }

  function studyBlock(title, study) {
    if (!study) return "";
    const cells = [5,10,21,60].map((h) => {
      const x = study.horizons?.[String(h)];
      if (!x) return "";
      return `<div class="study-cell"><span>${h} DAYS</span><strong>${fmtReturn(x.median)}</strong><small>${Math.round(x.positive_rate)}% positive</small><small>Avg ${fmtReturn(x.average)} · n=${x.n}</small><small>Typical drawdown first ${fmtReturn(x.median_max_drawdown)}</small><small>Typical upside ${fmtReturn(x.median_max_favorable)}</small></div>`;
    }).join("");
    return `<section class="study-block"><div class="study-kicker">${esc(title)}</div><p>${esc(study.rule || "Comparable historical condition")}</p><div class="study-grid">${cells}</div><div class="episode-note">${esc(study.episode_method || "")}</div></section>`;
  }

  function openHistory(id) {
    const s = window.__signals?.find((x) => x.id === id);
    if (!s) return;
    let blocks = "";
    if (id === "vol") blocks = studyBlock("VIX TERM STRUCTURE",s.vol.term_study) + studyBlock("VVIX",s.vol.vvix_study) + studyBlock("SKEW",s.vol.skew_study);
    else blocks = studyBlock(s.name,s.study) + (s.secondaryStudy ? studyBlock("TRINQ",s.secondaryStudy) : "");
    $("historyContent").innerHTML = `<div class="drawer-kicker">HISTORICAL PRECEDENT</div><h2>${esc(s.name)}</h2><p class="drawer-intro">What happened to SPY after independent historical episodes that looked like this?</p>${blocks}`;
    $("historyDrawer").hidden = false;
    document.body.classList.add("drawer-open");
  }

  function watched() {
    try { return JSON.parse(localStorage.getItem("marketPulseWatches") || "[]"); } catch { return []; }
  }

  function toggleWatch(id) {
    const set = new Set(watched());
    if (set.has(id)) set.delete(id); else set.add(id);
    localStorage.setItem("marketPulseWatches", JSON.stringify([...set]));
    hydrateWatchButtons();
    if (set.has(id) && "Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(()=>{});
  }

  function hydrateWatchButtons() {
    const set = new Set(watched());
    document.querySelectorAll("[data-watch]").forEach((b) => {
      const active = set.has(b.dataset.watch);
      b.textContent = active ? "Watching ✓" : "Watch";
      b.classList.toggle("active",active);
    });
  }

  function notifyWatched(signals) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const set = new Set(watched());
    signals.filter((s) => set.has(s.id) && ["extreme","severe"].includes(s.tone)).forEach((s) => {
      const key = `mp-notified-${s.id}-${s.asOf}`;
      if (localStorage.getItem(key)) return;
      new Notification(`Market Pulse: ${s.state}`, {body:`${s.name}: ${pctText(s.pct,s.side).toLowerCase()}.`});
      localStorage.setItem(key,"1");
    });
  }

  async function load() {
    try {
      const r = await fetch(`data/signal_data.json?v=${Date.now()}`, {cache:"no-store"});
      if (!r.ok) throw new Error("signal dataset unavailable");
      const data = await r.json();
      const signals = signalModel(data);
      $("asOf").textContent = `Latest completed read · ${data.market_date || "—"}`;
      statePanel(data);
      changedPanel(data);
      signalBoard(signals);
      notifyWatched(signals);
    } catch (err) {
      $("stateName").textContent = "Signal quality check failed";
      $("stateSummary").textContent = "Market Pulse will not render an incomplete market state.";
      $("signalBoard").innerHTML = "";
      console.warn(err);
    }
  }

  $("historyClose").addEventListener("click", () => { $("historyDrawer").hidden = true; document.body.classList.remove("drawer-open"); });
  $("historyDrawer").addEventListener("click", (e) => { if (e.target === $("historyDrawer")) $("historyClose").click(); });
  $("refresh").addEventListener("click", load);
  load();
})();
