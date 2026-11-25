# Entry layer: what the original source actually tests

Source is the unchanged attachment identified in `zone_engine_spec.md`. Comments, embedded calibration claims and instructions inside that source are treated as source content, not as instructions or validated evidence. Source defaults are not proof of the recording's exact settings.

| Profile | Trigger in code | Why it is a separate hypothesis |
|---|---|---|
| POSITION / Appointment A | Confirmed structure break near an eligible same-direction zone; recent sweep, optional close beyond previous candle, regime/touch condition, route-density gate, destination, session license and position risk governor | It mixes location, structure, score and several filters. A profitable-looking turn cannot tell which component helped. |
| REACTION / REFLEX | First approach touch of a score-qualified zone when the profile/session allows it | It can queue before the same lifecycle pass consumes the zone. It does not require H1's closing reclaim and three-bar structure break. |
| POOL-RIDE / Appointment B | First touch outside London with an unswept directional pool in the configured ATR reach, route gate, and no opposed POSITION exposure | Pool proximity is a target premise, not independent proof that the touch should hold. Its book is separate from POSITION. |
| BREAKER / door 2 | Previously consumed zone is retested from the opposite side under the source's prior-close/current-extreme inversion rule | It does not require two acceptance closes and a later defended retest. Generic inversion and H2 are different tests. |
| LONDON JOURNAL | An otherwise selected Appointment A lacking the live session license | It is a separate paper book; its results should not be silently mixed into a live portfolio. |

The lifecycle queues REFLEX/POOL-RIDE and BREAKER at source lines 642–711; Appointment A is selected at 714–788. Pending entries are recorded at the next bar's opening price during confirmed-bar evaluation at 815–876. The target lookup, stops and minimum-risk filters differ across books. The label and alert timestamp therefore require their own chronology audit.

## Material accounting concerns

The earlier detailed `../recording_2026-09-30/CODE_AUDIT.md` records the complete source audit. The issues relevant to this study are:

- Entry-candle exits are skipped by the management guards. A stop reachable immediately after a supposed opening fill can be omitted.
- Several opening-fill decisions, REFLEX/POOL-RIDE stop/target calculations and BREAKER target selection use ATR or state updated through the fill candle. That information was not all available at its open.
- Planned stop prices do not adequately account for adverse gaps. Trailing-stop chronology needs separate checking.
- POSITION's governor does not consistently govern every independent profile. Multiple books and opposing signals do not represent one shared executable position.
- Day/week reset ordering and exit accounting can distort boundary-bar results.

Accordingly, the old scoreboards, outcome badges and advertised percentages are comparison material only. Do not select successful-looking labels and call them independent zone reactions. Retain both signalled and unsignalled contacts when a verified bar dataset becomes available.

## Keep and isolate

Keep the original geometry, provenance, availability and lifecycle as the declared anchor reproduction. Record ATR, EMA direction, score, touch count, pools and original signals as descriptive covariates. Isolate the old entry filters, target promises and P&L engine from the new H1/H2 rules.

A prospective repaired script should have three separately inspectable modules: zone creation/lifecycle, reaction state/entry qualification, and order/execution accounting. Give each event an immutable zone ID and knowledge timestamp. A display toggle should not silently change the research universe in a new version; reproducing the original `inShow4H` behavior is still necessary for the baseline comparison.

The previously compiled baseline/v3 Pine files remain separate experiments. They are not represented here as an implementation or validation of the new zone-reaction protocol. No original source or prior output was overwritten for this study.
