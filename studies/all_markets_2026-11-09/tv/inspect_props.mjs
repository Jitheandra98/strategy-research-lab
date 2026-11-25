// Look for a back-adjustment switch on the main series / symbol info (read-only).
import { evaluate, disconnect } from "/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src/connection.js";
import { setSymbolRes } from "./pull_lib.mjs";
await setSymbolRes("CME_MINI:ES1!", "1D");
const out = await evaluate(`(() => {
  const s = window.TradingViewApi._chartWidgetCollection.getAll()[0].model().mainSeries();
  let props = null, si = null;
  try { props = JSON.stringify(s.properties().state ? s.properties().state() : {}).slice(0, 4000); } catch (e) { props = 'err ' + e; }
  try { const info = s.symbolInfo(); si = Object.keys(info).filter(k => /adjust|contract|roll|settle|back|expir|session|type/i.test(k))
          .reduce((o, k) => (o[k] = info[k], o), {}); } catch (e) { si = 'err ' + e; }
  const methods = []; let p = s; for (let d = 0; d < 3 && p; d++) { methods.push(...Object.getOwnPropertyNames(p).filter(k => /adjust|back|settle|contract|roll/i.test(k))); p = Object.getPrototypeOf(p); }
  return { si, methods, propsHasBack: /back|adjust|settle/i.test(props), propsSnippet: (props.match(/.{0,80}(back|adjust|settle).{0,80}/gi) || []).slice(0, 8) };
})()`);
console.log(JSON.stringify(out, null, 1));
await disconnect();
