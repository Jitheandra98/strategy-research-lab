// Does TradingView give back-adjusted continuous futures? Compare ES1! daily with and without back-adjustment.
import { disconnect } from "/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src/connection.js";
import { setSymbolRes, readBars, state } from "./pull_lib.mjs";
const variants = ["CME_MINI:ES1!", '={"backadjustment":"default","symbol":"CME_MINI:ES1!"}',
                  '={"backadjustment":"on","symbol":"CME_MINI:ES1!"}'];
const res = {};
for (const v of variants) {
  const st = await setSymbolRes(v, "1D");
  const bars = await readBars();
  res[v] = { st, n: bars.length, firstBar: bars[0], lastBar: bars[bars.length - 1] };
}
console.log(JSON.stringify(res, null, 1));
await disconnect();
