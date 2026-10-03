# Mini-thesis-remittances

ECO5016W — Minor Dissertation in FinTech, University of Cape Town

Author: Kerry-Lynn Whyte (WHYKER001)
Supervisor: Allan Davids

## Overview

`remittance_sim.py` is a parametric, graph-based simulation of the SA–SADC
remittance corridor. It models six payment architectures as directed graphs
and compares them across **cost**, **efficiency (time)** and **accessibility** dimensions at
three transfer sizes — **$50, $200, $500** — using deterministic results,
Monte Carlo analysis and a ranking-robustness test.

The primary analysis uses ±20% parameter variation (dissertation Tables 3
and 4). The script also repeats the analysis at
±50% and ±100% to check whether the Combined architecture's dominance depends
on that relatively narrow assumption (Section 3.3). ±100% variation is a deliberately
extreme stress test, not a realistic estimate of parameter uncertainty.

## Channels modelled

Each channel is a small `networkx` `DiGraph` whose edges carry `fee_pct`,
`fee_flat`, `fx_margin`, `time_hours` and `access_prob`:

| Channel | Path |
|---|---|
| **Cash ADLA** (Mukuru) | sender → ADLA booth → ADLA network → agent → recipient |
| **Bank** | sender → SA bank → correspondent bank → receiver bank → recipient |
| **Digital ADLA** (Sikhona / Mama Money) | sender → SA mobile wallet → payment network → receiver wallet → recipient |
| **TCIB** | sender → TCIB participant → TCIB clearing → receiver provider → recipient |
| **Blockchain** (Yellow Card) | sender → crypto platform → blockchain → payout partner → recipient |
| **Combined** (tiered eKYC + non-bank TCIB + mobile wallet payout) | sender → mobile wallet → TCIB clearing → receiver wallet → recipient |

Parameters are calibrated from FinMark Trust (2024), AfricaNenda (2022),
Srinivasan et al. (2025), Brandi et al. (2025), DiCaprio et al. (2025),
TechCentral (2024) and CNBC / Sigalos (2023); each channel's builder function
notes its specific sources.

`calculate_outcomes` walks the topologically sorted path and returns:

- `total_cost_usd` / `total_cost_pct` — `(Σ fee_pct + Σ fx_margin) × amount + Σ fee_flat`
- `total_time_hours` — sum of `time_hours`
- `effective_access_pct` — product of `access_prob` (first-mile access
  dominates, since all downstream edges have `access_prob = 1.0`)

## What the script does

`main()` runs five parts and prints each to the console:

1. **Deterministic results** (`run_dynamic_pricing`) — cost, time and access
   for every channel and amount with no parameter variation.
2. **Primary Monte Carlo, ±20%** (`run_monte_carlo`) — 1,000 trials per
   channel per amount. Each nonzero fee/FX/time parameter, and each access
   probability below 1.0, is multiplied by an independent
   `uniform(max(0, 1 − v), 1 + v)` draw (access is clipped to [0, 1]).
   Reports mean ± SE for cost, time and access (cf. Table 3).
3. **Primary ranking robustness, ±20%** (`run_ranking_test`) — 1,000 trials
   per amount, recording which channel ranks best on cost, time and access in
   each trial, reported as win-rates (cf. Table 4).
4. **Extended robustness** — repeats Parts 2–3 at ±20%, ±50% and ±100%,
   reporting cost (mean ± SE) per level, Combined's win-rates against the top
   alternative per level, and a full per-channel efficiency win-share
   breakdown at ±100% (cf. Tables 3(a–c) / 4(a–c)).
5. **Figures** — saves the dissertation's charts (see Outputs below).

A fixed seed (`np.random.seed(42)`) is set at import and reset at the start
of each `run_monte_carlo` / `run_ranking_test` call, so every variation level
starts from the same random state and all reported results are reproducible.

## Requirements

- Python 3
- `numpy`
- `networkx`
- `matplotlib`

```bash
pip install numpy networkx matplotlib
```

## Usage

```bash
cd Mini-thesis-remittances
python remittance_sim.py
```

## Outputs

| File | Contents |
|---|---|
| `simulation_results.txt` | Full console output for Parts 1–4 |
| `dynamic_pricing.png` | Deterministic cost by channel at each transfer amount |
| `monte_carlo_50.png`, `monte_carlo_200.png`, `monte_carlo_500.png` | Cost, time and access (mean ± SE, ±20%) per channel at each amount |
| `cost_by_amount.png` | How each channel's mean cost changes with transfer amount |

Every cost chart marks the SDG 3% remittance-cost target with a dashed line.

