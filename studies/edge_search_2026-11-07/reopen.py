"""Is the 'reopen hour' gain real or a quote artifact? Split the move into: 16:55 bar close -> first bar after reopen (gap),
first bar after reopen -> 18:30, 18:30 -> 19:00 (New York time). Spot (HistData bid quotes, 2013-2026) vs MGC futures trades (his chart, Sep-Nov 2026)."""
import json, numpy as np, pandas as pd
def legs(c):  # c: close series, NY tz, 5m bars labelled by bar start
    out = []
    for d, g in c.groupby(c.index.date):
        pre = g[(g.index.hour == 16) & (g.index.minute >= 50)]
        if pre.empty: continue
        nxt = c[(c.index > pre.index[-1]) & (c.index <= pre.index[-1] + pd.Timedelta(hours=3))]
        post = nxt[nxt.index.hour >= 18]
        if len(post) < 6: continue
        p0 = pre.iloc[-1]; p1 = post.iloc[0]
        p2 = post[post.index <= post.index[0].normalize() + pd.Timedelta(hours=18, minutes=30)]
        p3 = post[post.index <= post.index[0].normalize() + pd.Timedelta(hours=19)]
        if p2.empty or p3.empty: continue
        out.append(dict(day=pd.Timestamp(d), gap=(p1 / p0 - 1) * 1e4, first30=(p2.iloc[-1] / p1 - 1) * 1e4, next30=(p3.iloc[-1] / p2.iloc[-1] - 1) * 1e4))
    return pd.DataFrame(out)
def show(lab, df):
    m = df[["gap", "first30", "next30"]]
    print(f"\n{lab}: {len(df)} days")
    print(pd.DataFrame({"mean_bp": m.mean(), "t": m.mean() / (m.std() / np.sqrt(len(m))), "pct_up": (m > 0).mean() * 100}).round(2).to_string())
a = np.fromfile("/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/xau5m.f64").reshape(-1, 5)
ts = a[:, 0] if a[0, 0] < 1e11 else a[:, 0] / 1000
spot = pd.Series(a[:, 4], index=pd.to_datetime(ts, unit="s").tz_localize("UTC").tz_convert("America/New_York"))
spot = spot[spot.index.year >= 2013]
s = legs(spot)
show("SPOT XAUUSD 2013-2019", s[s.day.dt.year <= 2019]); show("SPOT XAUUSD 2020-2026", s[s.day.dt.year >= 2020])
b = np.array(json.load(open("/Users/jitheandrasubramaniam/Desktop/hey hey/research/replay_live_2026-11-01/mgc5m_bars.json")))
fut = pd.Series(b[:, 4], index=pd.to_datetime(b[:, 0], unit="s").tz_localize("UTC").tz_convert("America/New_York"))
show("MGC FUTURES (trade prices) Sep 16 - Nov 6 2026", legs(fut))
show("SPOT same dates Sep 16 - Sep 24 2026 (overlap)", s[s.day >= "2026-09-16"])
