# Market Pulse Rescue Status

Branch: `signal-quality-review`

Production policy: `main` and GitHub Pages production remain frozen until the owner explicitly says `DEPLOY`.

## Product contract ledger

| Capability | Status | Current owner / note |
|---|---|---|
| Market Pulse Score | IMPLEMENTED BUT NEEDS VALIDATION | `daily-experience.js`. Transparent 0-100 composite with visible drivers. |
| Market brief | IMPLEMENTED BUT NEEDS VALIDATION | `daily-experience.js`. Plain-English current-data synthesis. |
| Primary trend driver | IMPLEMENTED BUT NEEDS VALIDATION | Score driver + `guide.js` health drill-down. |
| Participation driver | LIVE | Core breadth data in `market_context.json`; presentation needs rendered QA. |
| Risk pricing driver | LIVE | VIX, put/call and options-risk data available; `options-risk.js` deterministic presentation needs rendered QA. |
| Momentum / stretch driver | LIVE | RSI, Williams %R, MACD, ADX, Bollinger and moving-average evidence available through SPY/QQQ workspace. |
| Turning-point pressure | IMPLEMENTED BUT NEEDS VALIDATION | `guide.js` synthesis + breadth cycle. No longer owned by competing tactical overlays. |
| SPY / QQQ switcher | LIVE | Base `app.js`; interaction still needs rendered QA. |
| Williams %R | LIVE | Data present; `williams-review.js` keeps it in technical evidence. |
| Market participation 5/20/50/200 | LIVE | Core dataset populated. |
| Advance / decline context | LIVE | Core dataset populated and used by turning-point intelligence. |
| Breadth cycle | LIVE | Data populated; deterministic `breadth-cycle.js` presentation. |
| VIX / VIX3M fear urgency | IMPLEMENTED BUT NEEDS VALIDATION | Options-risk feed/presentation. |
| VVIX volatility instability | IMPLEMENTED BUT NEEDS VALIDATION | Options-risk feed/presentation. |
| Equity put/call defensiveness | LIVE | Core feed populated. |
| SKEW crash-insurance demand | IMPLEMENTED BUT NEEDS VALIDATION | Options-risk feed/presentation. |
| Historical event studies | IMPLEMENTED BUT NEEDS VALIDATION | `historical-forward-returns.js`; 5/10/21/60-day horizons shown when present, low samples flagged. |
| Prior occurrences | IMPLEMENTED BUT NEEDS VALIDATION | Exposed when the study record provides occurrence dates. |
| Sector leadership | LIVE | Core dataset populated; breadth-cycle presentation. |
| Smart alerts | IMPLEMENTED BUT NEEDS VALIDATION | Base app / daily live logic. Browser limitations must remain explicit. |
| What changed | LIVE | Base app uses stored market history; rendered hierarchy needs QA. |
| What changes the view | IMPLEMENTED BUT NEEDS VALIDATION | Score + deterministic `guide.js`. |
| Morning Read | IMPLEMENTED BUT NEEDS VALIDATION | `daily.js`; only pre-market. |
| Closing Read | IMPLEMENTED BUT NEEDS VALIDATION | `daily.js`; only after close. |
| Intraday Live Pulse | IMPLEMENTED BUT NEEDS VALIDATION | `daily.js`; market-hours only, separate from official close regime. |
| Stocktwits sentiment | BLOCKED BY DATA OR CREDENTIALS | `data/stocktwits_sentiment.json` says `credentials_required`. Do not fake or score it. |
| Global Liquidity | BLOCKED BY DATA OR CREDENTIALS | Updater exists but `data/global_liquidity.json` remains `pending_refresh`. Do not surface a directional score yet. |

## Architecture decisions

### Keep
- `app.js` as the base market/indicator renderer.
- `daily-experience.js` as the single owner of the top score, five-driver board, brief and top-level watch condition.
- `guide.js` as the single owner of market-health and turning-point synthesis.
- `daily.js` as the single owner of time-sensitive Morning Read, Closing Read and intraday live pulse.
- `options-risk.js`, `history-intelligence.js`, `breadth-cycle.js`, and `historical-forward-returns.js` as specialized deterministic modules.
- `investor-language.js` for plain-English labeling.
- `williams-review.js` to preserve Williams %R evidence.

### Redundant presentation layers retired
These files remain as inert compatibility stubs on the review branch so references cannot fail while their duplicate behavior is removed:
- `premium.js`
- `strategist.js`
- `strategist-daily.js`
- `indicator-commentary.js`
- `tactical-summary.js`
- `actionable-summary.js`
- `historical-priority.js`
- `signal-quality.js`
- `focus-mode.js` is static-only and performs no delayed rendering.

## Reliability rule

No presentation module may use repeated `setTimeout` reconciliation, late script injection, late stylesheet injection, MutationObserver layout rewrites, or repeated DOM reordering. A time interval is allowed only for genuinely time-sensitive session/live-market refresh behavior.

## Acceptance gates still open

- Desktop rendered inspection
- Mobile rendered inspection at 320, 375, 390 and 430px
- SPY/QQQ tab interaction
- Signal-driver drill-down interaction
- Dialog close/open behavior
- Historical event expansion
- Smart-alert interaction and browser-permission messaging
- Session visibility across pre-market, open market, after close and weekends
- Horizontal overflow / clipping / touch-target review
- Data-staleness UI review
- First validated Global Liquidity refresh
- Stocktwits credentials and schema validation before activation

A successful syntax check or GitHub commit is not UAT acceptance.
