// Shared helpers: set symbol/resolution on the active chart, load full daily history, read all bars.
import { evaluate } from "/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src/connection.js";
export const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const SERIES = "window.TradingViewApi._chartWidgetCollection.getAll()[0].model().mainSeries()";
const CHART = "window.TradingViewApi._activeChartWidgetWV.value()";

export async function state() {
  return evaluate(`(() => { const s = ${SERIES}; const b = s.bars();
    return { symbol: s.symbol(), res: s.interval ? s.interval() : null, n: b.size(),
             first: b.size() ? b.valueAt(b.firstIndex())[0] : null }; })()`);
}
export async function setSymbolRes(sym, res) {
  await evaluate(`(() => { ${CHART}.setSymbol(${JSON.stringify(sym)}, {}); })()`);
  await sleep(1500);
  if (res) { await evaluate(`(() => { ${CHART}.setResolution(${JSON.stringify(res)}, {}); })()`); await sleep(1500); }
  let last = -1, stable = 0;
  for (let i = 0; i < 40; i++) {                      // wait until bars exist and stop changing
    const st = await state().catch(() => null);
    if (st && st.n > 0) { if (st.n === last) { if (++stable >= 2) return st; } else stable = 0; last = st.n; }
    await sleep(750);
  }
  return state();
}
export async function loadAll(maxRounds = 60) {
  let prev = (await state()).n, flat = 0;
  for (let r = 0; r < maxRounds && flat < 4; r++) {
    await evaluate(`(() => { ${SERIES}.requestMoreData(5000); })()`);
    await sleep(1200);
    const n = (await state()).n;
    if (n > prev) { prev = n; flat = 0; } else flat++;
  }
  return state();
}
export async function readBars() {
  return evaluate(`(() => { const b = ${SERIES}.bars(); const out = [];
    for (let i = b.firstIndex(); i <= b.lastIndex(); i++) { const v = b.valueAt(i); if (v) out.push(v.slice(0, 6)); }
    return out; })()`);
}
