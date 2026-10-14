# Formulas / Formules

Definitions used by `scripts/kelly_size.py`, `validate_risk.py`, and `performance.py`.

## Edge

\[
\text{edge} = p_{\text{model}} - p_{\text{market}}
\]

Require \(\text{edge} > \texttt{predict.min\_edge}\) (default **0.04**). Positive edge means the model thinks YES is underpriced (or adjust sign when trading NO).

## Expected value (EV)

For a YES share bought at price \(c = p_{\text{market}}\) (pays 1 if YES):

\[
\text{EV} = p_{\text{model}} \cdot (1 - c) - (1 - p_{\text{model}}) \cdot c
= p_{\text{model}} - c
\]

So EV per €1 of notional (in probability units) equals edge. In euros for stake \(s\) (cash outlay \(s\), contracts \(s/c\)):

\[
\text{EV}_{\euro} = \frac{s}{c} \cdot (p_{\text{model}} - c)
\]

## Mispricing z-score

If you have a forecast variance or historical residual std \(\sigma\):

\[
z = \frac{p_{\text{model}} - p_{\text{market}}}{\sigma}
\]

Large \(|z|\) flags anomalies; combine with liquidity/spread filters from `scan`.

## Brier score

For binary outcomes \(y \in \{0,1\}\) and forecast \(p\):

\[
\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2
\]

Lower is better (0 = perfect). Computed by `performance.py` when `predictions_log.jsonl` rows include `p_model` and `outcome`.

## Kelly criterion (full)

Net decimal odds when buying YES at price \(c\): stake \(c\), receive 1 on win ⇒ net odds

\[
b = \frac{1 - c}{c}
\]

Full Kelly fraction of bankroll:

\[
f^{*} = \frac{p \cdot b - (1 - p)}{b} = \frac{p - c}{1 - c}
\]

Clamp \(f^{*} \ge 0\) (no bet if edge ≤ 0 under this parameterization).

## Fractional Kelly

\[
f = \lambda \cdot f^{*}, \quad \text{size} = f \cdot \text{bankroll}
\]

Default \(\lambda = \texttt{risk.kelly\_fraction} = 0.25\) (quarter-Kelly). Cap further by `max_position_pct`, `max_total_exposure_pct`, and concurrent-position limits in `validate_risk.py`.
