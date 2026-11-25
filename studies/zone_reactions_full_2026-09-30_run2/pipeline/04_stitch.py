"""Stage 4 — stitch per-frame bars into one continuous, dated 5-minute series.

1. time-of-day (tod) for every digitized bar from the hour labels of its own frame
2. stitch: each frame gets an integer offset so global index g = k + off, chosen by
   matching tod AND prices against the chain built so far (new chain if nothing matches)
3. consolidate: per g, median of all clean observations (n_obs, spread kept for QA)
4. date: calendar walker over g using CME Globex metals sessions (Sun–Fri 17:00–16:00 CT,
   full closures below). OCR'd day/month labels are NOT used to set dates; they are held out
   as an independent check (agreement rate reported).
Outputs WORK/stitched/: bars_5m.csv, frame_map.csv, stitch_report.json
"""
import json, sys
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

W = Path(sys.argv[1])
import os
CONS_MODE = os.environ.get("CONS_MODE", "extreme")
OUT = W / "stitched"
OUT.mkdir(exist_ok=True)

# Days with NO Globex metals trade date (no session opens the evening before).
FULL_CLOSURES = {date(2025, 12, 25), date(2026, 1, 1), date(2026, 4, 3), date(2026, 12, 25)}


def is_trading_day(d):
    return d.weekday() < 5 and d not in FULL_CLOSURES


def next_session_open_date(d):
    """Calendar date whose 17:00 CT opens the next trade date after trade date containing d."""
    nd = d + timedelta(days=1)
    while not is_trading_day(nd):
        nd += timedelta(days=1)
    return nd - timedelta(days=1)


# ── 1. per-frame tod ───────────────────────────────────────────────────────
def frame_tod(rec):
    ax = rec["layout"]["axis_x"]
    raw = sorted([((l["xc"] - rec["phase"]) / rec["pitch"], l["value"]) for l in rec["labels"]
                  if l["kind"] == "hour" and l["value"] % 60 == 0 and 88 < l["xc"] < ax - 30])
    if not raw:
        return {}
    # Joint snapping: within one uninterrupted stretch, label k = A + minutes/5 for a constant A.
    # OCR box centres wobble by up to half a bar, so snap each stretch with its median A.
    tu, prev, add = [], None, 0
    for kf, t in raw:
        if prev is not None and t + add < prev:
            add += 1440
        tu.append(t + add)
        prev = t + add
    A = [kf - t / 5 for (kf, _), t in zip(raw, tu)]
    # drop labels inconsistent with BOTH neighbours (a real gap boundary agrees with one side)
    keep = []
    for i in range(len(A)):
        nb = [A[j] for j in (i - 1, i + 1) if 0 <= j < len(A)]
        if nb and all(abs(A[i] - x) > 1.0 for x in nb):
            if len(nb) == 2 and abs(nb[0] - nb[1]) <= 1.0:
                continue                      # neighbours agree with each other → i is the outlier
            if len(nb) == 1:
                j2 = i + 2 if i == 0 else i - 2
                if 0 <= j2 < len(A) and abs(A[j2] - nb[0]) <= 1.0:
                    continue                  # end label disagrees with a consistent pair
        keep.append(i)
    raw = [raw[i] for i in keep]
    tu = [tu[i] for i in keep]
    A = [A[i] for i in keep]
    if not raw:
        return {}
    groups, cur = [], [0]
    for i in range(1, len(raw)):
        if abs(A[i] - A[i - 1]) > 1.5:      # session gap between these labels
            groups.append(cur)
            cur = []
        cur.append(i)
    groups.append(cur)
    hrs = []
    for grp in groups:
        a = float(np.median([A[i] for i in grp]))
        if len(grp) >= 2 and max(abs(A[i] - a) for i in grp) > 1.0:
            continue                          # stretch is internally inconsistent: drop it
        for i in grp:
            hrs.append((int(round(a + tu[i] / 5)), raw[i][1]))
    hrs.sort()
    good = hrs
    tod = {}
    if not good:
        return tod
    CLOSE, OPEN = 16 * 60, 17 * 60          # daily Globex break 16:00–17:00 CT
    # between consecutive labels
    for (kL, tL), (kR, tR) in zip(good[:-1], good[1:]):
        dk, dt = kR - kL, (tR - tL) % 1440 or 1440
        if dk * 5 == dt:
            for k in range(kL, kR):
                tod[k] = (tL + 5 * (k - kL)) % 1440
        elif dk * 5 < dt and tR >= OPEN:
            # a gap lies between. Everything from the 17:00 open up to kR is fixed by tR; the rest
            # belongs to the earlier session (ends 15:55 normally, earlier on holiday early closes).
            nr = (tR - OPEN) // 5
            nl = dk - nr
            if nl >= 0 and tL + 5 * (nl - 1) < CLOSE:
                for i in range(nl):
                    tod[kL + i] = (tL + 5 * i) % 1440
                for i in range(nr):
                    tod[kR - nr + i] = OPEN + 5 * i
            # else: inconsistent — leave these bars unknown in this frame
        tod[kR] = tR
    # before the first label: walk back ≤ 12 bars, stopping at a 17:00 session open
    k1, t1 = good[0]
    tod[k1] = t1
    t, k = t1, k1
    for _ in range(12):
        if t == OPEN:
            break
        k -= 1
        t = (t - 5) % 1440
        tod[k] = t
    # after the last label: walk forward ≤ 11 bars (labels are hourly), never past 15:55
    kN, tN = good[-1]
    t, k = tN, kN
    for _ in range(11):
        k += 1
        t = (t + 5) % 1440
        if t == CLOSE:
            break
        tod[k] = t
    ks = {b["k"] for b in rec["bars"]}
    return {k: v for k, v in tod.items() if k in ks}


# ── 2. stitching ───────────────────────────────────────────────────────────
class Chain:
    def __init__(self, cid):
        self.cid = cid
        self.obs = defaultdict(list)     # g -> list of (tod, h, l, o, c, flags, frame_id)
        self.cache = {}                  # g -> (tod, h, l)

    def add(self, g, row):
        self.obs[g].append(row)
        self.cache.pop(g, None)

    def ref(self, g):
        if g not in self.cache:
            rows = [r for r in self.obs[g] if "last" not in r[5] and "clipped" not in r[5]] or self.obs[g]
            tc = Counter(r[0] for r in rows if r[0] is not None)
            tods = tc.most_common(1)[0][0] if tc else None
            self.cache[g] = (tods, float(np.median([r[1] for r in rows])), float(np.median([r[2] for r in rows])))
        return self.cache[g]


def match(chain, bars, tod, recent_g, scale=0.1):
    """Best offset near the chain's recent bars; widen the window only if that fails."""
    if not chain.obs:
        return None
    for back, fwd in ((400, 400), (2000, 2000), (10 ** 9, 10 ** 9)):
        m = _match(chain, bars, tod, recent_g - back, recent_g + fwd, scale)
        if m:
            return m
    return None


def _match(chain, bars, tod, lo, hi, scale=0.1):
    """Return (offset, overlap, frac_agree) or None. Same-tod bars recur daily, so the
    window must be short enough that each tod appears about once."""
    by_tod = defaultdict(list)
    for g in chain.obs:
        if lo <= g <= hi:
            by_tod[chain.ref(g)[0]].append(g)
    votes = Counter()
    for b in bars:
        t = tod.get(b["k"])
        if t is None:
            continue
        for g in by_tod.get(t, []):
            votes[g - b["k"]] += 1
    if not votes:
        return None
    # candidate offsets: top tod votes and their ±3 neighbours (frame labels may be snapped 1-2 bars off)
    cands = set()
    for off, _ in votes.most_common(5):
        cands.update(range(off - 3, off + 4))
    tol = max(0.25, 2.5 * scale)

    def agree(off):
        d, tm, nt = [], 0, 0
        for b in bars:
            g = b["k"] + off
            if g not in chain.obs or "last" in b["flags"] or "label" in b["flags"]:
                continue
            t, hh, ll = chain.ref(g)
            d += [abs(hh - b["high"]), abs(ll - b["low"])]
            if b["k"] in tod:
                nt += 1
                tm += tod[b["k"]] == t
        if len(d) < 16:
            return None
        return float((np.array(d) <= tol).mean()), len(d) // 2, (tm / nt if nt else 0.0)

    scored = {off: agree(off) for off in cands}
    scored = {k: v for k, v in scored.items() if v is not None}
    if not scored:
        return None
    off = max(scored, key=lambda k: scored[k][0])
    frac, ov, tod_ok = scored[off]
    nb = max([scored[k][0] for k in (off - 1, off + 1) if k in scored] or [0.0])
    # PRICE decides: clearly better than the one-bar-shifted alternatives, and good in absolute terms
    if frac < 0.5 or frac - nb < 0.15:
        return None
    return (off, ov, frac, tod_ok)


def main():
    recs = [json.loads(l) for l in (W / "digitized" / "frames.jsonl").open()]
    recs.sort(key=lambda r: r["video_s"])
    chains, cur = [], None
    fmap = []
    recent_g = 0
    for r in recs:
        row = {"frame_id": r["frame_id"], "video_s": r["video_s"], "ok": r.get("ok"), "why": r.get("why")}
        if not r.get("ok"):
            fmap.append(row)
            continue
        tod = frame_tod(r)
        bars = [b for b in r["bars"] if b["k"] in tod]
        row.update(n_bars=len(r["bars"]), n_tod=len(bars), pitch=r["pitch"])
        if len(bars) < 15:
            row["why"] = "few_tod"
            fmap.append(row)
            continue
        scale = abs(r["price_fit"]["b"])
        m = match(cur, bars, tod, recent_g, scale) if cur else None
        if m is None and chains:
            # try earlier chains (replay rewinds / returns)
            for ch in reversed(chains[:-1]):
                m2 = match(ch, bars, tod, max(ch.obs), scale)
                if m2:
                    cur, m = ch, m2
                    break
        if m is None:
            cur = Chain(len(chains))
            chains.append(cur)
            off = 100000 * cur.cid - min(b["k"] for b in bars)
            row.update(new_chain=True)
            md, ov = None, 0
        else:
            off, ov, md, tod_ok = m
            if tod_ok < 0.9:
                row["tod_override"] = True
        for b in bars:
            tval = None if row.get("tod_override") else tod[b["k"]]
            cur.add(b["k"] + off, (tval, b["high"], b["low"], b["open"], b["close"], tuple(b["flags"]), r["frame_id"], scale))
        recent_g = max(b["k"] for b in bars) + off
        row.update(chain=cur.cid, off=off, overlap=ov, match_frac=md,
                   g_last=(r["k_last"] + off) if r.get("k_last") is not None else None,
                   hdr4h=r.get("headers", {}).get("4h"), hdr5m=r.get("headers", {}).get("5m"))
        # held-out date evidence: day/month/year labels → g
        row["date_labels"] = [(l["kind"], l["value"], l["k"] + off) for l in r["labels"] if l["kind"] in ("day", "month", "year")]
        fmap.append(row)

    # ── 3. consolidate ─────────────────────────────────────────────────────
    out = []
    for ch in chains:
        for g in sorted(ch.obs):
            rows = ch.obs[g]
            clean = [x for x in rows if "last" not in x[5] and "clipped" not in x[5]]
            clean = [x for x in (clean or rows)]
            unlab = [x for x in clean if "label" not in x[5]]
            use = unlab or clean
            fine = min(x[7] for x in use)
            use = [x for x in use if x[7] <= 1.6 * fine]      # keep the highest-resolution views
            tcount = Counter(x[0] for x in rows if x[0] is not None)
            tod = tcount.most_common(1)[0][0] if tcount else None
            tod_agree = (tcount.most_common(1)[0][1] / sum(tcount.values())) if tcount else 0.0
            if unlab or CONS_MODE == "median":
                use = use if unlab else clean
                hs = [x[1] for x in use if "occ_top" not in x[5]] or [x[1] for x in use]
                ls = [x[2] for x in use if "occ_bot" not in x[5]] or [x[2] for x in use]
                hi_v, lo_v = float(np.median(hs)), float(np.median(ls))
            else:
                # every view touches a label: labels only ever HIDE wick ends (truncate), so take
                # a robust extreme across views (2nd-highest high / 2nd-lowest low guards 1 outlier)
                hs = sorted(x[1] for x in clean)
                ls = sorted(x[2] for x in clean)
                hi_v = hs[-2] if len(hs) >= 3 else hs[-1]
                lo_v = ls[1] if len(ls) >= 3 else ls[0]
            os_ = [x[3] for x in use if x[3] is not None]
            cs = [x[4] for x in use if x[4] is not None]
            out.append(dict(chain=ch.cid, g=g, tod=tod, high=hi_v, low=lo_v,
                            open=np.median(os_) if os_ else np.nan, close=np.median(cs) if cs else np.nan,
                            n_obs=len(rows), n_clean=len(clean),
                            h_spread=float(np.ptp(hs)) if len(hs) > 1 else 0.0,
                            l_spread=float(np.ptp(ls)) if len(ls) > 1 else 0.0,
                            only_last=not any("last" not in x[5] for x in rows), pt_per_px=fine, n_used=len(use),
                            label_only=len(unlab) == 0, tod_agree=tod_agree))
    bars = pd.DataFrame(out).sort_values(["chain", "g"]).reset_index(drop=True)
    # bars seen only by label-overridden frames: infer tod from the previous bar (+5 min, skipping
    # the 16:00–17:00 break). Holiday edges stay unknown and are dropped.
    for idx in bars.index[bars.tod.isna()]:
        if idx > 0 and bars.chain[idx - 1] == bars.chain[idx] and bars.g[idx - 1] == bars.g[idx] - 1 \
                and pd.notna(bars.tod[idx - 1]):
            t = (int(bars.tod[idx - 1]) + 5) % 1440
            bars.loc[idx, "tod"] = 17 * 60 if t == 16 * 60 else t
    bars = bars.dropna(subset=["tod"])
    # label-covered bodies: repair from clean neighbours (open ≈ previous close on gold 5m;
    # clean-bar median |open - prev close| = 0.14 pt)
    bars = bars.sort_values(["chain", "g"]).reset_index(drop=True)
    adj_prev = (bars.chain == bars.chain.shift()) & (bars.g == bars.g.shift() + 1)
    adj_next = (bars.chain == bars.chain.shift(-1)) & (bars.g == bars.g.shift(-1) - 1)
    lab = bars.label_only
    fix_o = lab & adj_prev & ~bars.label_only.shift().fillna(True).astype(bool) & (bars.tod != 17 * 60)
    fix_c = lab & adj_next & ~bars.label_only.shift(-1).fillna(True).astype(bool) & (bars.tod.shift(-1) != 17 * 60)
    bars.loc[fix_o, "open"] = bars.close.shift()[fix_o]
    bars.loc[fix_c, "close"] = bars.open.shift(-1)[fix_c]
    bars["body_repaired"] = fix_o | fix_c
    bars["high"] = bars[["high", "open", "close"]].max(axis=1)
    bars["low"] = bars[["low", "open", "close"]].min(axis=1)
    bars["tod"] = bars.tod.astype(int)
    bars.to_csv(OUT / "bars_raw.csv", index=False)
    pd.DataFrame(fmap).to_json(OUT / "frame_map.jsonl", orient="records", lines=True)
    print("chains", len(chains), "bars", len(bars), flush=True)
    for ch in chains:
        sub = bars[bars.chain == ch.cid]
        print(ch.cid, len(sub), sub.g.min(), sub.g.max(), "missing", (sub.g.max() - sub.g.min() + 1) - len(sub))


if __name__ == "__main__":
    main()
