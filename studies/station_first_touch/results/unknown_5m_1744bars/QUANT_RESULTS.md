# Station First-Touch quant report — `unknown_5m_1744bars`

This is a frozen research run. It does not prove profitability, identify institutional inventory, or reconstruct broker fills.
The feed is kept separate because its provenance is unknown.

## Data audit

- Source: `/Users/jitheandrasubramaniam/Desktop/hey hey/recorder_data/recorder_5m_1744bars.json`
- SHA-256: `a72b34c7d569bc4b672da7f91f511ede10604b38455a01770577c1e95b043319`
- Rows: **1744**; LTF step: **300 seconds**
- Observed range: **1785166200 → 1785887100 UTC seconds**
- Missing LTF buckets: **660** across **7** gaps; max gap **176700 seconds**
- Complete synthetic 4H buckets: **31**; partial: **9**
- Zones/events/visits: **8 / 36 / 19**

## Frozen selection

- Result: **NO_MODEL_SELECTED**
- Selected config: **none**
- Validation selection requires at least 10 uncensored trades, positive expectancy at 1 point cost, and a positive lower block-bootstrap CI.
- Holdout is not used to select a model.

## First touch versus repeat

- train / first / long: n=2 evaluable at 8h, median MFE=1.101 ATR, mean terminal=-9.218 ATR.

## Model metrics at 1 point cost

| Split | Config | n | uncensored | expectancy (R) | win rate | PF | max DD (R) | bootstrap CI |
|---|---|---:|---:|---:|---:|---:|---:|---|
| train | FT_LIMIT__ZONE_2R | 2 | 2 | -1.118 | 0.000 | 0.000 | 2.235 | — |
| train | FT_LIMIT__ATR_1_5R | 2 | 2 | -1.313 | 0.000 | 0.000 | 2.625 | — |
| train | REPEAT_LIMIT__ZONE_2R | 0 | 0 | — | — | — | — | — |
| train | REPEAT_LIMIT__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| train | FT_RECLAIM__ZONE_2R | 1 | 1 | -1.146 | 0.000 | 0.000 | 1.146 | — |
| train | FT_RECLAIM__ATR_1_5R | 1 | 1 | -1.274 | 0.000 | 0.000 | 1.274 | — |
| train | FLIP_LIMIT__ZONE_2R | 1 | 1 | 1.939 | 1.000 | — | 0.000 | — |
| train | FLIP_LIMIT__ATR_1_5R | 2 | 2 | 1.257 | 1.000 | — | 0.000 | — |
| train | FT_LIMIT_EMA50__ZONE_2R | 0 | 0 | — | — | — | — | — |
| train | FT_LIMIT_EMA50__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| validation | FT_LIMIT__ZONE_2R | 0 | 0 | — | — | — | — | — |
| validation | FT_LIMIT__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| validation | REPEAT_LIMIT__ZONE_2R | 0 | 0 | — | — | — | — | — |
| validation | REPEAT_LIMIT__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| validation | FT_RECLAIM__ZONE_2R | 0 | 0 | — | — | — | — | — |
| validation | FT_RECLAIM__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| validation | FLIP_LIMIT__ZONE_2R | 1 | 1 | -1.182 | 0.000 | 0.000 | 1.182 | — |
| validation | FLIP_LIMIT__ATR_1_5R | 1 | 1 | -1.200 | 0.000 | 0.000 | 1.200 | — |
| validation | FT_LIMIT_EMA50__ZONE_2R | 0 | 0 | — | — | — | — | — |
| validation | FT_LIMIT_EMA50__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| holdout | FT_LIMIT__ZONE_2R | 0 | 0 | — | — | — | — | — |
| holdout | FT_LIMIT__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| holdout | REPEAT_LIMIT__ZONE_2R | 0 | 0 | — | — | — | — | — |
| holdout | REPEAT_LIMIT__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| holdout | FT_RECLAIM__ZONE_2R | 0 | 0 | — | — | — | — | — |
| holdout | FT_RECLAIM__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| holdout | FLIP_LIMIT__ZONE_2R | 0 | 0 | — | — | — | — | — |
| holdout | FLIP_LIMIT__ATR_1_5R | 0 | 0 | — | — | — | — | — |
| holdout | FT_LIMIT_EMA50__ZONE_2R | 0 | 0 | — | — | — | — | — |
| holdout | FT_LIMIT_EMA50__ATR_1_5R | 0 | 0 | — | — | — | — | — |

## Interpretation boundary

A positive row is a conditional historical result under the declared OHLC fill assumptions. It is not evidence of live executable performance. Data gaps, synthetic 4H aggregation, unknown symbol/venue, spread, slippage, commissions and intrabar path ambiguity limit the result.
The next required step is an independent, symbol-identified feed with a pre-registered holdout and broker-matched costs.
