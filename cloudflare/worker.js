const QUOTES_URL = "https://stockcharts.com/quotebrain/quotes";

const SYMBOLS = [
  "$CPCE",
  "$NYADV", "$NYDEC", "$NYHGH", "$NYLOW", "$NYTOT", "$TRIN",
  "$NAADV", "$NADEC", "$NAHGH", "$NALOW", "$NATOT", "$TRINQ",
  "$SPXA20R", "$SPXA50R", "$SPXA200R",
  "$VIX", "$VIX3M", "$VVIX", "$SKEW"
];

const UPSTREAM_HEADERS = {
  "user-agent": "Mozilla/5.0 MarketPulse/1.0",
  "accept": "application/json,text/plain,*/*",
  "referer": "https://stockcharts.com/"
};

function providerTimestamp(row) {
  const millis = Number(row?.time?.millis);
  if (Number.isFinite(millis)) {
    return new Date(millis > 10_000_000_000 ? millis : millis * 1000).toISOString();
  }
  return row?.time?.time ? String(row.time.time) : null;
}

async function getQuote(symbol) {
  const url = new URL(QUOTES_URL);
  url.searchParams.set("s", symbol);
  url.searchParams.set("f", "json");
  url.searchParams.set("randomNumber", String(Date.now()));

  const response = await fetch(url, { headers: UPSTREAM_HEADERS });
  if (!response.ok) throw new Error(`${symbol}: HTTP ${response.status}`);

  const payload = await response.json();
  if (!Array.isArray(payload) || payload.length !== 1 || typeof payload[0] !== "object") {
    throw new Error(`${symbol}: malformed quote payload`);
  }

  const row = payload[0];
  const value = Number(row.close);
  if (!Number.isFinite(value)) throw new Error(`${symbol}: missing current value`);

  return {
    symbol,
    value,
    open: Number.isFinite(Number(row.open)) ? Number(row.open) : null,
    high: Number.isFinite(Number(row.high)) ? Number(row.high) : null,
    low: Number.isFinite(Number(row.low)) ? Number(row.low) : null,
    provider_timestamp: providerTimestamp(row),
    provider_source: row.source || null,
    provider_realtime_flag: Boolean(row.realtime)
  };
}

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "";
  const allowed = origin === "https://arjunthak0522.github.io" || origin === "null";
  return {
    "access-control-allow-origin": allowed ? origin : "https://arjunthak0522.github.io",
    "access-control-allow-methods": "GET, OPTIONS",
    "access-control-allow-headers": "content-type",
    "vary": "Origin"
  };
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }
    if (request.method !== "GET") {
      return new Response("Method not allowed", { status: 405, headers: corsHeaders(request) });
    }

    const settled = await Promise.allSettled(SYMBOLS.map(getQuote));
    const quotes = {};
    const errors = [];

    settled.forEach((result, index) => {
      const symbol = SYMBOLS[index];
      if (result.status === "fulfilled") quotes[symbol] = result.value;
      else errors.push({ symbol, error: String(result.reason?.message || result.reason) });
    });

    const critical = ["$TRIN", "$TRINQ", "$NYHGH", "$NYLOW", "$NAHGH", "$NALOW", "$VIX", "$VIX3M"];
    const missingCritical = critical.filter((symbol) => !quotes[symbol]);
    const status = missingCritical.length ? 503 : 200;

    return new Response(JSON.stringify({
      generated_at: new Date().toISOString(),
      source: "StockCharts QuoteBrain via Market Pulse Cloudflare Worker",
      refresh_guidance_seconds: 300,
      quotes,
      errors,
      complete: errors.length === 0,
      missing_critical: missingCritical
    }), {
      status,
      headers: {
        ...corsHeaders(request),
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=30, s-maxage=60"
      }
    });
  }
};
