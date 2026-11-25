# Station First-Touch quant report — `unknown_30m_5174bars`

This is a frozen research run. It does not prove profitability, identify institutional inventory, or reconstruct broker fills.
The feed is kept separate because its provenance is unknown.

## Data audit

- Source: `/Users/jitheandrasubramaniam/Desktop/hey hey/recorder_data/recorder_30m_5174bars.json`
- SHA-256: `44b48221f997d32e632abb8271ea0755a3c930c4c51b5bb50bdb6ec6356ef1b1`
- Rows: **5174**; LTF step: **1800 seconds**
- Observed range: **1769722200 → 1785825000 UTC seconds**
- Missing LTF buckets: **3773** across **135** gaps; max gap **460800 seconds**
- Complete synthetic 4H buckets: **555**; partial: **158**
- Zones/events/visits: **116 / 532 / 263**

## Frozen selection

- Result: **NO_MODEL_SELECTED**
- Selected config: **none**
- Validation selection requires at least 10 uncensored trades, positive expectancy at 1 point cost, and a positive lower block-bootstrap CI.
- Holdout is not used to select a model.

## First touch versus repeat

- holdout / repeat / short: n=8 evaluable at 8h, median MFE=2.038 ATR, mean terminal=-1.111 ATR.
- holdout / repeat / long: n=1 evaluable at 8h, median MFE=0.704 ATR, mean terminal=-2.552 ATR.
- holdout / first / short: n=3 evaluable at 8h, median MFE=1.521 ATR, mean terminal=0.584 ATR.
- holdout / first / long: n=5 evaluable at 8h, median MFE=1.834 ATR, mean terminal=0.123 ATR.
- train / repeat / short: n=18 evaluable at 8h, median MFE=2.128 ATR, mean terminal=0.597 ATR.
- train / repeat / long: n=13 evaluable at 8h, median MFE=1.573 ATR, mean terminal=-0.610 ATR.
- train / first / short: n=9 evaluable at 8h, median MFE=2.221 ATR, mean terminal=0.940 ATR.
- train / first / long: n=10 evaluable at 8h, median MFE=2.872 ATR, mean terminal=0.285 ATR.
- validation / repeat / short: n=6 evaluable at 8h, median MFE=2.798 ATR, mean terminal=1.505 ATR.
- validation / repeat / long: n=2 evaluable at 8h, median MFE=5.903 ATR, mean terminal=4.900 ATR.
- validation / first / short: n=5 evaluable at 8h, median MFE=5.833 ATR, mean terminal=1.410 ATR.
- validation / first / long: n=2 evaluable at 8h, median MFE=1.304 ATR, mean terminal=-0.844 ATR.

## Model metrics at 1 point cost

| Split | Config | n | uncensored | expectancy (R) | win rate | PF | max DD (R) | bootstrap CI |
|---|---|---:|---:|---:|---:|---:|---:|---|
| train | FT_LIMIT__ZONE_2R | 22 | 12 | -0.237 | 0.417 | 0.577 | 2.846 | [-0.689, 0.302] |
| train | FT_LIMIT__ATR_1_5R | 22 | 12 | 0.190 | 0.500 | 1.357 | 2.810 | [-0.436, 0.851] |
| train | REPEAT_LIMIT__ZONE_2R | 31 | 20 | -0.475 | 0.250 | 0.366 | 9.496 | [-0.876, 0.032] |
| train | REPEAT_LIMIT__ATR_1_5R | 33 | 22 | -0.380 | 0.273 | 0.508 | 9.117 | [-0.862, 0.189] |
| train | FT_RECLAIM__ZONE_2R | 22 | 12 | -0.210 | 0.333 | 0.586 | 4.050 | [-0.675, 0.385] |
| train | FT_RECLAIM__ATR_1_5R | 22 | 12 | -0.011 | 0.417 | 0.982 | 3.203 | [-0.742, 0.684] |
| train | FLIP_LIMIT__ZONE_2R | 29 | 20 | -0.222 | 0.350 | 0.653 | 9.456 | [-0.674, 0.329] |
| train | FLIP_LIMIT__ATR_1_5R | 29 | 20 | -0.049 | 0.400 | 0.921 | 6.399 | [-0.542, 0.481] |
| train | FT_LIMIT_EMA50__ZONE_2R | 11 | 4 | -0.898 | 0.000 | 0.000 | 3.590 | — |
| train | FT_LIMIT_EMA50__ATR_1_5R | 11 | 4 | -1.064 | 0.000 | 0.000 | 4.255 | — |
| validation | FT_LIMIT__ZONE_2R | 4 | 3 | -0.668 | 0.333 | 0.041 | 2.003 | — |
| validation | FT_LIMIT__ATR_1_5R | 5 | 4 | 0.174 | 0.500 | 1.323 | 1.084 | — |
| validation | REPEAT_LIMIT__ZONE_2R | 7 | 4 | 0.649 | 1.000 | — | 0.000 | — |
| validation | REPEAT_LIMIT__ATR_1_5R | 8 | 5 | 0.918 | 0.800 | 5.218 | 1.088 | — |
| validation | FT_RECLAIM__ZONE_2R | 5 | 4 | 0.727 | 0.750 | 3.846 | 1.022 | — |
| validation | FT_RECLAIM__ATR_1_5R | 5 | 4 | 0.811 | 0.750 | 4.087 | 1.051 | — |
| validation | FLIP_LIMIT__ZONE_2R | 8 | 5 | -0.801 | 0.200 | 0.074 | 4.328 | — |
| validation | FLIP_LIMIT__ATR_1_5R | 8 | 5 | -1.074 | 0.000 | 0.000 | 5.370 | — |
| validation | FT_LIMIT_EMA50__ZONE_2R | 1 | 1 | -1.031 | 0.000 | 0.000 | 1.031 | — |
| validation | FT_LIMIT_EMA50__ATR_1_5R | 2 | 2 | 0.172 | 0.500 | 1.320 | 1.075 | — |
| holdout | FT_LIMIT__ZONE_2R | 13 | 7 | -0.686 | 0.143 | 0.266 | 6.543 | — |
| holdout | FT_LIMIT__ATR_1_5R | 13 | 7 | -0.420 | 0.286 | 0.462 | 4.023 | — |
| holdout | REPEAT_LIMIT__ZONE_2R | 10 | 7 | -0.878 | 0.143 | 0.021 | 6.144 | — |
| holdout | REPEAT_LIMIT__ATR_1_5R | 11 | 8 | -0.188 | 0.375 | 0.728 | 3.283 | — |
| holdout | FT_RECLAIM__ZONE_2R | 9 | 6 | -1.075 | 0.000 | 0.000 | 6.449 | — |
| holdout | FT_RECLAIM__ATR_1_5R | 9 | 6 | -0.288 | 0.333 | 0.599 | 3.231 | — |
| holdout | FLIP_LIMIT__ZONE_2R | 11 | 8 | -0.492 | 0.250 | 0.396 | 4.460 | — |
| holdout | FLIP_LIMIT__ATR_1_5R | 13 | 10 | -0.106 | 0.400 | 0.841 | 2.426 | — |
| holdout | FT_LIMIT_EMA50__ZONE_2R | 5 | 2 | -1.050 | 0.000 | 0.000 | 2.100 | — |
| holdout | FT_LIMIT_EMA50__ATR_1_5R | 5 | 2 | -1.088 | 0.000 | 0.000 | 2.177 | — |

## Interpretation boundary

A positive row is a conditional historical result under the declared OHLC fill assumptions. It is not evidence of live executable performance. Data gaps, synthetic 4H aggregation, unknown symbol/venue, spread, slippage, commissions and intrabar path ambiguity limit the result.
The next required step is an independent, symbol-identified feed with a pre-registered holdout and broker-matched costs.
