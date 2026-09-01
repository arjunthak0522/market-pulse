# Market Pulse - Democratized Market Intelligence Acceptance Standard

This is a simulated product-review framework used for QA. It does not represent participation by actual named professional traders, Robinhood users, CNBC employees, or people recruited off the street.

## Product principle

Market Pulse should democratize access to meaningful market intelligence.

A user should not need to know technical analysis, options terminology, macro plumbing, or market jargon to understand:
1. What kind of market are we in?
2. Is risk getting better or worse?
3. What changed?
4. What matters now?
5. What would change the view?

Technical depth can exist underneath, but the default experience must translate sophisticated evidence into useful plain-English decisions.

## Review panels

### Ultra-efficient swing trader panel
Representative review lenses:
- Experienced swing trader who spends no more than 5 minutes per day on market homework
- Price-action trader focused on 2-day to 6-week setups
- Trend follower focused on confirmation and invalidation
- Mean-reversion trader focused on washouts and exhaustion
- Options-aware trader focused on volatility structure and hedging stress
- Risk manager focused on avoiding redundant signals and false precision

This panel must be able to answer within about 30 seconds:
- What is the setup?
- What confirms it?
- What contradicts it?
- What is stretched?
- What is the next decision-relevant level or condition?
- Is there enough evidence to act or should I wait?

The full daily review should take less than 5 minutes.

### Robinhood-style retail panel
Representative comprehension profiles:
- Mobile-first investor who mainly knows ticker symbols and percentage moves
- Investor who reacts to headlines and large daily moves
- Beginner who has seen RSI or VIX mentioned online but does not understand the mechanics
- Investor who wants to know whether a dip is ordinary or genuinely concerning

This panel must not need to learn formulas before understanding the conclusion.

### Grandma test
Representative comprehension profile:
- Smart non-market-specialist with no technical-analysis vocabulary
- Reads ordinary English comfortably
- Wants to know whether conditions look healthy, stressed, stretched, or uncertain

Within 30 seconds, this user should be able to explain the dashboard back in ordinary language.

Reject if the main takeaway depends on terms such as contango, backwardation, VVIX, breadth, SKEW, MACD, or put/call without a plain-English interpretation shown first.

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
- TV market strategist focused on concise explanation
- Cross-asset strategist focused on regime, liquidity, and risk context
- Technical strategist focused on correct signal interpretation
- Quant/event-study reviewer focused on statistical discipline

## Universal acceptance test

Within about 10 seconds, any user should be able to answer:
1. What kind of market is this?
2. Is risk improving or worsening?
3. What changed?

Within about 30 seconds, any user should be able to answer:
1. What matters most right now?
2. Is the market healthy, stretched, stressed, or mixed?
3. What would make the view materially better or worse?

Within about 60 seconds, a motivated user should understand:
1. Why the dashboard holds its current view
2. Whether participation supports the indexes
3. Whether risk pricing is calm, rising, or acute
4. Whether selling looks ordinary or exhausted
5. Whether crowd sentiment is confirming or diverging
6. Whether global liquidity is supportive or restrictive
7. What historically happened after a comparable setup

## Indicator admission rules

Every visible indicator must pass all of these tests:
- Distinct information: it adds useful information not already provided by another visible signal
- Actionability: a change can alter a watch condition, setup classification, or risk assessment
- Timing relevance: appropriate for the tactical horizon
- Interpretability: a non-expert understands the conclusion before the formula
- Reliability: missing or stale data is explicit
- Scan efficiency: it earns the screen space it consumes

Do not remove a technically overlapping indicator solely because correlation is high. Keep it if it materially improves timing, exhaustion detection, confirmation, or comprehension.

## Current technical-indicator review set

The current review build should test:
- RSI - short-term momentum/stretch
- Williams %R - fast range-position/exhaustion signal
- MACD - trend momentum
- ADX - trend strength
- 50-day distance - intermediate trend
- 200-day distance - primary trend

Williams %R remains in the active review set. The panel must determine whether it adds enough timing/exhaustion information beyond RSI to justify a permanent visible slot.

Bollinger %B and 20-day moving-average distance remain candidates for demotion because their incremental decision value is currently weaker.

## Language rules

- Conclusion before indicator name
- Plain English before technical terminology
- One dominant takeaway per section
- One clear Watch Next condition when possible
- Never describe an oversold condition as a confirmed bottom
- Never describe high SKEW as a crash prediction
- Never describe high Stocktwits sentiment as a buy or sell signal
- Never describe a liquidity proxy as a deterministic market forecast
- Never imply historical precedent predicts the future
- Missing data must display as unavailable, never as zero

Preferred language:
- Market participation, not breadth, in primary copy
- Intermediate support, not 50DMA, in primary copy
- Long-term support, not 200DMA, in primary copy
- Short-term momentum stretch, not RSI, in primary copy
- Fast exhaustion check, not Williams %R, in primary copy
- How urgent is fear?, not VIX term structure, in primary copy
- Volatility instability, not VVIX, in primary copy
- Crash-insurance demand, not SKEW, in primary copy
- How defensive are traders?, not put/call positioning, in primary copy
- Crowd sentiment, not Stocktwits score, in primary copy
- Crowd attention, not message volume, in primary copy
- Global liquidity backdrop, not central-bank balance-sheet composite, in primary copy

## Section-level acceptance

### Market Regime
Must state the regime and concise thesis. Trend, Participation, and Stress are the only equally weighted top-level evidence categories. Liquidity and sentiment are contextual confirmation.

### What Changed
Only meaningful changes should surface. Routine noise stays out.

### Watch Next
Prefer one decision-relevant condition over a laundry list. Clearly distinguish confirmation from invalidation.

### Market Participation
Explain whether the move is broad or narrow without requiring the user to understand market breadth terminology.

### Turning Point Evidence
Explain whether selling is spreading, becoming extreme, stabilizing, or reversing. Fast stretch indicators may support this section but cannot independently declare a bottom.

### Stress & Options Risk
Default questions:
- How urgent is fear?
- Is volatility itself becoming unstable?
- How defensive are traders?
- How expensive is crash insurance?

Spot VIX must not appear as a standalone signal.

### Market Sentiment
Default view:
- SPY crowd sentiment
- QQQ crowd sentiment
- Crowd-attention extremes only when unusual

No raw social feed. Sentiment is confirmation/divergence context only.

### Global Liquidity
Default view should answer:
- Is liquidity supportive, mixed, or restrictive?
- Is it improving or deteriorating?
- Is it confirming or diverging from equities?

Methodology must remain inspectable. Do not claim a fixed lead time unless validated historically.

### SPY / QQQ Detail
State the conclusion first. Technical evidence remains secondary.

## Five-minute swing-trader test

A complete daily dashboard review must fit inside 5 minutes without sacrificing important information.

Reject if:
- A trader must inspect several duplicate indicators to reach the same conclusion
- The important contradiction is buried below the fold
- A warning has no confirmation or invalidation condition
- More than 5 primary tactical conclusions compete for attention
- Sentiment or liquidity is presented as a standalone trade trigger
- Structural trend and tactical stretch are visually indistinguishable
- The user has to manually synthesize multiple technical cards to understand the setup

## Grandma test

Reject if a smart non-specialist cannot answer these questions after one pass:
- Is the market basically healthy or unhealthy?
- Are investors calm or nervous?
- Is the market move broad or being driven by only a few stocks?
- Is the market unusually stretched?
- What should I watch next?

Technical terminology is allowed only after the plain-English answer has already been given.

## Visual/mobile acceptance

Required rendered checks:
- Desktop
- Tablet
- 393 x 852
- 375 px width

Reject if:
- Supporting text is too dim
- Essential labels are microscopic
- Desktop is merely compressed onto mobile
- A screenful contains more than 3-4 equally weighted conclusions
- Technical tables dominate the default view
- Expanded details are required to understand the main conclusion
- The 5-minute trader requires excessive scrolling

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

Evidence labels describe sample depth only. They are not confidence ratings.

## Current pre-render verdict

Technical and language architecture can pass static review only after CI succeeds. Final acceptance still requires rendered visual QA across the required viewports and simulated review by all panels above. Production remains frozen until that gate passes and deployment is explicitly authorized.
