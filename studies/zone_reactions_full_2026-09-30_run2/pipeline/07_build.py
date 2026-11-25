"""Stage 7 — final bar series + zone engines.

Inputs : WORK/stitched/bars_5m_dated.csv
Outputs (OUT = research run folder):
  data/bars_5m.csv       reconstructed 5m OHLC (CT + UTC), quality columns
  data/bars_4h.csv       4H bars aggregated on the session grid (17,21,01,05,09,13 CT) — validated
  zones.csv              every zone from both engines with lifecycle timestamps
  data/structure_5m.csv, data/structure_4h.csv, data/pools_5m.csv
Engines run per contiguous segment (a bar gap that is not a session break splits a segment).
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from zone_engine import ZoneEngine

W = Path(sys.argv[1])
OUT = Path(sys.argv[2])
(OUT / "data").mkdir(parents=True, exist_ok=True)


def load_5m():
    b = pd.read_csv(W / "stitched" / "bars_5m_dated.csv")
    b["time_ct"] = pd.to_datetime(b.time_ct, utc=True).dt.tz_convert("America/Chicago")
    b["time_utc"] = b.time_ct.dt.tz_convert("UTC")
    # when did each bar first appear completed on screen? (recording time, for scrubbing the video)
    fm = pd.read_json(W / "stitched" / "frame_map.jsonl", lines=True).dropna(subset=["g_last"])
    fm = fm.sort_values("video_s")
    first_seen = {}
    for ch, sub in fm.groupby("chain"):
        top = -10 ** 12
        for vs, gl in zip(sub.video_s, sub.g_last):
            gl = int(gl)
            if gl > top:
                for gg in range(max(top + 1, gl - 400), gl + 1):
                    first_seen.setdefault((ch, gg), vs)
                top = gl
    b["video_s"] = [first_seen.get((c_, g_), np.nan) for c_, g_ in zip(b.chain, b.g)]
    b["video_ts"] = b.video_s.map(lambda v: "" if pd.isna(v) else f"{int(v)//3600}:{int(v)//60%60:02d}:{int(v)%60:02d}")
    # chains are dated independently against their own axis labels; merge the substantial ones
    # (>= 1000 bars and >= 90% label agreement) on time; stray one-frame chains are dropped
    rep = pd.DataFrame(json.loads((W / "stitched" / "date_report.json").read_text()))
    rep["agree"] = rep.votes_ok / rep.votes_total.clip(lower=1)
    keep = rep[(rep.n_bars >= 1000) & (rep.agree >= 0.9)].chain
    b = b[b.chain.isin(keep)]
    b = b.sort_values(["time_ct", "n_obs"], ascending=[True, False]).drop_duplicates("time_ct", keep="first")
    b = b.reset_index(drop=True)
    # fill missing open/close from neighbours (no_body observations): open=prev close, close=next open
    b["open"] = b.open.fillna(b.close.shift())
    b["close"] = b.close.fillna(b.open.shift(-1))
    mid = b[["high", "low"]].mean(axis=1)
    b["open"] = b.open.fillna(mid)
    b["close"] = b.close.fillna(mid)
    b = repair_spikes(b)
    # enforce OHLC consistency (pixel noise can put a body edge 1 px past a wick end)
    b["high"] = b[["high", "open", "close"]].max(axis=1)
    b["low"] = b[["low", "open", "close"]].min(axis=1)
    for c in ["open", "high", "low", "close"]:
        b[c] = b[c].round(1)
    # segments: consecutive bars must be 5 min apart unless the gap is a session break
    dt = b.time_ct.diff().dt.total_seconds().div(60)
    # small holes (bars never observed) inside a session are bridged, not split: up to 6 bars
    same_session = ~((b.tod == 17 * 60) & (dt >= 65))
    b["gap_before"] = np.where(same_session & (dt > 5) & (dt <= 35), (dt / 5 - 1).astype("Int64"), 0)
    brk = (dt != 5) & same_session & ~((dt > 5) & (dt <= 35))
    brk.iloc[0] = True
    b["segment"] = brk.cumsum() - 1
    return b


def repair_spikes(b):
    """Backstop for reading glitches (flat junk bars, borders read as wicks). Uses a provisional
    ATR(14) on the raw series. Flags every repaired bar in `spike_repaired`.
    (1) runs of 1-3 bars whose mid-price sits > 3 ATR from both the bar before and after while those
        two agree (within 1.5 ATR): replaced by a flat bridge at the neighbours' level.
    (2) single wicks extending > 3 ATR beyond BOTH neighbours' extremes with the body inside the
        neighbours' range: the wick is clipped to the neighbours' extreme."""
    b = b.copy()
    o, h, l, c = (b[k].to_numpy(float).copy() for k in ["open", "high", "low", "close"])
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = pd.Series(tr).rolling(14, min_periods=5).median().bfill().to_numpy() * 1.3
    t = b.time_ct.to_numpy()
    n = len(b)
    fl = np.zeros(n, bool)
    for L in (1, 2, 3):
        for i in range(1, n - L):
            if (t[i + L] - t[i - 1]) / np.timedelta64(1, "m") > 5 * (L + 1) + 70:
                continue
            pre, post = c[i - 1], o[i + L]
            mid = (h[i:i + L] + l[i:i + L]).mean() / 2
            A = a[i - 1]
            if abs(post - pre) <= 1.5 * A and abs(mid - pre) > 3 * A and abs(mid - post) > 3 * A:
                for j in range(i, i + L):
                    o[j] = c[j] = pre + (post - pre) * (j - i + 1) / (L + 1)
                    h[j] = l[j] = o[j]
                fl[i:i + L] = True
    # (3) flat junk bars (range <= 0.3 pt, i.e. a line or label edge read as a candle) that are
    #     discontinuous with a neighbour by > 1.5 ATR: bridged between prev close and next open
    for i in range(1, n - 1):
        A = a[i - 1]
        if h[i] - l[i] <= 0.3 and (abs(o[i] - c[i - 1]) > 1.5 * A or abs(o[i + 1] - c[i]) > 1.5 * A):
            if (t[i + 1] - t[i - 1]) / np.timedelta64(1, "m") <= 10:
                v0, v1 = c[i - 1], o[i + 1]
                o[i], c[i] = v0, v1
                h[i], l[i] = max(v0, v1), min(v0, v1)
                fl[i] = True
    for i in range(1, n - 1):
        A = a[i - 1]
        body_lo, body_hi = min(o[i], c[i]), max(o[i], c[i])
        if l[i] < min(l[i - 1], l[i + 1]) - 3 * A and body_lo >= min(l[i - 1], l[i + 1]):
            l[i] = min(l[i - 1], l[i + 1], body_lo)
            fl[i] = True
        if h[i] > max(h[i - 1], h[i + 1]) + 3 * A and body_hi <= max(h[i - 1], h[i + 1]):
            h[i] = max(h[i - 1], h[i + 1], body_hi)
            fl[i] = True
    b["open"], b["high"], b["low"], b["close"] = o, h, l, c
    b["spike_repaired"] = fl
    return b


def bucket_4h(t):
    h = (t.hour - 17) % 24
    return t - pd.Timedelta(hours=h % 4, minutes=t.minute)


def build_4h(b):
    b = b.copy()
    b["b4"] = [bucket_4h(t) for t in b.time_ct]
    g = b.groupby(["segment", "b4"], sort=True)
    h4 = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
               n5=("open", "size"), last5=("time_ct", "last"), first_i=("open", lambda s: s.index[0]),
               last_i=("open", lambda s: s.index[-1])).reset_index()
    h4 = h4.rename(columns={"b4": "time_ct"})
    h4["time_utc"] = h4.time_ct.dt.tz_convert("UTC")
    return b, h4


def h4_import(b, h4):
    """request.security("240",[low[1],high[3],high[1],low[3],time[1]]) as seen by each 5m bar in
    REPLAY (realtime) mode: inside forming 4H bar j the tuple refers to closed bars j-1, j-3."""
    idx = {(s, t): i for i, (s, t) in enumerate(zip(h4.segment, h4.time_ct))}
    rows = []
    for s, t in zip(b.segment, b.b4):
        j = idx[(s, t)]
        if j >= 3 and h4.segment.iloc[j - 3] == s:
            rows.append((h4.low.iloc[j - 1], h4.high.iloc[j - 3], h4.high.iloc[j - 1], h4.low.iloc[j - 3],
                         h4.time_ct.iloc[j - 1]))
        else:
            rows.append((np.nan, np.nan, np.nan, np.nan, pd.NaT))
    return pd.DataFrame(rows, columns=["h4bl", "h4bh", "h4sl", "h4sh", "h4t"])


def main():
    b = load_5m()
    b, h4 = build_4h(b)
    imp = h4_import(b, h4)
    zones_all, s5, s4, pools = [], [], [], []
    for seg, sub in b.groupby("segment"):
        if len(sub) < 400:
            continue
        idx = sub.index.to_numpy()
        e5 = ZoneEngine(sub[["open", "high", "low", "close"]], h4_import=imp.loc[idx].reset_index(drop=True),
                        label="5m").run()
        times = sub.time_ct.to_numpy()
        z = e5.zones_frame(times=list(sub.time_ct))
        if z.empty:
            continue
        z["segment"] = seg
        z["born_i"] = z.born_bar.map(lambda k: idx[int(k)])
        for c in ["first_touch_bar", "consumed_bar", "inverted_bar", "end_bar"]:
            z[c.replace("_bar", "_i")] = z[c].map(lambda k: idx[int(k)] if pd.notna(k) else np.nan)
        zones_all.append(z)
        s5 += [dict(segment=seg, i=idx[i], time_ct=sub.time_ct.iloc[i], dir=d, kind=k, level=lv)
               for i, d, k, lv in e5.structure]
        pools += [dict(segment=seg, level=p["level"], side=p["side"], born_i=idx[p["born"]],
                       swept_i=(idx[p["swept_bar"]] if p["swept_bar"] not in (None, -1) else np.nan),
                       dropped=p["swept_bar"] == -1) for p in e5.pools]
        # engine atr/ema/trend back onto bars
        b.loc[idx, "atr5"] = e5.atr
        b.loc[idx, "ema5"] = e5.ema
        b.loc[idx, "trend5"] = e5.trend
    for seg, sub4 in h4.groupby("segment"):
        if len(sub4) < 60:
            continue
        # 4H chart: 250-bar warm-up would erase ~6 weeks of a 10-month sample; use EMA length (100)
        e4 = ZoneEngine(sub4[["open", "high", "low", "close"]].reset_index(drop=True), label="4h",
                        cfg={"WARMUP": 100}).run()
        z = e4.zones_frame(times=list(sub4.time_ct))
        if z.empty:
            continue
        z["segment"] = seg
        # availability on the 5m clock: the 4H bar closes with its last 5m bar
        li = sub4.last_i.to_numpy()
        z["born_i"] = z.born_bar.map(lambda k: li[int(k)])
        for c in ["first_touch_bar", "consumed_bar", "inverted_bar", "end_bar"]:
            z[c.replace("_bar", "_i")] = z[c].map(lambda k: li[int(k)] if pd.notna(k) else np.nan)
        zones_all.append(z)
        s4 += [dict(segment=seg, i=li[i], time_ct=sub4.time_ct.iloc[i], dir=d, kind=k, level=lv)
               for i, d, k, lv in e4.structure]
        h4.loc[sub4.index, "atr4"] = e4.atr
        h4.loc[sub4.index, "ema4"] = e4.ema
        h4.loc[sub4.index, "trend4"] = e4.trend
    zones = pd.concat(zones_all, ignore_index=True)
    zones.insert(0, "zone_uid", [f"{tf}-{seg}-{zid}" for tf, seg, zid in zip(zones.tf, zones.segment, zones.zid)])
    zones.to_csv(OUT / "zones.csv", index=False)
    b.drop(columns=["b4"]).to_csv(OUT / "data" / "bars_5m.csv", index=False)
    h4.to_csv(OUT / "data" / "bars_4h.csv", index=False)
    pd.DataFrame(s5).to_csv(OUT / "data" / "structure_5m.csv", index=False)
    pd.DataFrame(s4).to_csv(OUT / "data" / "structure_4h.csv", index=False)
    pd.DataFrame(pools).to_csv(OUT / "data" / "pools_5m.csv", index=False)
    print("5m bars", len(b), "segments", b.segment.nunique(), "4h bars", len(h4))
    print("segment sizes", b.groupby("segment").size().sort_values(ascending=False).head(12).to_dict())
    print("segment starts", b.groupby("segment").time_ct.first().astype(str).tolist()[:40])
    print(zones.groupby(["tf", "kind"]).size())


if __name__ == "__main__":
    main()
