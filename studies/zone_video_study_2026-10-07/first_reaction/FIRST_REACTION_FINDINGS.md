# First-reaction pattern scan — 2026-10-07

Exploratory results, using reconstructed zone events and independent-feed one-minute bars. All existing splits were previously inspected. V3 is a robustness check, not an untouched holdout.

Entry: next minute open after the arrival 15m candle closes. This tests reactions still available after a completed candle; it cannot settle immediate-touch scalping. Targets: 0.25/0.5/0.75 arrival ATR; stops: 0.5/1 ATR; holding limits: 5/15/30 minutes. Costs: 0.30 and 0.60 points per trade. Same-minute target/stop ties lose. No missing minute is filled. These settings are research choices, not the user's exact trade rules.

Eligible event rows: 26911; excluded for missing execution window: 341. 28 conditions × 18 configurations were screened on discovery only. Multiple zones on the same candle/direction are counted once within each condition. Separate trades still overlap; these are signal-level results, not portfolio returns. Daily bootstrap intervals measure dependence sensitivity but do not correct selection or prove significance.

Top conditions selected by discovery net R (minimum 80 signals), one configuration per condition:

pattern,target_atr,stop_atr,hold_min,n_discovery,net_R_discovery,n_robustness,net_R_robustness,net_pts_robustness,daily_ci_lo_pts,daily_ci_hi_pts
deep_wick_reclaim,0.5,1.0,30,165,-0.0213,1419,-0.0866,-0.4995,-0.8335,-0.1701
deep_wick_reclaim & with_4h_trend,0.5,1.0,5,94,-0.056,828,-0.0644,-0.2579,-0.5454,0.0572
first_arrival & velocity_atr_per_bar_low,0.5,1.0,30,257,-0.0963,1111,-0.0773,-0.5043,-0.7949,-0.2228
height_atr_low,0.75,1.0,30,1551,-0.1091,9152,-0.0683,-0.3055,-0.4219,-0.1857
first_arrival,0.75,1.0,30,978,-0.113,4141,-0.0816,-0.3281,-0.4993,-0.15
multiple_toward,0.75,1.0,30,768,-0.1139,2224,-0.0801,-0.2284,-0.4236,-0.0077
compress5_atr_high,0.75,1.0,30,1408,-0.1156,4050,-0.0744,-0.1904,-0.3492,-0.0112
rng_last3_atr_low,0.5,1.0,30,1504,-0.1185,4922,-0.0781,-0.3656,-0.5083,-0.2457
accel_ratio_low,0.5,1.0,30,1537,-0.1247,4836,-0.0762,-0.336,-0.4599,-0.2063
close_back_outside & accel_ratio_low,0.5,1.0,30,839,-0.1262,2918,-0.0691,-0.2633,-0.4218,-0.0975


See ALL_RESULTS.csv for every attempted condition/settings combination and EXAMPLES.csv for successes and failures. Zone identity and interpolated video timestamps retain the limitations documented in audit/TAKEOVER_AUDIT.md. A positive result must survive matched random-band controls, realistic execution, portfolio overlap constraints and new unseen data before becoming a trading recommendation.
