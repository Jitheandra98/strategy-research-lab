# Input and data inventory

Video: 03:36:53.12, 2560×1440, approximately 59.16 fps, 14,740,561,000 bytes. FFmpeg metadata is retained in `video_metadata.txt`. `ffprobe` was not installed; the available FFmpeg binary supplied the container/stream metadata. Original video and indicator were not changed.

Chart: MGC1!, COMEX, 5M left and 4H right. MGCZ2026 axis tags, ETH and B-ADJ are visible. These identify chart context, not a verified execution contract through every historical bar. The filename is a recording date, not the market-history range.

## Existing local OHLC files

| File | Bars | First UTC | Last UTC | OHLC values off 0.10 grid |
|---|---:|---|---|---:|
| recorder_5m_1744bars.json | 1744 | 2026-07-27T15:30:00+00:00 | 2026-08-04T23:45:00+00:00 | 95.0% |
| recorder_30m_5174bars.json | 5174 | 2026-01-29T21:30:00+00:00 | 2026-08-04T06:30:00+00:00 | 47.0% |

These files have no verified MGC instrument/feed/adjustment provenance in their bar records. The short 5M period cannot cover the replay. Tick-grid inconsistency is a data-quality flag requiring explanation, not proof of the instrument by itself. They were not substituted for the replay or used to report MGC returns. JSONL recorder samples also exist, but do not supply a verified complete replay-matched feed merely by their filenames.

No verified full-period 5M OHLCV export was supplied. Therefore market-clock MFE/MAE, entry/exit order, costs, independent opportunity frequency and net expectancy cannot be established by this study. The video-derived quote table remains separate from all raw market data.

## Tool outputs and audit trail

- `frame_index.csv`: all 2,604 baseline sample frames.
- `scene_frame_index.csv`: 544 extra frames around 136 sampled visual-change candidates.
- `all_frame_index.csv`: merged time index, once final tables are built.
- `ocr_fast`, `ocr`, `ocr_axes`: raw OCR outputs.
- `ocr_merged`: provenance-preserving merged observations.
- `fullspan_*`: complete parser output, including rejected/unresolved geometry candidates.
- `zones.csv`: frame-level candidates with provisional screen-track IDs.
- `events.csv`: screen transitions plus separately labelled manual descriptive examples.

All frame timestamps are recording offsets. No crosshair timestamp or currently hovered header OHLC is silently assigned to the latest replay bar. Audio was not transcribed; it was not used as trading evidence.
