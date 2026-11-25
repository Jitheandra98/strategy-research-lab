"""Block until the replay produces new closed bars (or timeout), then print them compactly for live commentary."""
import json, sys, time, os, datetime as dt
MIN_NEW = int(sys.argv[1]) if len(sys.argv) > 1 else 1
TIMEOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 120
st = "next_state.json"
done = json.load(open(st))["n"] if os.path.exists(st) else 0
t0 = time.time()
while True:
    rows = [json.loads(l) for l in open("bars.jsonl")] if os.path.exists("bars.jsonl") else []
    if len(rows) - done >= MIN_NEW or (time.time() - t0 > TIMEOUT): break
    time.sleep(1.5)
new = rows[done:]
json.dump({"n": len(rows)}, open(st, "w"))
if not new: print(f"no new bars in {TIMEOUT}s (replay paused?)"); sys.exit()
for r in new:
    d = r["desk"]; t = dt.datetime.utcfromtimestamp(r["t"] - 5 * 3600).strftime("%m-%d %H:%M CT")
    adx = d.get("ADX 14", "").replace("   ", " ")
    fresh = [f for f in r["fresh"] if not f.startswith(("QF SSL", "QF BSL"))]
    print(f"{t}  O{r['o']} H{r['h']} L{r['l']} C{r['c']}  {d.get('Regime','')} | ADX {adx} | {d.get('60 bias','').split(' ')[0]} | vol {d.get('Volatility','')}"
          + (f"\n    new: {'; '.join(fresh)[:400]}" if fresh else ""))
