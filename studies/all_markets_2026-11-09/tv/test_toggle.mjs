// Verify the chart's backAdjustment property changes the data, then restore it to its original value.
import { evaluate, disconnect } from "/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src/connection.js";
import { setSymbolRes, readBars, loadAll, sleep } from "./pull_lib.mjs";
const P = "window.TradingViewApi._chartWidgetCollection.getAll()[0].model().mainSeries().properties().childs()";
const orig = await evaluate(`${P}.backAdjustment.value()`);
await setSymbolRes("NYMEX:CL1!", "1D");
await loadAll(6);
const a = await readBars();
await evaluate(`${P}.backAdjustment.setValue(${!orig})`); await sleep(4000);
await loadAll(6);
const b = await readBars();
await evaluate(`${P}.backAdjustment.setValue(${orig})`); await sleep(3000);
const now = await evaluate(`${P}.backAdjustment.value()`);
const mapB = new Map(b.map(v => [v[0], v[4]]));
const sample = a.filter((v, i) => i % Math.floor(a.length / 8) === 0).map(v => [new Date(v[0] * 1000).toISOString().slice(0, 10), v[4], mapB.get(v[0])]);
console.log(JSON.stringify({ original_backAdjustment: orig, restored_to: now, bars_orig: a.length, bars_toggled: b.length,
  first_date: new Date(a[0][0] * 1000).toISOString().slice(0, 10), sample_close_orig_vs_toggled: sample }, null, 1));
await disconnect();
