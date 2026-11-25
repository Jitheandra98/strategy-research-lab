# Strategy Research Lab

Pre-registered backtests of **5,668 trading-rule variants** on 2012–2026 gold futures data. None passed. This repository holds the code and the write-ups; the market data is licensed and is not included.

## How every idea was tested

1. A spec written before any result (`SPEC.md` or a pre-registration file in the study's folder).
2. A chronological split: develop on older data, judge the newer data once.
3. The same rules run on random entries, as a luck check.
4. The idea logged in [IDEA_LEDGER.md](IDEA_LEDGER.md). The bar it must clear rises with the number of ideas tried: 1,000 rules with no edge would still give about 23 with t ≥ 2.
5. Only then a paper-account gate ([studies/paper_account_2026-11-09](studies/paper_account_2026-11-09)).

## Engines

| Engine | Where | What it does |
|---|---|---|
| Fixed-exit search | [studies/fixed_exit_search_2026-11-09](studies/fixed_exit_search_2026-11-09) | Numba engine that tests 1,764 entry strategies with one stop/target in about 22 seconds |
| Structure × exits grid | [studies/structure_exits_2026-11-09](studies/structure_exits_2026-11-09) | 2,880 market-structure entry × stop × exit combinations on 5m to 4h |
| Paper account | [studies/paper_account_2026-11-09](studies/paper_account_2026-11-09) | 1% risk sizing, a daily loss halt, a drawdown freeze and Monte Carlo reshuffles of trade order |
| Order-block / FVG port | [studies/tokyo_obfvg_2026-11-08](studies/tokyo_obfvg_2026-11-08) | `qf_zones.py`, a Python port of a TradingView order-block and fair-value-gap indicator |

## Main results

| Study | Variants | Result |
|---|---|---|
| Market-structure entries × stops × exits | 2,880 | 0 of 10 finalists pass. The target changes the win rate, not the result; 5m fees cost about 0.3R a trade |
| Fixed $250 stop / $100 target × standard entry toolkit | 1,764 | 0 pass. The closest rule lost $890 on unseen weeks |
| 5m spike scalps (targets, stops, holds, sessions) | 672 | 0 of 432 profitable; random entries did as well. No bigger target fixes it |
| $1–3 scalps at levels and times | 168 + grid | 0 positive in both years; a 96% win rate came with a profit factor of 0.6 |
| 100-setup catalog + range breakout | 48 | 0 pass; coin flips before costs |
| The opposite of every losing rule | 78 | 0 pass; fees are paid both ways |
| US stock factors, 1926–2026 | 7 | Only owning the market works; all 6 published factors faded after publication |
| Trend following on 38 futures, 1981–2026 | 2 | Sharpe 0.83 over the full sample, 0.39 after publication: fails narrowly |
| Audit of a TradingView "institutional" indicator | 2 | Its dashboard claimed profit factor 16.68; as coded, 2 of 3 signals never fire and the rest lose |

Real but too small to trade at one micro contract: the evening reopen drift (+0.42 pt a day), morning momentum into the 13:30 close (t 4.8) and following morning spikes (+$1–2 a trade). Each is about the size of the $3–5 round-trip cost. Every row is in [IDEA_LEDGER.md](IDEA_LEDGER.md), with its folder.

## Layout

- `IDEA_LEDGER.md`: every idea tested, with its folder, variant count and result
- `studies/<name>/`: one folder per study, with its scripts, spec and report
- Scripts point at data paths on the machine they were written on; the data itself is not in this repository

## About

Built by Jitheandra Subramaniam with AI coding agents (Claude Code), directed and reviewed by me. Part of my portfolio: [github.com/Jitheandra98](https://github.com/Jitheandra98).

© 2026 Jitheandra Subramaniam. All rights reserved. This code is shared for viewing; no license to copy, modify or redistribute it is granted.
