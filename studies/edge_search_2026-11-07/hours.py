"""Intraday seasonality on gold 5m 2013-2026: mean return by New-York hour, train 2013-2019, test 2020-2026.
Strategy: long (or short) only in the hours whose train mean was clearly positive (negative). Compared with the
average hour, because gold's drift alone makes 'long any hour' look good in 2020-26. Cost 0.3 pt per round trip."""
import numpy as np, pandas as pd
a = np.fromfile("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
ts = a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000
c = pd.Series(a[:, 4], index=pd.to_datetime(ts, unit="s").tz_localize("UTC").tz_convert("America/New_York"))
c = c[c.index.year >= 2013]
h = c.resample("1h").last().dropna()
r = h.pct_change().dropna() * 1e4                       # bp per hour, labelled by the hour it ENDS in
r = r[r.abs() < 300]                                    # drop weekend/holiday gap jumps
r.index = r.index - pd.Timedelta(hours=1)              # label = hour it covers (e.g. 09 = 09:00-10:00 NY)
df = pd.DataFrame(dict(r=r, hr=r.index.hour, yr=r.index.year))
tr, te = df[df.yr <= 2019], df[df.yr >= 2020]
g = pd.DataFrame({"train_bp": tr.groupby("hr").r.mean(), "train_t": tr.groupby("hr").r.mean() / (tr.groupby("hr").r.std() / np.sqrt(tr.groupby("hr").r.size())),
                  "test_bp": te.groupby("hr").r.mean(), "test_t": te.groupby("hr").r.mean() / (te.groupby("hr").r.std() / np.sqrt(te.groupby("hr").r.size())),
                  "yrs_same_sign_as_train": df.groupby(["hr", "yr"]).r.mean().unstack().apply(lambda row: 0, axis=1)})
yrly = df.groupby(["hr", "yr"]).r.mean().unstack()
g["yrs_same_sign_as_train"] = [(np.sign(yrly.loc[hh]) == np.sign(g.train_bp[hh])).sum() for hh in g.index]
pd.set_option("display.float_format", lambda v: f"{v:.2f}")
print(g.to_string())
long_h = g.index[g.train_t > 2]; short_h = g.index[g.train_t < -2]
print("\nhours picked on 2013-19: long", list(long_h), "short", list(short_h))
avg_te = te.r.mean()
for lab, hh, sgn in [("long picked hours", long_h, 1), ("short picked hours", short_h, -1)]:
    if len(hh) == 0: continue
    x = te[te.hr.isin(hh)].r * sgn
    cost_bp = 0.3 / c[c.index.year >= 2020].mean() * 1e4 / len(hh)   # one round trip per day spread over the picked hours
    print(f"{lab}: test 2020-26 {x.mean():.2f} bp/hour gross, {x.mean() - cost_bp:.2f} net; average hour {avg_te*sgn:.2f} bp; t={x.mean()/(x.std()/np.sqrt(len(x))):.1f}")
