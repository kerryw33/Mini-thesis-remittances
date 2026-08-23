# Mini-thesis-remittances

ECO5016W — Minor Dissertation in FinTech, University of Cape Town

Author: Kerry-Lynn Whyte (WHYKER001)
Supervisor: Allan Davids

## Overview

`remittance_sim.py` models six cross-border remittance channels as directed
graphs and runs a Monte Carlo robustness test to see how each channel's cost,
speed, and access performance holds up as the underlying fee/FX/time/access
parameters are varied by increasing amounts.

Per supervisor feedback, this script extends the original single-level
(±20%) Monte Carlo analysis to report both the **cost (mean ± SE)** table and
the **ranking-robustness** table at three parameter uncertainty levels —
±20%, ±50%, ±100% — so that the Combined architecture's dominance can be
assessed as parameter uncertainty widens, rather than relying on one
relatively narrow assumption. ±20% is retained as the first level for direct
comparability with the earlier results.

## Channels modelled

Each channel is built as a small `networkx` `DiGraph` with edges carrying
`fee_pct`, `fee_flat`, `fx_margin`, `time_hours`, and `access_prob`:

- **Cash ADLA** — sender → ADLA agent → ADLA network → agent out → recipient
- **Bank** — sender → SA bank → correspondent bank → receiver bank → recipient
- **Digital ADLA** — sender → sender wallet → payment network → receiver wallet → recipient
- **TCIB** — sender → sender bank → TCIB clearing → receiver provider → recipient
- **Blockchain** — sender → crypto platform → blockchain → payout partner → recipient
- **Combined** — sender → mobile entry → TCIB clearing → receiver wallet → recipient

Outcomes per channel (`calculate_outcomes`) are computed by summing fees/FX
margin/time along the topologically sorted path and multiplying access
probabilities:

- `total_cost_pct` — total cost as a % of the transfer amount
- `total_time_hours` — total transfer time
- `effective_access_pct` — effective access probability

Transfer amounts tested: **$50, $200, $500**.

## What the script does

1. **Cost (mean ± SE) analysis** (`run_monte_carlo_at_variation`) — for each
   variation level, runs 1,000 trials per channel per transfer amount,
   randomly perturbing each nonzero fee/FX/time/access parameter by a
   `uniform(1 - variation, 1 + variation)` multiplier (clipped at 0, and at
   1.0 for access probability), and reports mean ± standard error for cost,
   time, and access.
2. **Ranking-robustness analysis** (`run_ranking_at_variation`) — for the
   same variation levels, runs 1,000 trials per transfer amount and records,
   per trial, which channel ranks best on cost, time, and access, reporting
   each channel's win-rate as a percentage.
3. **Reporting** (`main`) — prints and writes both tables (Parts 1 and 2),
   plus a full per-channel efficiency win-share breakdown at the widest
   (±100%) variation level (Part 2b).

A fixed random seed (`np.random.seed(42)`) is used throughout for
reproducibility.

## Requirements

- Python 3
- `numpy`
- `networkx`

## Usage

```bash
python remittance_sim.py
```

Results are printed to the console and written to
`robustness_variation_results.txt`.
