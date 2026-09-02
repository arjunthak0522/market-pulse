(() => {
  const $ = (id) => document.getElementById(id);
  const num = (v) => (v == null || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const pctText = (p, side = "high") => {
    p = num(p);
    if (p == null) return "History building";
    const q = Math.max(1, Math.min(99, Math.round(p)));
    if (side === "low") return q <= 10 ? `Bottom ${q}% of the past year` : `Stronger than ${q}% of the past year`;
    if (side === "two") {
      if (q <= 10) return `Bottom ${q}% of the past year`;
      if (q >= 90) return `Top ${Math.max(1, 100 - q)}% of the past year`;
    }
    return q >= 90 ? `Top ${Math.max(1, 100 - q)}% of the past year` : `Higher than ${q}% of the past year`;
  };
  const toneFromPct = (p, side = "high") => {
    p = num(p);
    if (p == null) return "normal";
    if (side === "low") return p <= 2.5 ? "severe" : p <= 10 ? "extreme" : p <= 25 ? "watch" : "normal";
    if (side === "two") return p <= 2.5 || p >= 97.5 ? "severe" : p <= 10 || p >= 90 ? "extreme" : p <= 25 || p >= 75 ? "watch" : "normal";
    return p >= 97.5 ? "severe" : p >= 90 ? "extreme" : p >= 75 ? "watch" : "normal";
  };
  const fmtReturn = (v) => v == null ? "—" : `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(1)}%`;

  function signalModel(data) {
    const s = data.signals || {};
    const cp = s.cpce || {}, na = s.namo || {}, ny = s.nymo || {}, tr = s.trin || {}, tq = s.trinq || {}, nl = s.newlows || {}, br = s.breadth || {}, v = s.vol || {};
    return [
      {id:"cpce", family:"fear", name:"CPCE", label:"Options fear", question:"Are equity traders getting defensive?", value:num(cp.value)?.toFixed(2) ?? "—", context:`5-day avg ${num(cp.average_5d)?.toFixed(2) ?? "—"}`, pct:num(cp.percentile_252d), side:"high", tone:toneFromPct(cp.percentile_252d,"high"), state:num(cp.percentile_252d)>=90?"Fear extreme":num(cp.percentile_252d)>=75?"Elevated fear":"Normal fear", insight:"Higher readings mean equity traders are buying more puts relative to calls.", study:cp.study, asOf:cp.as_of, source:cp.source},
      {id:"namo", family:"breadth", name:"NAMO", label:"Nasdaq breadth", question:"Is Nasdaq breadth washed out or thrusting?", value:num(na.value)?.toFixed(0) ?? "—", context:"Ratio-adjusted McClellan", pct:num(na.percentile_252d), side:"two", tone:toneFromPct(na.percentile_252d,"two"), state:num(na.percentile_252d)<=10?"Nasdaq washout":num(na.percentile_252d)>=90?"Nasdaq thrust":"Normal breadth", insight:"Measures momentum in Nasdaq advances versus declines.", study:na.study, asOf:na.as_of, source:na.source},
      {id:"nymo", family:"breadth", name:"NYMO", label:"NYSE breadth", question:"Is broad-market breadth washed out or thrusting?", value:num(ny.value)?.toFixed(0) ?? "—", context:"Ratio-adjusted McClellan", pct:num(ny.percentile_252d), side:"two", tone:toneFromPct(ny.percentile_252d,"two"), state:num(ny.percentile_252d)<=2.5?"Severe NYSE washout":num(ny.percentile_252d)<=10?"NYSE washout":num(ny.percentile_252d)>=90?"NYSE thrust":"Normal breadth", insight:"Confirms whether internal weakness or recovery is spreading across NYSE issues.", study:ny.study, asOf:ny.as_of, source:ny.source},
      {id:"newlows", family:"breadth", name:"New High / Low", label:"Internal damage", question:"Is structural damage spreading beneath the indexes?", value:`${nl.value ?? "—"} lows`, context:`${nl.new_highs ?? "—"} highs · ${num(nl.new_low_pct)?.toFixed(1) ?? "—"}% at new lows`, pct:num(nl.percentile_252d), side:"high", tone:toneFromPct(nl.percentile_252d,"high"), state:num(nl.percentile_252d)>=90?"Damage extreme":num(nl.percentile_252d)>=75?"Damage elevated":"Healthy internals", insight:"Expanding 52-week lows help distinguish an ordinary pullback from deeper deterioration.", study:nl.study, asOf:nl.as_of, source:nl.source},
      {id:"breadth", family:"breadth", name:"Breadth Participation", label:"Participation", question:"How many S&P 500 stocks are actually participating?", value:`${num(br.above_5d)?.toFixed(0) ?? "—"}%`, context:"Above 5-day trend", pct:num(br.percentile_252d), side:"low", tone:toneFromPct(br.percentile_252d,"low"), state:num(br.percentile_252d)<=2.5?"Severe participation washout":num(br.percentile_252d)<=10?"Participation washout":num(br.percentile_252d)<=25?"Weak participation":"Normal participation", insight:"Shows whether index moves are broadly supported or being carried by a narrow group.", study:br.study, asOf:br.as_of, source:br.source, ladder:[['5D',br.above_5d],['20D',br.above_20d],['50D',br.above_50d],['200D',br.above_200d]]},
      {id:"trin", family:"pressure", name:"TRIN / TRINQ", label:"Capitulation", question:"Is selling becoming indiscriminate?", value:`${num(tr.value)?.toFixed(2) ?? "—"} / ${num(tq.value)?.toFixed(2) ?? "—"}`, context:"NYSE / Nasdaq Arms Index", pct:Math.max(num(tr.percentile_252d) ?? 50,num(tq.percentile_252d) ?? 50), side:"high", tone:toneFromPct(Math.max(num(tr.percentile_252d) ?? 50,num(tq.percentile_252d) ?? 50),"high"), state:Math.max(num(tr.percentile_252d) ?? 50,num(tq.percentile_252d) ?? 50)>=90?"Capitulation":"No capitulation", insight:"High readings flag unusually intense selling pressure after adjusting for breadth and volume.", study:tr.study, secondaryStudy:tq.study, asOf:tr.as_of, source:`${tr.source || ""} · ${tq.source || ""}`},
      {id:"vol", family:"fear", name:"Volatility Regime", label:"Volatility", question:"Is options-market stress becoming urgent?", value:"3-part read", context:"Term structure · VVIX · SKEW", pct:Math.max(num(v.term_percentile_252d) ?? 50,num(v.vvix_percentile_252d) ?? 50,num(v.skew_percentile_252d) ?? 50), side:"high", tone:toneFromPct(Math.max(num(v.term_percentile_252d) ?? 50,num(v.vvix_percentile_252d) ?? 50,num(v.skew_percentile_252d) ?? 50),"high"), state:num(v.term_ratio)>=1?"Term structure inverted":num(v.skew_percentile_252d)>=90?"Tail risk elevated":"Volatility contained", insight:"Separates urgent near-term fear, volatility hedging, and crash-protection demand.", asOf:v.as_of, source:v.source, vol:v}
    ];
  }

  function statePanel(data) {
    const m = data.market_state || {};
    const d = m.dimensions || {};
    const setup = m.setup || {};
    const dim = (key,title,sub) => `<div class="pressure-dim"><div class="pressure-title">${title}</div><div class="pressure-value">${esc(d[key]?.label || "—")}</div><div class="pressure-sub">${sub}</div><div class="pressure-track"><span style="width:${Math.min(100,Math.max(3,num(d[key]?.score)||0))}%"></span></div></div>`;
    $("stateName").textContent = m.name || "Reading market state…";
    $("stateSummary").textContent = m.summary || "Synthesizing market internals.";
    $("pressureMap").innerHTML = [
      dim("fear","FEAR","Options and volatility positioning"),
      dim("internals","INTERNALS","Breadth and participation"),
      dim("capitulation","CAPITULATION","Selling pressure and volume")
    ].join("");
    const stage = (key,title) => `<div class="stage ${setup[key]?.confirmed?"confirmed":"pending"}"><span class="stage-dot"></span><div><strong>${title}</strong><small>${esc(setup[key]?.copy || "")}</small></div></div>`;
    $("setupPath").innerHTML = stage("extreme","1. EXTREME") + stage("confirmation","2. CONFIRMATION") + stage("trigger","3. TRIGGER");
  }

  function changedPanel(data) {
    const rows = data.what_changed || [];
    $("changedList").innerHTML = rows.map((x) => `<div class="change-row"><span class="change-pulse"></span><div><strong>${esc(x.headline)}</strong><p>${esc(x.detail)}</p></div></div>`).join("");
  }

  function studyTeaser(s) {
    const h = s.study?.horizons?.["21"] || s.study?.horizons?.["60"];
    if (!h) return "";
    return `<div class="precedent-teaser"><span>HISTORICAL PRECEDENT</span><div><strong>${fmtReturn(h.median)} median</strong><small>${Math.round(h.positive_rate)}% positive · n=${h.n}</small></div></div>`;
  }

  function breadthVisual(s) {
    if (!s.ladder) return "";
    return `<div class="breadth-ladder">${s.ladder.map(([k,v])=>`<div><span>${k}</span><div class="mini-track"><i style="width:${Math.max(2,Math.min(100,num(v)||0))}%"></i></div><strong>${num(v)?.toFixed(0) ?? "—"}%</strong></div>`).join("")}</div>`;
  }

  function volVisual(v) {
    const item = (name,question,value,pct,state) => `<div class="vol-cell"><div class="vol-cell-top"><span>${name}</span><strong>${value}</strong></div><p>${question}</p><div class="vol-state">${state}</div><small>${pctText(pct,"high")}</small></div>`;
    const termPct=num(v.term_percentile_252d), vvixPct=num(v.vvix_percentile_252d), skewPct=num(v.skew_percentile_252d);
    return `<div class="vol-cells">${item("TERM STRUCTURE","Is fear becoming urgent?",num(v.term_ratio)?.toFixed(2)??"—",termPct,num(v.term_ratio)>=1?"INVERTED":"Normal curve")}${item("VVIX","Are traders hedging volatility itself?",num(v.vvix)?.toFixed(1)??"—",vvixPct,vvixPct>=90?"Fear-of-fear extreme":vvixPct>=75?"Elevated":"Contained")}${item("SKEW","Are traders paying for crash protection?",num(v.skew)?.toFixed(0)??"—",skewPct,skewPct>=90?"Tail risk extreme":skewPct>=75?"Tail risk elevated":"Contained")}</div>`;
  }

  function signalCard(s) {
    const special = s.id === "vol" ? volVisual(s.vol) : s.id === "breadth" ? breadthVisual(s) : `<div class="signal-reading"><strong>${esc(s.value)}</strong><span>${esc(s.context)}</span></div>`;
    return `<article class="signal-module ${s.id} ${s.tone}">
      <div class="module-head"><div><span class="module-label">${esc(s.label)}</span><h3>${esc(s.name)}</h3></div><span class="module-state ${s.tone}">${esc(s.state)}</span></div>
      <div class="module-question">${esc(s.question)}</div>
      ${special}
      <p class="module-insight">${esc(s.insight)}</p>
      <div class="rarity"><span>${esc(pctText(s.pct,s.side))}</span><i><b style="left:${Math.max(2,Math.min(98,num(s.pct)||50))}%"></b></i></div>
      ${s.id!=="vol" ? studyTeaser(s) : ""}
      <div class="module-actions"><button class="history-action" data-history="${s.id}">Historical study</button><button class="watch-action" data-watch="${s.id}">Watch signal</button></div>
    </article>`;
  }

  function signalBoard(signals) {
    $("signalBoard").innerHTML = signals.map(signalCard).join("");
    document.querySelectorAll("[data-history]").forEach((b) => b.addEventListener("click", () => openHistory(b.dataset.history)));
    document.querySelectorAll("[data-watch]").forEach((b) => b.addEventListener("click", () => toggleWatch(b.dataset.watch, b)));
    hydrateWatchButtons();
  }

  function studyBlock(title, study) {
    if (!study) return "";
    const cells = [5,10,21,60].map((h) => {
      const x = study.horizons?.[String(h)];
      if (!x) return "";
      return `<div class="study-cell"><span>${h} DAYS</span><strong>${fmtReturn(x.median)}</strong><small>${Math.round(x.positive_rate)}% positive</small><small>Avg ${fmtReturn(x.average)} · n=${x.n}</small><small>Typical drawdown first: ${fmtReturn(x.median_max_drawdown)}</small><small>Typical upside excursion: ${fmtReturn(x.median_max_favorable)}</small></div>`;
    }).join("");
    return `<section class="study-block"><div class="study-kicker">${esc(title)}</div><p>${esc(study.rule || "Comparable historical condition")}</p><div class="study-grid">${cells}</div><div class="episode-note">${esc(study.episode_method || "")}</div></section>`;
  }

  function openHistory(id) {
    const s = window.__signals?.find((x) => x.id === id);
    if (!s) return;
    let blocks = "";
    if (id === "vol") {
      blocks = studyBlock("VIX TERM STRUCTURE",s.vol.term_study) + studyBlock("VVIX",s.vol.vvix_study) + studyBlock("SKEW",s.vol.skew_study);
    } else {
      blocks = studyBlock(s.name,s.study) + (s.secondaryStudy ? studyBlock("TRINQ",s.secondaryStudy) : "");
    }
    $("historyContent").innerHTML = `<div class="drawer-kicker">HISTORICAL PRECEDENT</div><h2>${esc(s.name)}</h2><p class="drawer-intro">What happened to SPY after independent historical episodes that looked like this?</p>${blocks}`;
    $("historyDrawer").hidden = false;
    document.body.classList.add("drawer-open");
  }

  function watched() {
    try { return JSON.parse(localStorage.getItem("marketPulseWatches") || "[]"); } catch { return []; }
  }
  function toggleWatch(id, btn) {
    const set = new Set(watched());
    if (set.has(id)) set.delete(id); else set.add(id);
    localStorage.setItem("marketPulseWatches", JSON.stringify([...set]));
    hydrateWatchButtons();
    if (set.has(id) && "Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(()=>{});
  }
  function hydrateWatchButtons() {
    const set = new Set(watched());
    document.querySelectorAll("[data-watch]").forEach((b) => { b.textContent = set.has(b.dataset.watch) ? "Watching ✓" : "Watch signal"; b.classList.toggle("active",set.has(b.dataset.watch)); });
  }
  function notifyWatched(signals) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const set = new Set(watched());
    signals.filter((s) => set.has(s.id) && ["extreme","severe"].includes(s.tone)).forEach((s) => {
      const key = `mp-notified-${s.id}-${s.asOf}`;
      if (localStorage.getItem(key)) return;
      new Notification(`Market Pulse: ${s.state}`, {body:`${s.name} is ${pctText(s.pct,s.side).toLowerCase()}.`});
      localStorage.setItem(key,"1");
    });
  }

  async function load() {
    try {
      const r = await fetch(`data/signal_data.json?v=${Date.now()}`, {cache:"no-store"});
      if (!r.ok) throw new Error("signal dataset unavailable");
      const data = await r.json();
      const signals = signalModel(data);
      window.__signals = signals;
      $("asOf").textContent = `Latest completed signal set · ${data.market_date || "—"}`;
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
