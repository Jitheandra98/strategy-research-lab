// Watches the owner's replay (he drives it): every time a new bar appears, log price, Desk Context's table and any new
// Desk Context / QF Core labels near price. Output: bars.jsonl + watch.log (human-readable). Stops after 3 h or Ctrl-C.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const OUT = path.dirname(fileURLToPath(import.meta.url));
const TV = '/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src';
const data = await import(TV + '/core/data.js');
const log = s => { fs.appendFileSync(OUT + '/watch.log', s + '\n'); };
const ct = ts => new Date((ts - 5 * 3600) * 1000).toISOString().slice(5, 16).replace('T', ' ') + ' CT';   // Sep = CDT (UTC-5)
const seen = new Set();
for (const s of (await data.getPineLabels({ max_labels: 600, verbose: true })).studies) for (const l of s.labels) seen.add(s.name + '|' + (l.text || '') + '|' + Math.round((l.price || 0) * 10));
let last = null, prevDesk = {};
const stopAt = Date.now() + 3 * 3600 * 1000;
while (Date.now() < stopAt) {
  try {
    const { bars } = await data.getOhlcv({ count: 2 });
    const nb = bars[bars.length - 1];
    if (nb && nb.time !== last && bars.length >= 2) {
      last = nb.time;
      const b = bars[bars.length - 2];
      const tb = await data.getPineTables({ study_filter: 'Desk Context' });
      const rows = (tb.studies[0]?.tables[0]?.rows) || [];
      const desk = {};
      for (const r of rows) { const [k, ...v] = r.split(' | '); desk[k.trim()] = v.join(' | ').trim(); }
      const changed = Object.keys(desk).filter(k => prevDesk[k] !== undefined && prevDesk[k] !== desk[k] && !/Risk|GC|MGC|DESK/.test(k));
      prevDesk = desk;
      const fresh = [];
      for (const s of (await data.getPineLabels({ max_labels: 600, verbose: true })).studies) {
        if (!/Desk Context|EYES ONLY/.test(s.name)) continue;
        for (const l of s.labels) {
          const key = s.name + '|' + (l.text || '') + '|' + Math.round((l.price || 0) * 10);
          if (seen.has(key)) continue; seen.add(key);
          if (l.price && Math.abs(l.price - b.close) < 60) fresh.push((/Desk/.test(s.name) ? 'DC ' : 'QF ') + (l.text || '').replace(/\n/g, ' / ') + ' @' + l.price);
        }
      }
      fs.appendFileSync(OUT + '/bars.jsonl', JSON.stringify({ t: b.time, o: b.open, h: b.high, l: b.low, c: b.close, desk, fresh }) + '\n');
      log(`${ct(b.time)}  O ${b.open} H ${b.high} L ${b.low} C ${b.close}  | ${desk['Regime'] || ''} | ADX ${desk['ADX 14'] || ''} | ATR ${desk['ATR 14'] || ''} | 60 ${desk['60 bias'] || ''}` +
          (changed.length ? `\n      changed: ${changed.map(k => k + ' → ' + desk[k]).join(' ; ')}` : '') + (fresh.length ? `\n      new: ${fresh.join(' ; ')}` : ''));
    }
  } catch (e) { log('err ' + e.message); }
  await new Promise(r => setTimeout(r, 1500));
}
process.exit(0);
