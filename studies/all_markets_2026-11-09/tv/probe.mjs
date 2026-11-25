// Probe the TradingView chart: layout, symbols, resolutions, and a safety check for unexpected pages.
import { evaluate, disconnect } from "/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src/connection.js";
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
for (let i = 0; i < 30; i++) {
  const ok = await evaluate("!!(window.TradingViewApi && window.TradingViewApi._chartWidgetCollection)").catch(() => false);
  if (ok) break; await sleep(2000);
}
const info = await evaluate(`(() => {
  const col = window.TradingViewApi._chartWidgetCollection.getAll();
  const charts = col.map((w, i) => { try { const m = w.model(); const s = m.mainSeries();
      return { i, symbol: s.symbol(), resolution: s.interval ? s.interval() : null, bars: s.bars().size() }; }
    catch (e) { return { i, err: String(e) }; } });
  const txt = document.body ? document.body.innerText : '';
  return { url: location.href, title: document.title, charts,
           checkoutLike: /checkout|card number|billing address/i.test(txt), hidden: document.hidden };
})()`);
console.log(JSON.stringify(info, null, 1));
await disconnect();
