"""
Monte Carlo Robustness Test Across Multiple Parameter Variation Levels
=======================================================================
ECO5016W — Minor Dissertation in FinTech
University of Cape Town

Author: Kerry-Lynn Whyte (WHYKER001)
Supervisor: Allan Davids

Purpose
-------
The main simulation (remittance_simulation.py) originally reported Monte
Carlo cost (mean +/- SE) and ranking-robustness results at a single
parameter uncertainty level (+/-20%). Per supervisor feedback, this script
instead reports BOTH the cost (mean +/- SE) table and the ranking table at
three variation levels -- +/-20%, +/-50%, +/-100% -- so that Combined
architecture's dominance can be assessed as parameter uncertainty widens,
rather than relying on a single, relatively narrow assumption. +/-20% is
retained as the first level for direct comparability with earlier results.

Uses the same six channel definitions, parameters, and calculation logic
as remittance_simulation.py, with a fixed random seed (42) for
reproducibility.

Output: results are printed to console AND written to
robustness_variation_results.txt.
"""

import networkx as nx
import numpy as np

np.random.seed(42)  # fixed for reproducibility of reported results


# ============================================================
# 1. MODEL DEFINITION (identical to remittance_simulation.py)
# ============================================================

def create_scenario(name, description, transfer_amount, nodes, edges):
    G = nx.DiGraph()
    G.graph['name'] = name
    G.graph['description'] = description
    G.graph['transfer_amount'] = transfer_amount
    for node_id, node_data in nodes.items():
        G.add_node(node_id, **node_data)
    for (src, dst), edge_data in edges.items():
        G.add_edge(src, dst, **edge_data)
    return G


def calculate_outcomes(G):
    amount = G.graph['transfer_amount']
    total_fee_pct = total_fee_flat = total_fx = total_time = 0
    effective_access = 1.0
    path = list(nx.topological_sort(G))
    for i in range(len(path) - 1):
        src, dst = path[i], path[i + 1]
        if G.has_edge(src, dst):
            edge = G[src][dst]
            total_fee_pct += edge.get('fee_pct', 0)
            total_fee_flat += edge.get('fee_flat', 0)
            total_fx += edge.get('fx_margin', 0)
            total_time += edge.get('time_hours', 0)
            effective_access *= edge.get('access_prob', 1.0)
    pct_cost = (total_fee_pct + total_fx) * amount
    total_cost = pct_cost + total_fee_flat
    return {
        'total_cost_pct': (total_cost / amount) * 100,
        'total_time_hours': total_time,
        'effective_access_pct': effective_access * 100,
    }


# ============================================================
# 2. CHANNEL DEFINITIONS (identical parameters to remittance_simulation.py)
# ============================================================

def build_cash_adla(amount):
    nodes = {n: {} for n in ['sender', 'adla_in', 'adla_network', 'agent_out', 'recipient']}
    edges = {
        ('sender', 'adla_in'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.5, 'access_prob': 0.60},
        ('adla_in', 'adla_network'): {'fee_pct': 0.087, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.25, 'access_prob': 1.0},
        ('adla_network', 'agent_out'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0027, 'time_hours': 2.0, 'access_prob': 1.0},
        ('agent_out', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 1.0, 'access_prob': 1.0},
    }
    return create_scenario('Cash ADLA', '', amount, nodes, edges)


def build_bank(amount):
    nodes = {n: {} for n in ['sender', 'sa_bank', 'correspondent', 'receiver_bank', 'recipient']}
    edges = {
        ('sender', 'sa_bank'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.5, 'access_prob': 0.15},
        ('sa_bank', 'correspondent'): {'fee_pct': 0.005, 'fee_flat': 7.10, 'fx_margin': 0.0, 'time_hours': 24.0, 'access_prob': 1.0},
        ('correspondent', 'receiver_bank'): {'fee_pct': 0.022, 'fee_flat': 3.50, 'fx_margin': 0.0157, 'time_hours': 12.0, 'access_prob': 1.0},
        ('receiver_bank', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 2.00, 'fx_margin': 0.0, 'time_hours': 1.0, 'access_prob': 1.0},
    }
    return create_scenario('Bank', '', amount, nodes, edges)


def build_digital_adla(amount):
    nodes = {n: {} for n in ['sender', 'sender_wallet', 'payment_network', 'receiver_wallet', 'recipient']}
    edges = {
        ('sender', 'sender_wallet'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.1, 'access_prob': 0.40},
        ('sender_wallet', 'payment_network'): {'fee_pct': 0.0275, 'fee_flat': 0.0, 'fx_margin': 0.0322, 'time_hours': 0.25, 'access_prob': 1.0},
        ('payment_network', 'receiver_wallet'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.25, 'access_prob': 1.0},
        ('receiver_wallet', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 0.50, 'fx_margin': 0.0, 'time_hours': 0.1, 'access_prob': 1.0},
    }
    return create_scenario('Digital ADLA', '', amount, nodes, edges)


def build_tcib(amount):
    nodes = {n: {} for n in ['sender', 'sender_bank', 'tcib_clearing', 'receiver_provider', 'recipient']}
    edges = {
        ('sender', 'sender_bank'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.25, 'access_prob': 0.25},
        ('sender_bank', 'tcib_clearing'): {'fee_pct': 0.015, 'fee_flat': 0.10, 'fx_margin': 0.012, 'time_hours': 0.017, 'access_prob': 1.0},
        ('tcib_clearing', 'receiver_provider'): {'fee_pct': 0.005, 'fee_flat': 0.50, 'fx_margin': 0.0, 'time_hours': 0.1, 'access_prob': 1.0},
        ('receiver_provider', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 1.00, 'fx_margin': 0.0, 'time_hours': 0.5, 'access_prob': 1.0},
    }
    return create_scenario('TCIB', '', amount, nodes, edges)


def build_blockchain(amount):
    nodes = {n: {} for n in ['sender', 'crypto_platform', 'blockchain', 'payout_partner', 'recipient']}
    edges = {
        ('sender', 'crypto_platform'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.25, 'access_prob': 0.20},
        ('crypto_platform', 'blockchain'): {'fee_pct': 0.02, 'fee_flat': 0.50, 'fx_margin': 0.015, 'time_hours': 0.1, 'access_prob': 1.0},
        ('blockchain', 'payout_partner'): {'fee_pct': 0.01, 'fee_flat': 0.50, 'fx_margin': 0.01, 'time_hours': 0.25, 'access_prob': 1.0},
        ('payout_partner', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 1.00, 'fx_margin': 0.0, 'time_hours': 0.5, 'access_prob': 1.0},
    }
    return create_scenario('Blockchain', '', amount, nodes, edges)


def build_combined(amount):
    nodes = {n: {} for n in ['sender', 'mobile_entry', 'tcib_clearing', 'receiver_wallet', 'recipient']}
    edges = {
        ('sender', 'mobile_entry'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.1, 'access_prob': 0.70},
        ('mobile_entry', 'tcib_clearing'): {'fee_pct': 0.012, 'fee_flat': 0.10, 'fx_margin': 0.01, 'time_hours': 0.017, 'access_prob': 1.0},
        ('tcib_clearing', 'receiver_wallet'): {'fee_pct': 0.005, 'fee_flat': 0.0, 'fx_margin': 0.0, 'time_hours': 0.1, 'access_prob': 1.0},
        ('receiver_wallet', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 0.25, 'fx_margin': 0.0, 'time_hours': 0.1, 'access_prob': 1.0},
    }
    return create_scenario('Combined', '', amount, nodes, edges)


CHANNELS = {
    'Cash ADLA': build_cash_adla,
    'Bank': build_bank,
    'Digital ADLA': build_digital_adla,
    'TCIB': build_tcib,
    'Blockchain': build_blockchain,
    'Combined': build_combined,
}
TRANSFER_AMOUNTS = [50, 200, 500]

# Variation levels: +/-20% retained for comparability with the original
# single-level analysis, then +/-50% and +/-100% to test whether Combined's
# dominance holds under progressively wider parameter uncertainty.
VARIATION_LEVELS = [0.20, 0.50, 1.00]


# ============================================================
# 3. COST (MEAN +/- SE) ANALYSIS AT A GIVEN VARIATION LEVEL
# ============================================================

def run_monte_carlo_at_variation(variation, n_trials=1000):
    """
    Run the cost/time/access Monte Carlo (mean +/- SE) test at a specified
    +/- variation level. Mirrors remittance_simulation.py's run_monte_carlo,
    parameterised by variation instead of a fixed 0.8-1.2 multiplier range.
    """
    low, high = max(0.0, 1 - variation), 1 + variation
    all_results = {}

    for amount in TRANSFER_AMOUNTS:
        all_results[amount] = {}
        for name, builder in CHANNELS.items():
            costs, times, access = [], [], []
            for _ in range(n_trials):
                G = builder(amount)
                for u, v, data in G.edges(data=True):
                    for param in ['fee_pct', 'fee_flat', 'fx_margin', 'time_hours']:
                        if data.get(param, 0) > 0:
                            data[param] *= np.random.uniform(low, high)
                    if data.get('access_prob', 1.0) < 1.0:
                        mult = np.random.uniform(low, high)
                        data['access_prob'] = min(max(data['access_prob'] * mult, 0.0), 1.0)
                outcome = calculate_outcomes(G)
                costs.append(outcome['total_cost_pct'])
                times.append(outcome['total_time_hours'])
                access.append(outcome['effective_access_pct'])
            n = len(costs)
            all_results[amount][name] = {
                'cost_mean': round(np.mean(costs), 2),
                'cost_se': round(np.std(costs) / np.sqrt(n), 3),
                'time_mean': round(np.mean(times), 2),
                'time_se': round(np.std(times) / np.sqrt(n), 3),
                'access_mean': round(np.mean(access), 2),
                'access_se': round(np.std(access) / np.sqrt(n), 3),
            }
    return all_results


# ============================================================
# 4. RANKING ANALYSIS AT A GIVEN VARIATION LEVEL
# ============================================================

def run_ranking_at_variation(variation, n_trials=1000):
    """
    Run the ranking-robustness test at a specified +/- variation level.
    variation=0.20 reproduces the main simulation's +/-20% test;
    variation=1.00 tests +/-100% (multiplier range 0.0-2.0, clipped at 0).
    """
    low, high = max(0.0, 1 - variation), 1 + variation
    rankings = {}

    for amount in TRANSFER_AMOUNTS:
        rankings[amount] = {name: {'best_cost': 0, 'best_time': 0, 'best_access': 0}
                             for name in CHANNELS}

        for _ in range(n_trials):
            trial_results = {}
            for name, builder in CHANNELS.items():
                G = builder(amount)
                for u, v, data in G.edges(data=True):
                    for param in ['fee_pct', 'fee_flat', 'fx_margin', 'time_hours']:
                        if data.get(param, 0) > 0:
                            data[param] *= np.random.uniform(low, high)
                    if data.get('access_prob', 1.0) < 1.0:
                        mult = np.random.uniform(low, high)
                        data['access_prob'] = min(max(data['access_prob'] * mult, 0.0), 1.0)
                trial_results[name] = calculate_outcomes(G)

            best_cost = min(trial_results, key=lambda x: trial_results[x]['total_cost_pct'])
            best_time = min(trial_results, key=lambda x: trial_results[x]['total_time_hours'])
            best_access = max(trial_results, key=lambda x: trial_results[x]['effective_access_pct'])

            rankings[amount][best_cost]['best_cost'] += 1
            rankings[amount][best_time]['best_time'] += 1
            rankings[amount][best_access]['best_access'] += 1

        for name in rankings[amount]:
            for key in rankings[amount][name]:
                rankings[amount][name][key] = round(
                    rankings[amount][name][key] / n_trials * 100, 1)

    return rankings


# ============================================================
# 4. MAIN EXECUTION — run across all variation levels, write results
# ============================================================

def main():
    lines = []

    def out(text=''):
        print(text)
        lines.append(text)

    out("=" * 100)
    out("MONTE CARLO ROBUSTNESS ACROSS THREE PARAMETER VARIATION LEVELS")
    out("ECO5016W Minor Dissertation - Kerry-Lynn Whyte (WHYKER001)")
    out(f"Variation levels tested: {[f'+/-{int(v*100)}%' for v in VARIATION_LEVELS]}")
    out(f"n_trials = 1000 per variation level per transfer amount, seed = 42")
    out("=" * 100)

    all_mc = {}
    all_rankings = {}

    # ---- PART 1: Cost (mean +/- SE) subtable at each variation level ----
    out()
    out("#" * 100)
    out("PART 1: COST (%) BY CHANNEL AND TRANSFER AMOUNT, MEAN +/- SE")
    out("(subtable per variation level -- cf. Table 3 in the dissertation)")
    out("#" * 100)

    for var in VARIATION_LEVELS:
        mc = run_monte_carlo_at_variation(var, n_trials=1000)
        all_mc[var] = mc

        out()
        out(f"--- Variation: +/-{int(var*100)}% ---")
        out(f"{'Channel':<14} {'$50':>16} {'$200':>16} {'$500':>16}")
        out("-" * 64)
        for name in CHANNELS:
            row = f"{name:<14}"
            for amount in TRANSFER_AMOUNTS:
                r = mc[amount][name]
                row += f" {r['cost_mean']:>6.1f} +/- {r['cost_se']:<6.2f}"
            out(row)

    # ---- PART 2: Ranking subtable at each variation level ----
    out()
    out("#" * 100)
    out("PART 2: RANKING ROBUSTNESS -- % OF 1,000 TRIALS EACH CHANNEL RANKS BEST")
    out("(subtable per variation level -- cf. Table 4 in the dissertation)")
    out("#" * 100)

    for var in VARIATION_LEVELS:
        rankings = run_ranking_at_variation(var, n_trials=1000)
        all_rankings[var] = rankings

        out()
        out(f"--- Variation: +/-{int(var*100)}% ---")
        out(f"{'':>14} {'Best cost':^18} {'Best efficiency':^22} {'Best access':^18}")
        out(f"{'Amount':<14} {'Combined':>9} {'TCIB':>8} {'Combined':>9} {'Top alt.':>12} {'Combined':>9} {'Cash ADLA':>8}")
        out("-" * 90)
        for amount in TRANSFER_AMOUNTS:
            r = rankings[amount]
            # identify the actual top non-Combined competitor on efficiency, by name
            others_time = {k: v['best_time'] for k, v in r.items() if k != 'Combined'}
            top_time_alt = max(others_time, key=others_time.get)
            top_time_val = others_time[top_time_alt]
            top_time_label = f"{top_time_alt} {top_time_val:.1f}%" if top_time_val > 0 else "-- 0.0%"
            out(f"{'$'+str(amount):<14} "
                f"{r['Combined']['best_cost']:>8.1f}% {r['TCIB']['best_cost']:>7.1f}% "
                f"{r['Combined']['best_time']:>8.1f}% {top_time_label:>12} "
                f"{r['Combined']['best_access']:>8.1f}% {r['Cash ADLA']['best_access']:>7.1f}%")

    # ---- PART 2b: full per-channel efficiency breakdown at widest variation ----
    widest = max(VARIATION_LEVELS)
    out()
    out(f"--- Full efficiency win-share breakdown, all channels, +/-{int(widest*100)}% variation ---")
    out(f"{'Channel':<14} {'$50':>10} {'$200':>10} {'$500':>10}")
    out("-" * 46)
    for name in CHANNELS:
        row = f"{name:<14}"
        for amount in TRANSFER_AMOUNTS:
            row += f" {all_rankings[widest][amount][name]['best_time']:>9.1f}%"
        out(row)

    # ---- PART 3: Interpretation ----
    out()

    c50_200 = all_rankings[0.50][200]['Combined']['best_cost']
    c100_200 = all_rankings[1.00][200]['Combined']['best_cost']
    a20_200 = all_rankings[0.20][200]['Combined']['best_access']
    a100_200 = all_rankings[1.00][200]['Combined']['best_access']

  
    out()
    

    with open('robustness_variation_results.txt', 'w') as f:
        f.write('\n'.join(lines))

    print("\nResults written to robustness_variation_results.txt")

    return all_mc, all_rankings


if __name__ == '__main__':
    all_mc, all_rankings = main()