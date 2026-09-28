"""
Parametric Graph-Based Simulation of the SA-SADC Remittance Corridor
=====================================================================
ECO5016W — Minor Dissertation in FinTech
University of Cape Town

Author: Kerry-Lynn Whyte (WHYKER001)
Supervisor: Allan Davids

Compares six payment architectures across three transfer sizes ($50, $200, $500):
    1. Cash-based ADLA (Mukuru)
    2. Bank transfer
    3. Digital ADLA (Sikhona / Mama Money)
    4. TCIB-enabled transfer
    5. Blockchain (Yellow Card)
    6. Combined architecture (tiered eKYC + non-bank TCIB + mobile wallet payout)

Parameters calibrated from:
    - FinMark Trust (2024) — mystery shopping data, access estimates
    - AfricaNenda (2022) — TCIB clearing fee
    - Srinivasan et al. (2025) — corridor cost benchmarks
    - Brandi et al. (2025) — FX margin data
    - DiCaprio et al. (2025) — processing time data
    - TechCentral (2024) — TCIB clearing speed (SA-Zambia corridor)
    - CNBC / Sigalos (2023) — blockchain network fee data

This single script produces:
    1. Deterministic results (no randomness) for all channels/amounts.
    2. Monte Carlo cost/time/access results (mean +/- SE) at the primary
       +/-20% parameter variation, matching Table 3 in the dissertation.
    3. Ranking-robustness results (% of trials each channel ranks best)
       at the primary +/-20% variation, matching Table 4.
    4. An extended robustness analysis repeating (2) and (3) at +/-50%
       and +/-100% variation, to test whether the primary result depends
       on the narrower +/-20% assumption (Section 3.3 of the dissertation).
    5. Inline figures (dynamic pricing, channel comparison at $50/$200/$500,
       cost-by-amount) matching the dissertation's Figures 2-3.

A fixed random seed (42) is set once, below, for full reproducibility of
every reported result. All console output is also written to
simulation_results.txt.
"""

import networkx as nx
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

np.random.seed(42)  # fixed once, for reproducibility of all reported results


# ============================================================
# 1. MODEL DEFINITION
# ============================================================

def create_scenario(name, description, transfer_amount, nodes, edges):
    """Create a scenario as a directed graph with parameterised edges."""
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
    """
    Calculate total cost, time, and access for a scenario.
    Cost = sum of (fee_pct * amount + fee_flat + fx_margin * amount) across hops
    Time = sum of time_hours across hops
    Access = product of access_prob across edges (first-mile access dominates,
             since all downstream edges have access_prob = 1.0)
    """
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
    total_cost_pct = (total_cost / amount) * 100
    effective_access_pct = effective_access * 100

    return {
        'scenario': G.graph['name'],
        'transfer_amount': amount,
        'total_cost_usd': round(total_cost, 2),
        'total_cost_pct': round(total_cost_pct, 2),
        'total_time_hours': round(total_time, 2),
        'effective_access_pct': round(effective_access_pct, 2),
    }


# ============================================================
# 2. CHANNEL DEFINITIONS
# ============================================================

def build_cash_adla(amount):
    """
    Cash-based ADLA (e.g. Mukuru) — BASELINE
    Sourced: FinMark Trust (2024) Tables 11/12/18 (fee, FX, time); Lite KYC access.
    """
    nodes = {
        'sender': {'label': 'Sender'}, 'adla_in': {'label': 'Mukuru Booth'},
        'adla_network': {'label': 'ADLA Network'}, 'agent_out': {'label': 'Mukuru Agent'},
        'recipient': {'label': 'Recipient'}
    }
    edges = {
        ('sender', 'adla_in'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                 'time_hours': 0.5, 'access_prob': 0.60,
                                 'label': 'Cash deposit + Lite KYC'},
        ('adla_in', 'adla_network'): {'fee_pct': 0.087, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                       'time_hours': 0.25, 'access_prob': 1.0,
                                       'label': 'Internal processing'},
        ('adla_network', 'agent_out'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0027,
                                         'time_hours': 2.0, 'access_prob': 1.0,
                                         'label': 'Cross-border transfer'},
        ('agent_out', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                      'time_hours': 1.0, 'access_prob': 1.0,
                                      'label': 'Cash collection'},
    }
    return create_scenario('Cash ADLA', 'Cash-based ADLA (Mukuru)', amount, nodes, edges)


def build_bank(amount):
    """
    Bank transfer — Authorised Dealer channel.
    Sourced: FinMark Trust (2024) fee schedule, median SWIFT fee; DiCaprio et al. (2025) timing.
    """
    nodes = {
        'sender': {'label': 'Sender'}, 'sa_bank': {'label': 'SA Bank'},
        'correspondent': {'label': 'Correspondent Bank'}, 'receiver_bank': {'label': 'Receiver Bank'},
        'recipient': {'label': 'Recipient'}
    }
    edges = {
        ('sender', 'sa_bank'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                 'time_hours': 0.5, 'access_prob': 0.15,
                                 'label': 'Full KYC verification'},
        ('sa_bank', 'correspondent'): {'fee_pct': 0.005, 'fee_flat': 7.10, 'fx_margin': 0.0,
                                        'time_hours': 24.0, 'access_prob': 1.0,
                                        'label': 'SWIFT instruction'},
        ('correspondent', 'receiver_bank'): {'fee_pct': 0.022, 'fee_flat': 3.50, 'fx_margin': 0.0157,
                                              'time_hours': 12.0, 'access_prob': 1.0,
                                              'label': 'FX conversion + settlement'},
        ('receiver_bank', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 2.00, 'fx_margin': 0.0,
                                          'time_hours': 1.0, 'access_prob': 1.0,
                                          'label': 'Bank withdrawal'},
    }
    return create_scenario('Bank', 'Bank via correspondent banking', amount, nodes, edges)


def build_digital_adla(amount):
    """
    Digital ADLA (Sikhona / Mama Money).
    Sourced: FinMark Trust (2024) Tables 11/12; Arnt et al. (2025) ecosystem context.
    """
    nodes = {
        'sender': {'label': 'Sender'}, 'sender_wallet': {'label': 'SA Mobile Wallet'},
        'payment_network': {'label': 'Payment Network'}, 'receiver_wallet': {'label': 'EcoCash Wallet'},
        'recipient': {'label': 'Recipient'}
    }
    edges = {
        ('sender', 'sender_wallet'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                       'time_hours': 0.1, 'access_prob': 0.40,
                                       'label': 'Mobile KYC + wallet load'},
        ('sender_wallet', 'payment_network'): {'fee_pct': 0.0275, 'fee_flat': 0.0, 'fx_margin': 0.0322,
                                                'time_hours': 0.25, 'access_prob': 1.0,
                                                'label': 'Cross-border routing'},
        ('payment_network', 'receiver_wallet'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                                  'time_hours': 0.25, 'access_prob': 1.0,
                                                  'label': 'Mobile money credit'},
        ('receiver_wallet', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 0.50, 'fx_margin': 0.0,
                                            'time_hours': 0.1, 'access_prob': 1.0,
                                            'label': 'Wallet receipt / cash-out'},
    }
    return create_scenario('Digital ADLA', 'Mobile wallet to mobile money', amount, nodes, edges)


def build_tcib(amount):
    """
    TCIB — Transactions Cleared on an Immediate Basis.
    Sourced: AfricaNenda (2022) clearing fee; TechCentral (2024) 60s clearing.
    """
    nodes = {
        'sender': {'label': 'Sender'}, 'sender_bank': {'label': 'TCIB Participant'},
        'tcib_clearing': {'label': 'TCIB Clearing'}, 'receiver_provider': {'label': 'Receiver Provider'},
        'recipient': {'label': 'Recipient'}
    }
    edges = {
        ('sender', 'sender_bank'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                     'time_hours': 0.25, 'access_prob': 0.25,
                                     'label': 'Account verification'},
        ('sender_bank', 'tcib_clearing'): {'fee_pct': 0.015, 'fee_flat': 0.10, 'fx_margin': 0.012,
                                            'time_hours': 0.017, 'access_prob': 1.0,
                                            'label': 'TCIB instant clearing'},
        ('tcib_clearing', 'receiver_provider'): {'fee_pct': 0.005, 'fee_flat': 0.50, 'fx_margin': 0.0,
                                                  'time_hours': 0.1, 'access_prob': 1.0,
                                                  'label': 'Settlement to receiver'},
        ('receiver_provider', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 1.00, 'fx_margin': 0.0,
                                              'time_hours': 0.5, 'access_prob': 1.0,
                                              'label': 'Fund collection'},
    }
    return create_scenario('TCIB', 'TCIB instant clearing', amount, nodes, edges)


def build_blockchain(amount):
    """
    Blockchain — Yellow Card cryptocurrency remittance service.
    Sourced: CNBC/Sigalos (2023) network fee context; Brandi et al. (2025) liquidity risk.
    """
    nodes = {
        'sender': {'label': 'Sender'}, 'crypto_platform': {'label': 'Yellow Card'},
        'blockchain': {'label': 'Blockchain Settlement'}, 'payout_partner': {'label': 'Payout Partner'},
        'recipient': {'label': 'Recipient'}
    }
    edges = {
        ('sender', 'crypto_platform'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                         'time_hours': 0.25, 'access_prob': 0.20,
                                         'label': 'App onboarding + KYC'},
        ('crypto_platform', 'blockchain'): {'fee_pct': 0.02, 'fee_flat': 0.50, 'fx_margin': 0.015,
                                             'time_hours': 0.1, 'access_prob': 1.0,
                                             'label': 'Crypto purchase + transfer'},
        ('blockchain', 'payout_partner'): {'fee_pct': 0.01, 'fee_flat': 0.50, 'fx_margin': 0.01,
                                            'time_hours': 0.25, 'access_prob': 1.0,
                                            'label': 'Crypto to local currency'},
        ('payout_partner', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 1.00, 'fx_margin': 0.0,
                                           'time_hours': 0.5, 'access_prob': 1.0,
                                           'label': 'Cash-out / mobile credit'},
    }
    return create_scenario('Blockchain', 'Yellow Card, bypasses intermediaries', amount, nodes, edges)


def build_combined(amount):
    """
    Combined: tiered eKYC + non-bank TCIB participation + mobile wallet payout.
    Tests interventions "in combination" per the research question.
    """
    nodes = {
        'sender': {'label': 'Sender'}, 'mobile_entry': {'label': 'Mobile Wallet'},
        'tcib_clearing': {'label': 'TCIB Clearing'}, 'receiver_wallet': {'label': 'EcoCash Wallet'},
        'recipient': {'label': 'Recipient'}
    }
    edges = {
        ('sender', 'mobile_entry'): {'fee_pct': 0.0, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                      'time_hours': 0.1, 'access_prob': 0.70,
                                      'label': 'Tiered KYC + mobile wallet'},
        ('mobile_entry', 'tcib_clearing'): {'fee_pct': 0.012, 'fee_flat': 0.10, 'fx_margin': 0.01,
                                             'time_hours': 0.017, 'access_prob': 1.0,
                                             'label': 'Direct TCIB clearing (no sponsor bank)'},
        ('tcib_clearing', 'receiver_wallet'): {'fee_pct': 0.005, 'fee_flat': 0.0, 'fx_margin': 0.0,
                                                'time_hours': 0.1, 'access_prob': 1.0,
                                                'label': 'Mobile money credit'},
        ('receiver_wallet', 'recipient'): {'fee_pct': 0.0, 'fee_flat': 0.25, 'fx_margin': 0.0,
                                            'time_hours': 0.1, 'access_prob': 1.0,
                                            'label': 'Wallet receipt'},
    }
    return create_scenario('Combined', 'TCIB + mobile money + tiered KYC', amount, nodes, edges)


CHANNELS = {
    'Cash ADLA': build_cash_adla, 'Bank': build_bank, 'Digital ADLA': build_digital_adla,
    'TCIB': build_tcib, 'Blockchain': build_blockchain, 'Combined': build_combined,
}
TRANSFER_AMOUNTS = [50, 200, 500]

# +/-20% is the primary variation level (Table 3/4). +/-50% and +/-100% extend
# the robustness check (Section 3.3) to test whether the primary result depends
# on this specific, relatively narrow assumption. +/-100% is a deliberately
# extreme stress test, not a realistic estimate of parameter uncertainty.
PRIMARY_VARIATION = 0.20
EXTENDED_VARIATION_LEVELS = [0.20, 0.50, 1.00]


# ============================================================
# 3. DETERMINISTIC (NO RANDOMNESS) RESULTS
# ============================================================

def run_dynamic_pricing():
    """Deterministic cost/time/access for each channel at each amount (no variation applied)."""
    results = {}
    for amount in TRANSFER_AMOUNTS:
        results[amount] = {name: calculate_outcomes(builder(amount))
                            for name, builder in CHANNELS.items()}
    return results


# ============================================================
# 4. MONTE CARLO (MEAN +/- SE), PARAMETERISED BY VARIATION LEVEL
# ============================================================

def run_monte_carlo(variation=PRIMARY_VARIATION, n_trials=1000):
    """
    Vary all edge parameters by a uniform random factor of +/-variation,
    independently per parameter per trial. Report mean +/- SE per channel
    per amount. variation=0.20 reproduces the primary +/-20% analysis;
    variation=0.50/1.00 extend it for the robustness check.

    The seed is reset at the start of this function so that each call
    (i.e. each variation level) draws from the same starting random
    state, matching the reproducibility approach used to generate the
    reported dissertation results.
    """
    np.random.seed(42)
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
                'cost_mean': round(np.mean(costs), 2), 'cost_se': round(np.std(costs) / np.sqrt(n), 3),
                'time_mean': round(np.mean(times), 2), 'time_se': round(np.std(times) / np.sqrt(n), 3),
                'access_mean': round(np.mean(access), 2), 'access_se': round(np.std(access) / np.sqrt(n), 3),
            }
    return all_results


# ============================================================
# 5. RANKING ROBUSTNESS, PARAMETERISED BY VARIATION LEVEL
# ============================================================

def run_ranking_test(variation=PRIMARY_VARIATION, n_trials=1000):
    """
    For each amount, count how often each channel ranks best on cost,
    efficiency (time), and accessibility across n_trials, at the given
    +/-variation level.

    The seed is reset at the start of this function, matching
    run_monte_carlo's approach, so each call starts from the same
    random state.
    """
    np.random.seed(42)
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
                rankings[amount][name][key] = round(rankings[amount][name][key] / n_trials * 100, 1)
    return rankings


# ============================================================
# 6. VISUALISATION
# ============================================================

COLORS = {
    'Cash ADLA': '#1D9E75', 'Bank': '#30C4D8', 'Digital ADLA': '#378ADD',
    'TCIB': '#CB74D7', 'Blockchain': '#F15BB8', 'Combined': '#F1A15B',
}


def plot_dynamic_pricing(pricing_results):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.patch.set_facecolor('#FAFAF8')
    for idx, amount in enumerate(TRANSFER_AMOUNTS):
        ax = axes[idx]
        channels = list(pricing_results[amount].keys())
        costs = [pricing_results[amount][c]['total_cost_pct'] for c in channels]
        bars = ax.bar(channels, costs, color=[COLORS[c] for c in channels], edgecolor='white', linewidth=1.5)
        ax.set_title(f'${amount} Transfer', fontweight='bold', fontsize=12)
        ax.set_ylabel('Total Cost (%)' if idx == 0 else '')
        ax.axhline(y=3, color="#060606", linestyle='--', linewidth=0.8)
        for bar, val in zip(bars, costs):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                     f'{val:.1f}%', ha='center', fontsize=9, fontweight='bold')
        ax.set_facecolor('#FAFAF8')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='x', rotation=25)
    fig.suptitle('Dynamic Pricing: Cost by Transfer Amount and Channel', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig


def plot_monte_carlo_results(mc_results, amount=200):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.patch.set_facecolor('#FAFAF8')
    channels = list(mc_results[amount].keys())

    means = [mc_results[amount][c]['cost_mean'] for c in channels]
    ses = [mc_results[amount][c]['cost_se'] for c in channels]
    axes[0].bar(channels, means, color=[COLORS[c] for c in channels], edgecolor='white',
                linewidth=1.5, yerr=ses, capsize=4, error_kw={'linewidth': 1.5})
    axes[0].set_title('Cost (%)', fontweight='bold')
    axes[0].set_ylabel(f'Total Cost (% of ${amount})')
    axes[0].axhline(y=3, color="#060606", linestyle='--', linewidth=0.8, label='SDG 3%')
    axes[0].legend(fontsize=8)

    means = [mc_results[amount][c]['time_mean'] for c in channels]
    ses = [mc_results[amount][c]['time_se'] for c in channels]
    axes[1].bar(channels, means, color=[COLORS[c] for c in channels], edgecolor='white',
                linewidth=1.5, yerr=ses, capsize=4, error_kw={'linewidth': 1.5})
    axes[1].set_title('Efficiency (hours)', fontweight='bold')
    axes[1].set_ylabel('Total Time (hours)')

    means = [mc_results[amount][c]['access_mean'] for c in channels]
    ses = [mc_results[amount][c]['access_se'] for c in channels]
    axes[2].bar(channels, means, color=[COLORS[c] for c in channels], edgecolor='white',
                linewidth=1.5, yerr=ses, capsize=4, error_kw={'linewidth': 1.5})
    axes[2].set_title('Accessibility (%)', fontweight='bold')
    axes[2].set_ylabel('Effective Access (%)')
    axes[2].set_ylim(0, 100)

    for ax in axes:
        ax.set_facecolor('#FAFAF8')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='x', rotation=25)
    fig.suptitle(f'Channel Comparison: ${amount} Transfer (mean +/- SE, n=1000)',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig


def plot_cost_by_amount(mc_results):
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#FAFAF8')
    markers = {'Cash ADLA': 'o', 'Bank': 's', 'Digital ADLA': '^', 'TCIB': 'D',
               'Blockchain': 'P', 'Combined': '*'}
    for name in CHANNELS:
        means = [mc_results[a][name]['cost_mean'] for a in TRANSFER_AMOUNTS]
        ses = [mc_results[a][name]['cost_se'] for a in TRANSFER_AMOUNTS]
        ax.errorbar(TRANSFER_AMOUNTS, means, yerr=ses, marker=markers[name], color=COLORS[name],
                     linewidth=2, markersize=8, capsize=4, label=name)
    ax.axhline(y=3, color='#060606', linestyle='--', linewidth=0.8, label='SDG 3%')
    ax.set_xlabel('Transfer Amount (USD)', fontsize=11)
    ax.set_ylabel('Total Cost (%)', fontsize=11)
    ax.set_title('Dynamic Pricing: How Cost Varies with Transfer Amount (mean +/- SE)',
                 fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.set_xticks(TRANSFER_AMOUNTS)
    ax.set_xticklabels(['$50', '$200', '$500'])
    ax.set_facecolor('#FAFAF8')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(alpha=0.2)
    plt.tight_layout()
    return fig


# ============================================================
# 7. MAIN EXECUTION
# ============================================================

def main():
    lines = []

    def out(text=''):
        print(text)
        lines.append(text)

    out("=" * 100)
    out("SA-SADC REMITTANCE CORRIDOR SIMULATION")
    out("ECO5016W Minor Dissertation - Kerry-Lynn Whyte (WHYKER001)")
    out("6 channels x 3 transfer amounts, n_trials=1000 per Monte Carlo test, seed=42")
    out("=" * 100)

    # ---- Part 1: Deterministic results ----
    out()
    out("#" * 100)
    out("PART 1: DETERMINISTIC RESULTS (no parameter variation)")
    out("#" * 100)
    pricing = run_dynamic_pricing()
    for amount in TRANSFER_AMOUNTS:
        out(f"\n--- ${amount} Transfer ---")
        out(f"{'Channel':<14} {'Cost ($)':>10} {'Cost (%)':>10} {'Time (h)':>10} {'Access (%)':>12}")
        out("-" * 58)
        for name in CHANNELS:
            r = pricing[amount][name]
            out(f"{name:<14} {'$'+str(r['total_cost_usd']):>10} {str(r['total_cost_pct'])+'%':>10} "
                f"{r['total_time_hours']:>10} {str(r['effective_access_pct'])+'%':>12}")

    # ---- Part 2: Primary Monte Carlo (+/-20%) — cf. Table 3 ----
    out()
    out("#" * 100)
    out(f"PART 2: PRIMARY MONTE CARLO, +/-{int(PRIMARY_VARIATION*100)}% (cf. Table 3)")
    out("#" * 100)
    mc_primary = run_monte_carlo(PRIMARY_VARIATION, n_trials=1000)
    for amount in TRANSFER_AMOUNTS:
        out(f"\n--- ${amount} Transfer ---")
        out(f"{'Channel':<14} {'Cost (%)':>16} {'Time (h)':>16} {'Access (%)':>16}")
        out("-" * 64)
        for name in CHANNELS:
            r = mc_primary[amount][name]
            out(f"{name:<14} {r['cost_mean']:>6.1f} +/- {r['cost_se']:<6.2f} "
                f"{r['time_mean']:>6.1f} +/- {r['time_se']:<6.2f} "
                f"{r['access_mean']:>6.1f} +/- {r['access_se']:<6.2f}")

    # ---- Part 3: Primary ranking robustness (+/-20%) — cf. Table 4 ----
    out()
    out("#" * 100)
    out(f"PART 3: PRIMARY RANKING ROBUSTNESS, +/-{int(PRIMARY_VARIATION*100)}% (cf. Table 4)")
    out("#" * 100)
    ranking_primary = run_ranking_test(PRIMARY_VARIATION, n_trials=1000)
    for amount in TRANSFER_AMOUNTS:
        out(f"\n--- ${amount} Transfer ---")
        out(f"{'Channel':<14} {'Best Cost':>12} {'Best Time':>12} {'Best Access':>12}")
        out("-" * 52)
        for name in CHANNELS:
            r = ranking_primary[amount][name]
            out(f"{name:<14} {str(r['best_cost'])+'%':>12} {str(r['best_time'])+'%':>12} "
                f"{str(r['best_access'])+'%':>12}")

    # ---- Part 4: Extended robustness across variation levels — cf. Section 3.3 ----
    out()
    out("#" * 100)
    out("PART 4: EXTENDED ROBUSTNESS ACROSS PARAMETER VARIATION LEVELS")
    out("(repeats Parts 2-3 at +/-20%, +/-50%, +/-100% -- cf. Tables 3(a-c)/4(a-c))")
    out("#" * 100)

    all_mc, all_rankings = {}, {}
    for var in EXTENDED_VARIATION_LEVELS:
        all_mc[var] = mc_primary if var == PRIMARY_VARIATION else run_monte_carlo(var, n_trials=1000)
        all_rankings[var] = ranking_primary if var == PRIMARY_VARIATION else run_ranking_test(var, n_trials=1000)

    out()
    out("--- Cost (mean +/- SE) by variation level ---")
    for var in EXTENDED_VARIATION_LEVELS:
        out(f"\n+/-{int(var*100)}%:")
        out(f"{'Channel':<14} {'$50':>16} {'$200':>16} {'$500':>16}")
        out("-" * 64)
        for name in CHANNELS:
            row = f"{name:<14}"
            for amount in TRANSFER_AMOUNTS:
                r = all_mc[var][amount][name]
                row += f" {r['cost_mean']:>6.1f} +/- {r['cost_se']:<6.2f}"
            out(row)

    out()
    out("--- Ranking robustness by variation level (named top alternative competitor) ---")
    for var in EXTENDED_VARIATION_LEVELS:
        out(f"\n+/-{int(var*100)}%:")
        out(f"{'':>14} {'Best cost':^18} {'Best efficiency':^22} {'Best access':^18}")
        out(f"{'Amount':<14} {'Combined':>9} {'TCIB':>8} {'Combined':>9} {'Top alt.':>12} "
            f"{'Combined':>9} {'Cash ADLA':>8}")
        out("-" * 90)
        for amount in TRANSFER_AMOUNTS:
            r = all_rankings[var][amount]
            others_time = {k: v['best_time'] for k, v in r.items() if k != 'Combined'}
            top_time_alt = max(others_time, key=others_time.get)
            top_time_val = others_time[top_time_alt]
            top_time_label = f"{top_time_alt} {top_time_val:.1f}%" if top_time_val > 0 else "-- 0.0%"
            out(f"{'$'+str(amount):<14} "
                f"{r['Combined']['best_cost']:>8.1f}% {r['TCIB']['best_cost']:>7.1f}% "
                f"{r['Combined']['best_time']:>8.1f}% {top_time_label:>12} "
                f"{r['Combined']['best_access']:>8.1f}% {r['Cash ADLA']['best_access']:>7.1f}%")

    widest = max(EXTENDED_VARIATION_LEVELS)
    out()
    out(f"--- Full efficiency win-share breakdown, all channels, +/-{int(widest*100)}% ---")
    out(f"{'Channel':<14} {'$50':>10} {'$200':>10} {'$500':>10}")
    out("-" * 46)
    for name in CHANNELS:
        row = f"{name:<14}"
        for amount in TRANSFER_AMOUNTS:
            row += f" {all_rankings[widest][amount][name]['best_time']:>9.1f}%"
        out(row)

    # ---- Part 5: Figures ----
    out()
    out("Generating figures...")
    plot_dynamic_pricing(pricing).savefig('dynamic_pricing.png', dpi=200, bbox_inches='tight', facecolor='#FAFAF8')
    plot_monte_carlo_results(mc_primary, 200).savefig('monte_carlo_200.png', dpi=200, bbox_inches='tight', facecolor='#FAFAF8')
    plot_monte_carlo_results(mc_primary, 50).savefig('monte_carlo_50.png', dpi=200, bbox_inches='tight', facecolor='#FAFAF8')
    plot_monte_carlo_results(mc_primary, 500).savefig('monte_carlo_500.png', dpi=200, bbox_inches='tight', facecolor='#FAFAF8')
    plot_cost_by_amount(mc_primary).savefig('cost_by_amount.png', dpi=200, bbox_inches='tight', facecolor='#FAFAF8')
    out("Figures saved: dynamic_pricing.png, monte_carlo_50/200/500.png, cost_by_amount.png")

    with open('simulation_results.txt', 'w') as f:
        f.write('\n'.join(lines))
    print("\nFull results written to simulation_results.txt")

    return pricing, mc_primary, ranking_primary, all_mc, all_rankings


if __name__ == '__main__':
    pricing, mc, rankings, all_mc, all_rankings = main()