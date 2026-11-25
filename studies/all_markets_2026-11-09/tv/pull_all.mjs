// Pull daily history for ~45 continuous futures from the owner's TradingView app (owner's OK 2026-11-09).
// Pass 1: back-adjusted (the owner's own setting). Pass 2: unadjusted. Then restore: back-adjust ON, MGC1!, 5 m.
import fs from "fs";
import { evaluate, disconnect } from "/Users/jitheandrasubramaniam/Desktop/hey hey/tradingview-mcp/src/connection.js";
import { setSymbolRes, loadAll, readBars, state, sleep } from "./pull_lib.mjs";
const OUT = "/Users/jitheandrasubramaniam/Desktop/hey hey/research/all_markets_2026-11-09/tv/data/";
fs.mkdirSync(OUT, { recursive: true });
const P = "window.TradingViewApi._chartWidgetCollection.getAll()[0].model().mainSeries().properties().childs()";
const ORIGINAL = { symbol: "COMEX_MINI:MGC1!", res: "5", backAdj: true };          // as read by probe.mjs
const SYMS = {
  ES: "CME_MINI:ES1!", NQ: "CME_MINI:NQ1!", YM: "CBOT_MINI:YM1!", RTY: "CME_MINI:RTY1!", FDAX: "EUREX:FDAX1!",
  FESX: "EUREX:FESX1!", NKD: "CME:NKD1!",
  ZT: "CBOT:ZT1!", ZF: "CBOT:ZF1!", ZN: "CBOT:ZN1!", ZB: "CBOT:ZB1!", FGBL: "EUREX:FGBL1!",
  "6E": "CME:6E1!", "6J": "CME:6J1!", "6B": "CME:6B1!", "6A": "CME:6A1!", "6C": "CME:6C1!", "6S": "CME:6S1!",
  "6N": "CME:6N1!", "6M": "CME:6M1!", DX: "ICEUS:DX1!",
  CL: "NYMEX:CL1!", NG: "NYMEX:NG1!", HO: "NYMEX:HO1!", RB: "NYMEX:RB1!", BRN: "ICEEUR:BRN1!",
  GC: "COMEX:GC1!", SI: "COMEX:SI1!", HG: "COMEX:HG1!", PL: "NYMEX:PL1!", PA: "NYMEX:PA1!",
  ZC: "CBOT:ZC1!", ZW: "CBOT:ZW1!", ZS: "CBOT:ZS1!", ZM: "CBOT:ZM1!", ZL: "CBOT:ZL1!", KE: "CBOT:KE1!",
  KC: "ICEUS:KC1!", SB: "ICEUS:SB1!", CC: "ICEUS:CC1!", CT: "ICEUS:CT1!", OJ: "ICEUS:OJ1!",
  LE: "CME:LE1!", HE: "CME:HE1!", GF: "CME:GF1!",
};
const log = (m) => { fs.appendFileSync(OUT + "pull.log", `${new Date().toISOString()} ${m}\n`); console.log(m); };
try {
  for (const mode of ["adj", "raw"]) {
    await evaluate(`${P}.backAdjustment.setValue(${mode === "adj"})`);
    await sleep(2500);
    for (const [k, sym] of Object.entries(SYMS)) {
      const f = OUT + `${k}_${mode}.json`;
      if (fs.existsSync(f)) continue;                                     // resume support
      try {
        const st0 = await setSymbolRes(sym, "1D");
        if (!st0 || st0.symbol !== sym || !st0.n) { log(`${k} ${mode}: SKIPPED (chart shows ${st0 && st0.symbol}, ${st0 && st0.n} bars)`); continue; }
        await loadAll(30);
        const ba = await evaluate(`${P}.backAdjustment.value()`);
        const bars = await readBars();
        const st1 = await state();
        if (st1.symbol !== sym || ba !== (mode === "adj")) { log(`${k} ${mode}: SKIPPED (state changed: ${st1.symbol}, backAdj ${ba})`); continue; }
        fs.writeFileSync(f, JSON.stringify({ key: k, symbol: sym, mode, backAdjustment: ba, pulled: new Date().toISOString(), bars }));
        log(`${k} ${mode}: ${bars.length} bars ${new Date(bars[0][0] * 1000).toISOString().slice(0, 10)} -> ${new Date(bars.at(-1)[0] * 1000).toISOString().slice(0, 10)}`);
      } catch (e) { log(`${k} ${mode}: ERROR ${e}`); }
    }
  }
} finally {
  await evaluate(`${P}.backAdjustment.setValue(${ORIGINAL.backAdj})`).catch(() => {});
  await sleep(1500);
  await setSymbolRes(ORIGINAL.symbol, ORIGINAL.res).catch(() => {});
  const fin = await state().catch(() => ({}));
  const ba = await evaluate(`${P}.backAdjustment.value()`).catch(() => null);
  log(`RESTORED chart: ${fin.symbol} ${fin.res}, backAdjustment ${ba}`);
  await disconnect();
}
