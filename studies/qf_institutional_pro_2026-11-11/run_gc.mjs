// PineTS runner on GC 5m futures with real volume. usage: node run_gc.mjs <script.pine> <tfMin> <startISO> <endISO> <out.json> [tz]
import { PineTS, Indicator } from '/Users/jitheandrasubramaniam/Desktop/hey hey/trading-video-intel/tools/pine_runner/node_modules/pinets/dist/pinets.min.es.js';
import fs from 'fs';
const [, , scriptPath, tfArg, startIso, endIso, outPath, tzArg] = process.argv;
const TZ = tzArg || 'America/Chicago';
const buf = fs.readFileSync(new URL((process.env.GCFILE || './gc5m7.f64'), import.meta.url));
const A = new Float64Array(buf.buffer, buf.byteOffset, buf.byteLength / 8);
const F = 7, N = A.length / F;
function tfMinutes(tf) {
  const s = String(tf).trim().toUpperCase(); let m;
  if (s === '') return Number(tfArg);
  if ((m = s.match(/^(\d+)$/))) return Number(m[1]);
  if ((m = s.match(/^(\d+)H$/))) return Number(m[1]) * 60;
  if ((m = s.match(/^(\d*)D$/))) return (Number(m[1]) || 1) * 1440;
  if ((m = s.match(/^(\d*)W$/))) return (Number(m[1]) || 1) * 10080;
  return Number(tfArg);
}
function lowerBound(t) { let lo = 0, hi = N; while (lo < hi) { const m = (lo + hi) >> 1; if (A[m * F] < t) lo = m + 1; else hi = m; } return lo; }
const cache = new Map();
function bars(tfMin, sDate, eDate) {
  const key = tfMin + ':' + (sDate || 0) + ':' + (eDate || 0);
  if (!cache.has(key)) {
    const out = []; const ms = tfMin * 60000; let cur = null;
    const i0 = sDate ? lowerBound(sDate) : 0, i1 = eDate ? lowerBound(eDate) : N;
    for (let i = i0; i < i1; i++) {
      const t = A[i * F];
      const b = tfMin >= 1440 ? A[i * F + 6] : Math.floor(t / ms) * ms;   // daily = CME session (18:00 ET open)
      if (!cur || cur.openTime !== b) {
        if (cur) out.push(cur);
        cur = { openTime: b, open: A[i*F+1], high: A[i*F+2], low: A[i*F+3], close: A[i*F+4], volume: A[i*F+5] };
      } else { cur.high = Math.max(cur.high, A[i*F+2]); cur.low = Math.min(cur.low, A[i*F+3]); cur.close = A[i*F+4]; cur.volume += A[i*F+5]; }
    }
    if (cur) out.push(cur);
    for (const k of out) { k.closeTime = k.openTime + (tfMin >= 1440 ? 23 * 3600000 : ms); k.quoteAssetVolume = 0; k.numberOfTrades = 0; k.takerBuyBaseAssetVolume = 0; k.takerBuyQuoteAssetVolume = 0; k.ignore = 0; }
    cache.set(key, out);
  }
  return cache.get(key);
}
const provider = {
  configure() {},
  async getMarketData(tickerId, timeframe, limit, sDate, eDate) {
    const tfm = tfMinutes(timeframe);
    const tk = String(tickerId || '').toUpperCase();
    if (tk && !/MGC|GC|GOLD|XAU/.test(tk)) return [];          // other symbols (DXY) -> na
    const warm = tfm >= 1440 ? 400 * 86400000 : tfm > Number(tfArg) ? 30 * 86400000 : 0;
    return bars(tfm, sDate ? sDate - warm : sDate, eDate);
  },
  async getSymbolInfo() {
    return { current_contract: '', description: 'Micro Gold Futures', isin: '', main_tickerid: 'COMEX:MGC1!', prefix: 'COMEX', root: 'MGC',
      ticker: 'MGC1!', tickerid: 'COMEX:MGC1!', type: 'futures', basecurrency: '', country: 'US', currency: 'USD', timezone: TZ,
      employees: 0, industry: '', sector: '', shareholders: 0, shares_outstanding_float: 0, shares_outstanding_total: 0, expiration_date: 0,
      session: '1800-1700', volumetype: 'base', mincontract: 1, minmove: 1, mintick: 0.1, pointvalue: 10, pricescale: 10,
      recommendations_buy: 0, recommendations_buy_strong: 0, recommendations_date: 0, recommendations_hold: 0, recommendations_sell: 0,
      recommendations_sell_strong: 0, recommendations_total: 0, target_price_average: 0, target_price_date: 0, target_price_estimates: 0,
      target_price_high: 0, target_price_low: 0, target_price_median: 0 };
  },
};
const t0 = Date.now();
let src = fs.readFileSync(scriptPath, 'utf8');
const patches = [];
const rw = (re, to, name) => { const n = (src.match(re) || []).length; if (n) { src = src.replace(re, to); patches.push(`${name} x${n}`); } };
rw(/time\(\s*timeframe\.period\s*,\s*"(?:America|Europe|Asia|Etc|UTC|GMT)[^"]*"\s*\)/g, 'time', 'time(tf, timezone)->time');
const out = { script: scriptPath, patches, tz: TZ };
try {
  const pt = new PineTS(provider, 'COMEX:MGC1!', String(tfArg), undefined, Date.parse(startIso), Date.parse(endIso));
  const ind = new Indicator(src);
  const res = await pt.run(ind);
  out.nbars = (res.marketData || []).length;
  out.values = {}; out.signals = {};
  const md = res.marketData || [];
  const tindex = new Map(md.map((k, i) => [k.openTime, i]));
  const vtitles = Object.keys(res.plots || {}).filter(t => t.startsWith('v_'));
  out.vtitles = vtitles;
  const M = new Float32Array(md.length * vtitles.length).fill(NaN);
  vtitles.forEach((title, j) => { for (const x of (res.plots[title].data || [])) { const i = tindex.get(x.time); if (i !== undefined && x && typeof x.value === 'number' && Number.isFinite(x.value)) M[i * vtitles.length + j] = x.value; } });
  fs.writeFileSync(outPath + '.vals.f32', Buffer.from(M.buffer));
  fs.writeFileSync(outPath + '.times.f64', Buffer.from(new Float64Array(md.map(k => k.openTime)).buffer));
  for (const [title, p] of Object.entries(res.plots || {})) {
    const d = (p.data || []);
    if (title.startsWith('v_')) continue;
    else {
      const hits = d.filter(x => x && x.value !== null && x.value !== undefined && x.value !== false && !(typeof x.value === 'number' && Number.isNaN(x.value)));
      out.signals[title] = { n: hits.length, sample: hits.slice(0, 3).map(x => [x.time, x.value]) };
    }
  }
  out.labels = ((res.plots || {})['__labels__']?.data || []).length;
  out.tables = Object.keys(res.plots || {}).filter(k => k.startsWith('__')).join(',');
} catch (e) { out.error = String(e && e.stack || e).slice(0, 2000); }
out.ms = Date.now() - t0;
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(JSON.stringify({ ms: out.ms, nbars: out.nbars, error: out.error, patches, nvalues: Object.keys(out.values || {}).length, signals: out.signals }, null, 0).slice(0, 3000));
