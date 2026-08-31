# Market Pulse - Retail Investor + Market Strategist Acceptance Standard

This is a simulated expert-panel review framework used for product QA. It does not represent participation by actual CNBC employees or external research participants.

## Review panels

### Retail investor panel
Representative comprehension profiles:
- New investor who knows SPY/QQQ but not technical analysis
- Long-term ETF investor who checks markets daily
- Retirement investor focused on risk rather than trading
- Intermediate investor familiar with VIX and moving averages
- Mobile-first investor reading the dashboard in under one minute
- Investor who opens the dashboard only during volatile markets

### Market strategist panel
Representative review lenses:
- TV market strategist focused on concise on-air explanation
- Cross-asset strategist focused on regime and risk context
- Technical strategist focused on correct signal interpretation
- Quant/event-study reviewer focused on statistical discipline

## Mandatory comprehension test

Within about 10 seconds, a retail investor should be able to answer:
1. What kind of market is this?
2. Is risk improving or worsening?
3. What changed?
4. Does the change matter?
5. What should I watch next?

Within about 60 seconds, the same investor should understand:
1. Why the dashboard holds its current view
2. Whether participation supports the indexes
3. Whether market stress is calm, rising, or acute
4. Whether selling looks ordinary or exhausted
5. What historically happened after a comparable setup
6. What could invalidate the current view

## Language rules

- Conclusion before indicator name
- Plain English before technical terminology
- One dominant takeaway per section
- One clear Watch Next condition when possible
- Technical labels remain available as secondary education
- Never describe an oversold condition as a confirmed bottom
- Never describe high SKEW as a crash prediction
- Never describe historical drift as signal alpha
- Never imply historical precedent predicts the future
- Missing data must display as unavailable, never as zero

Preferred language:
- Market participation, not breadth, in primary copy
- Intermediate support, not 50DMA, in primary copy
- Long-term support, not 200DMA, in primary copy
- Short-term momentum stretch, not RSI, in primary copy
- Selling-volume pressure, not TRIN, in primary copy
- How urgent is fear?, not VIX term structure, in primary copy
- Crash-insurance demand, not SKEW, in primary copy
- How defensive are traders?, not put/call positioning, in primary copy
- Typical worst drop, not maximum adverse excursion, in primary copy
- Better or worse than normal?, not historical alpha, in primary copy

## Section-level acceptance

### Market Regime
Must state the regime and a concise thesis. Trend, Participation, and Stress are the only equally weighted top-level evidence categories.

### Morning / Live / Closing Read
Only the context appropriate to the current market session should appear. Intraday data can challenge the prior-close thesis but must not silently replace the official closing regime.

### What Changed
Only meaningful changes should surface. Routine noise should not compete for attention.

### Watch Next
Prefer one decision-relevant condition over a laundry list.

### Market Health
Trend, Participation, Stress only. Leadership and momentum are supporting context.

### Turning Point Evidence
Explain whether selling is spreading, becoming extreme, stabilizing, or confirming a turn. A/D, oversold-stock share, and selling-volume pressure are supporting evidence. Put/call does not belong here.

### Historical Forward Returns
Default view must show:
- Exact current or selected setup
- Prior-example count
- Evidence label
- Typical forward return
- Percentage ending higher
- Comparison with normal market behavior
- Typical downside path
- Plain-English strategist read

Detailed statistics, quartiles, path thresholds, regime splits, and methodology belong under progressive disclosure.

### Stress & Options Risk
Primary labels should answer human questions:
- Fear Level
- How Urgent Is Fear?
- How Defensive Are Traders?
- Crash-Insurance Demand

Technical names are secondary.

### SPY / QQQ Detail
State what the current structure means before displaying technical evidence. Technical evidence remains collapsed by default.

## Visual/mobile acceptance

Required rendered checks:
- Desktop
- Tablet
- 393 x 852
- 375 px width

Reject if:
- Supporting text is too dim to read comfortably
- Essential labels are visually microscopic
- Desktop content is merely compressed onto mobile
- A screenful presents more than 3-4 equally weighted conclusions
- Technical tables dominate the default mobile view
- Expanded details are required to understand the main conclusion

## Statistical acceptance for historical studies

Must validate:
- Event dates
- Trading-session horizons
- No look-ahead bias
- Duplicate/cooldown logic
- Baseline calculations
- Median and mean
- Positive/negative rates
- Quartiles and best/worst
- Maximum favorable/adverse path
- Threshold-hit probabilities
- Same-bar hit-order ambiguity
- Regime splits
- Low-sample and end-of-history behavior
- Current event detection
- Cached/precomputed delivery

Evidence labels describe sample depth only. They must never be described as confidence ratings.

## Current pre-render verdict

Technical and language architecture can pass static review only after CI succeeds. Final product acceptance still requires rendered visual QA at all required viewport sizes. Production remains frozen until that visual gate passes and deployment is explicitly authorized.
