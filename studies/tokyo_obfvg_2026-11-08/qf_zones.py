"""QF CORE v1.0 order blocks + fair value gaps, ported from the owner's Pine code (2026-11-08) to Python on gold 5m 2012-2026.
Follows the script's bar order: crossovers on pre-update levels -> swing-flip OB expiry -> swing/internal pivots ->
internal then swing BOS/CHoCH (internal needs 1.3x displacement) -> OB store -> OB full-cross deletion -> FVG create /
IFVG overlap / close-through removal. Output zones.npz: kind (0 int OB, 1 swing OB, 2 FVG), side (+1 bull, -1 bear),
top, bot, created, removed (bar at whose close it disappeared; N = never), touch (first touch of the entry edge, -1 = none)."""
import sys
import numpy as np, pandas as pd

sys.path.insert(0, "/Users/jitheandrasubramaniam/Desktop/hey hey/research/catalog_100_2026-11-08")
from common import O, H, L, C, N, ATR

OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/tokyo_obfvg_2026-11-08/zones.npz"
SWING, INTL, DISP, OBMAX, FVGMAX, FVGMIN = 50, 5, 1.3, 100, 15, 0.3

body = np.abs(C - O); prng = H - L
cloc = np.where(prng > 0, 100.0 * (C - L) / np.where(prng > 0, prng, 1.0), 50.0)
avg10 = pd.Series(body).rolling(10).mean().to_numpy()
avg3 = (np.r_[np.nan, body[:-1]] + np.r_[np.nan, np.nan, body[:-2]] + np.r_[np.nan, np.nan, np.nan, body[:-3]]) / 3
ref = np.maximum(avg3, avg10)
dispBull = ((body > ref * DISP) & (cloc > 55) & (C > O)).tolist()
dispBear = ((body > ref * DISP) & (cloc < 45) & (C < O)).tolist()
hh = {n: pd.Series(H).rolling(n).max().to_numpy().tolist() for n in (SWING, INTL)}
ll = {n: pd.Series(L).rolling(n).min().to_numpy().tolist() for n in (SWING, INTL)}
Ol, Hl, Ll, Cl, Al = O.tolist(), H.tolist(), L.tolist(), C.tolist(), ATR.tolist()
isBear = (C < O).tolist()

kind, side, top, bot, created, removed = [], [], [], [], [], []


def new_zone(k, s, t, b, i):
    kind.append(k); side.append(s); top.append(t); bot.append(b); created.append(i); removed.append(N)
    return len(kind) - 1


class Piv:
    __slots__ = ("cur", "crossed", "idx")
    def __init__(self): self.cur, self.crossed, self.idx = None, False, -1


def run():
    swHi, swLo, inHi, inLo = Piv(), Piv(), Piv(), Piv()
    swTrend = inTrend = prevSw = 0
    leg = {SWING: 0, INTL: 0}
    intOBs, swgOBs, bullF, bearF = [], [], [], []
    prev_pre = (0.0, 0.0, 0.0, 0.0)
    nz = lambda p: p.cur if p.cur is not None else 0.0

    def storeOB(p, lst, k, bias, i):
        if not (0 < p.idx < i): return
        best, bv = -1, None
        for q in range(p.idx, i):
            if bias == 1 and isBear[q] and (bv is None or Ll[q] < bv): bv, best = Ll[q], q
            if bias == -1 and not isBear[q] and (bv is None or Hl[q] > bv): bv, best = Hl[q], q
        if best < 0: return
        if len(lst) >= OBMAX:
            removed[lst.pop()] = i
        lst.insert(0, new_zone(k, bias, Hl[best], Ll[best], i))

    for i in range(N):
        pre = (nz(inHi), nz(inLo), nz(swHi), nz(swLo))
        c, c1 = Cl[i], (Cl[i - 1] if i else Cl[0])
        xoIn = i > 0 and c > pre[0] and c1 <= prev_pre[0]
        xuIn = i > 0 and c < pre[1] and c1 >= prev_pre[1]
        xoSw = i > 0 and c > pre[2] and c1 <= prev_pre[2]
        xuSw = i > 0 and c < pre[3] and c1 >= prev_pre[3]
        prev_pre = pre
        # swing-flip OB expiry (uses the swing trend from earlier bars)
        flipBull, flipBear = swTrend == 1 and prevSw != 1, swTrend == -1 and prevSw != -1
        prevSw = swTrend
        if flipBull or flipBear:
            kill = -1 if flipBull else 1
            for lst in (intOBs, swgOBs):
                for z in [z for z in lst if side[z] == kill]:
                    lst.remove(z); removed[z] = i
        # pivots (swing then internal)
        for n, hiP, loP in ((SWING, swHi, swLo), (INTL, inHi, inLo)):
            if i >= n:
                newLeg = leg[n]
                if Hl[i - n] > hh[n][i]: newLeg = 0
                elif Ll[i - n] < ll[n][i]: newLeg = 1
                chg = newLeg - leg[n]; leg[n] = newLeg
                if chg == 1: loP.cur, loP.crossed, loP.idx = Ll[i - n], False, i - n
                elif chg == -1: hiP.cur, hiP.crossed, hiP.idx = Hl[i - n], False, i - n
        # internal structure (displacement required, must differ from the swing level)
        if xoIn and not inHi.crossed and inHi.cur != swHi.cur and dispBull[i]:
            inHi.crossed = True; inTrend = 1; storeOB(inHi, intOBs, 0, 1, i)
        if xuIn and not inLo.crossed and inLo.cur != swLo.cur and dispBear[i]:
            inLo.crossed = True; inTrend = -1; storeOB(inLo, intOBs, 0, -1, i)
        # swing structure
        if xoSw and not swHi.crossed:
            swHi.crossed = True; swTrend = 1; storeOB(swHi, swgOBs, 1, 1, i)
        if xuSw and not swLo.crossed:
            swLo.crossed = True; swTrend = -1; storeOB(swLo, swgOBs, 1, -1, i)
        # OB full-cross deletion (High/Low mitigation)
        for lst in (intOBs, swgOBs):
            dead = [z for z in lst if (side[z] == 1 and Ll[i] < bot[z]) or (side[z] == -1 and Hl[i] > top[z])]
            for z in dead:
                lst.remove(z); removed[z] = i
        # FVGs
        if i >= 2:
            nb = ns = None
            g = Ll[i] - Hl[i - 2]
            if g > 0 and g >= FVGMIN * Al[i]:
                nb = new_zone(2, 1, Ll[i], Hl[i - 2], i); bullF.append(nb)
                if len(bullF) > FVGMAX: removed[bullF.pop(0)] = i
            g = Ll[i - 2] - Hl[i]
            if g > 0 and g >= FVGMIN * Al[i]:
                ns = new_zone(2, -1, Ll[i - 2], Hl[i], i); bearF.append(ns)
                if len(bearF) > FVGMAX: removed[bearF.pop(0)] = i
            if ns is not None:
                for k in range(len(bullF) - 1, -1, -1):
                    z = bullF[k]
                    if min(top[z], top[ns]) > max(bot[z], bot[ns]):
                        removed[z] = i; bullF.pop(k); break
            if nb is not None:
                for k in range(len(bearF) - 1, -1, -1):
                    z = bearF[k]
                    if min(top[z], top[nb]) > max(bot[z], bot[nb]):
                        removed[z] = i; bearF.pop(k); break
            for z in [z for z in bullF if Cl[i] < bot[z]]:
                bullF.remove(z); removed[z] = i
            for z in [z for z in bearF if Cl[i] > top[z]]:
                bearF.remove(z); removed[z] = i


if __name__ == "__main__":
    import time
    t0 = time.time(); run(); print(f"engine {time.time() - t0:.0f}s, zones {len(kind):,}")
    K, S, T, B, Cr, Rm = (np.array(x) for x in (kind, side, top, bot, created, removed))
    touch = np.full(len(K), -1)
    for z in range(len(K)):
        end = min(Rm[z], N - 1)
        if S[z] == 1:
            e = T[z]
            for j in range(Cr[z] + 1, end + 1):
                if Ol[j] > e and Ll[j] <= e: touch[z] = j; break
        else:
            e = B[z]
            for j in range(Cr[z] + 1, end + 1):
                if Ol[j] < e and Hl[j] >= e: touch[z] = j; break
    np.savez(OUT, kind=K, side=S, top=T, bot=B, created=Cr, removed=Rm, touch=touch)
    for k, nm in ((0, "internal OB"), (1, "swing OB"), (2, "FVG")):
        m = K == k
        print(f"{nm:12s} {m.sum():8,d} zones ({(m & (S == 1)).sum():,} bull / {(m & (S == -1)).sum():,} bear), "
              f"touched {100 * (touch[m] >= 0).mean():.0f}%, median life {np.median(np.minimum(Rm[m], N) - Cr[m]):.0f} bars")
    print(f"total {time.time() - t0:.0f}s")
