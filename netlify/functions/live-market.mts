const QUOTES_URL = "https://stockcharts.com/quotebrain/quotes";

const SYMBOLS = [
  "$CPCE",
  "$NYADV", "$NYDEC", "$NYHGH", "$NYLOW", "$NYTOT", "$NYMO", "$TRIN",
  "$NAADV", "$NADEC", "$NAHGH", "$NALOW", "$NATOT", "$NAMO", "$TRINQ",
  "$SPXA20R", "$SPXA50R", "$SPXA200R",
  "$VIX", "$VIX3M", "$VVIX", "$SKEW"
];

const HEADERS = {
  "user-agent": "Mozilla/5.0 MarketPulse/1.0",
  "accept": "application/json,text/plain,*/*",
  "referer": "https://stockcharts.com/"
};

function quoteTimestamp(row) {
  const millis = row?.time?.millis;
  if (Number.isFinite(Number(millis))) {
    const raw = Number(millis);
    return new Date(raw > 10_000_000_000 ? raw : raw * 1000).toISOString();
  }
  const raw = row?.time?.time;
  if (raw) return String(raw);
  return null;
}

async function getQuote(symbol) {
  const url = new URL(QUOTES_URL);
  url.searchParams.set("s", symbol);
  url.searchParams.set("f", "json");
  url.searchParams.set("randomNumber", String(Date.now()));

  const response = await fetch(url, {headers: HEADERS, cache: "no-store"});
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
    provider_timestamp: quoteTimestamp(row),
    provider_source: row.source || null,
    provider_realtime_flag: Boolean(row.realtime)
  };
}

export default async () => {
  const settled = await Promise.allSettled(SYMBOLS.map(getQuote));
  const quotes = {};
  const errors = [];

  settled.forEach((result, index) => {
    const symbol = SYMBOLS[index];
    if (result.status === "fulfilled") quotes[symbol] = result.value;
    else errors.push({symbol, error: String(result.reason?.message || result.reason)});
  });

  const critical = ["$TRIN", "$TRINQ", "$NYADV", "$NYDEC", "$NAADV", "$NADEC", "$VIX", "$VIX3M"];
  const missingCritical = critical.filter((symbol) => !quotes[symbol]);
  const status = missingCritical.length ? 503 : 200;

  return new Response(JSON.stringify({
    generated_at: new Date().toISOString(),
    source: "StockCharts QuoteBrain via Market Pulse server-side relay",
    quotes,
    errors,
    complete: errors.length === 0,
    missing_critical: missingCritical
  }), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store, max-age=0",
      "access-control-allow-origin": "*"
    }
  });
};

export const config = {
  path: "/api/live-market"
};
