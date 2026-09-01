# Market Pulse - Retail Investor + Market Strategist + Swing Trader Acceptance Standard

This is a simulated expert-panel review framework used for product QA. It does not represent participation by actual CNBC employees, named professional traders, or external research participants.

## Review panels

### Retail investor panel
Representative comprehension profiles:
- New investor who knows SPY/QQQ but not technical analysis
- Long-term ETF investor who checks markets daily
- Retirement investor focused on risk rather than trading
- Intermediate investor familiar with volatility and moving averages
- Mobile-first investor reading the dashboard in under one minute
- Investor who opens the dashboard only during volatile markets

### Market strategist panel
Representative review lenses:
- TV market strategist focused on concise on-air explanation
- Cross-asset strategist focused on regime, liquidity, and risk context
- Technical strategist focused on correct signal interpretation
- Quant/event-study reviewer focused on statistical discipline

### Swing trader panel
Representative review lenses:
- Price-action swing trader focused on 2-day to 6-week setups
- Trend-following swing trader focused on confirmation and invalidation
- Mean-reversion trader focused on washouts and exhaustion
- Options-aware swing trader focused on volatility structure and hedging stress
- Risk manager focused on avoiding false precision and redundant signals
- Mobile-first active trader who must identify the setup in under 20 seconds

The swing-trader panel must reject any indicator that does not answer at least one of these questions:
1. Is the setup improving or deteriorating?
2. Is the current move stretched enough to matter?
3. Is market participation confirming the move?
4. Is risk pricing confirming or contradicting price action?
5. Is liquidity becoming more or less supportive?
6. What exact condition would strengthen, weaken, or invalidate the setup?

## Mandatory comprehension test

Within about 10 seconds, a retail investor should be able to answer:
1. What kind of market is this?
2. Is risk improving or worsening?
3. What changed?
4. Does the change matter?
5. What should I watch next?

Within about 20 seconds, a swing trader should be able to answer:
1. Is the current setup risk-on, risk-off, washout, or mixed?
2. What is the strongest confirming signal?
3. What is the strongest contradiction or divergence?
4. What is the next decision-relevant level or condition?
5. Is there enough evidence to act, or should the trader wait for confirmation?

Within about 60 seconds, the same investor should understand:
1. Why the dashboard holds its current view
2. Whether participation supports the indexes
3. Whether market stress is calm, rising, or acute
4. Whether selling looks ordinary or exhausted
5. What historically happened after a comparable setup
6. What could invalidate the current view

## Indicator admission rules

Every visible indicator must pass all of these tests:
- Distinct information: it adds information not already provided by another visible signal
- Actionability: a change in the indicator can alter a watch condition, setup classification, or risk assessment
- Timing relevance: the indicator is appropriate for the dashboard's tactical horizon
- Interpretability: a non-expert can understand the conclusion without learning the formula first
- Reliability: missing or stale data is explicitly shown and never silently substituted

Reject or demote indicators that are highly correlated with an existing measure and do not change the decision. Technical evidence may remain available under progressive disclosure when educationally useful.

## Language rules

- Conclusion before indicator name
- Plain English before technical terminology
- One dominant takeaway per section
- One clear Watch Next condition when possible
- Technical labels remain available as secondary education
- Never describe an oversold condition as a confirmed bottom
- Never describe high SKEW as a crash prediction
- Never describe high Stocktwits sentiment as a buy or sell signal
- Never describe historical drift as signal alpha
- Never imply historical precedent predicts the future
- Never describe a liquidity proxy as a deterministic market forecast
- Missing data must display as unavailable, never as zero

Preferred language:
- Market participation, not breadth, in primary copy
- Intermediate support, not 50DMA, in primary copy
- Long-term support, not 200DMA, in primary copy
- Short-term momentum stretch, not RSI, in primary copy
- Selling-volume pressure, not TRIN, in primary copy
- How urgent is fear?, not VIX term structure, in primary copy
- Volatility-of-volatility stress, not VVIX, in primary copy
- Crash-insurance demand, not SKEW, in primary copy
- How defensive are traders?, not put/call positioning, in primary copy
- Crowd sentiment, not Stocktwits score, in primary copy
- Crowd attention, not message volume, in primary copy
- Global liquidity backdrop, not central-bank balance-sheet composite, in primary copy
- Typical worst drop, not maximum adverse excursion, in primary copy
- Better or worse than normal?, not historical alpha, in primary copy

## Section-level acceptance

### Market Regime
Must state the regime and a concise thesis. Trend, Participation, and Stress are the only equally weighted top-level evidence categories. Liquidity and sentiment are contextual confirmation, not automatic regime overrides.

### Morning / Live / Closing Read
Only the context appropriate to the current market session should appear. Intraday data can challenge the prior-close thesis but must not silently replace the official closing regime.

### What Changed
Only meaningful changes should surface. Routine noise should not compete for attention.

### Watch Next
Prefer one decision-relevant condition over a laundry list. A swing trader must be able to distinguish confirmation from invalidation.

### Market Health
Trend, Participation, Stress only. Leadership, momentum, liquidity, and sentiment are supporting context.

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
- How urgent is fear?
- Is volatility itself becoming unstable?
- How defensive are traders?
- How expensive is crash insurance?

Spot VIX must not appear as a standalone signal. It may be used only as a component required to calculate a more informative structure measure.

### Market Sentiment
Default view should show only:
- SPY crowd sentiment
- QQQ crowd sentiment
- Crowd-attention extremes when message volume is unusually high or low

Do not display a raw social feed. Posts may not influence the dashboard thesis directly. Sentiment is confirmation or divergence context only.

### Global Liquidity
Must show a transparent proxy, not a proprietary black-box score. The default view should answer:
- Is the global liquidity backdrop improving, flat, or tightening?
- Is the rate of change accelerating or decelerating?
- Is liquidity confirming or diverging from the equity trend?

The methodology and component sources must be inspectable. Do not imply a fixed lead time unless historical testing supports it.

### SPY / QQQ Detail
State what the current structure means before displaying technical evidence. Technical evidence remains collapsed by default.

Swing-trader technical evidence should default to one primary measure per question:
- Momentum stretch: RSI
- Trend momentum: MACD
- Trend strength: ADX
- Intermediate trend: distance from 50-day average
- Primary trend: distance from 200-day average

Williams %R, Bollinger %B, and the 20-day moving-average distance should not be visible by default because they overlap with the retained measures.

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
- A swing trader cannot identify the strongest confirmation, contradiction, and watch-next condition without scrolling through multiple screens

## Swing-trader actionability acceptance

Reject the build if any of these are true:
- Two visible indicators regularly produce the same conclusion and neither changes the action
- A warning is shown without a specific confirmation or invalidation condition
- A signal is visually prominent but has no defined role in the regime, washout, divergence, or watch-next logic
- Sentiment or liquidity is presented as a standalone trade trigger
- The dashboard requires interpretation of more than five primary tactical signals to reach a decision
- The user cannot distinguish structural trend evidence from tactical stretch

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
