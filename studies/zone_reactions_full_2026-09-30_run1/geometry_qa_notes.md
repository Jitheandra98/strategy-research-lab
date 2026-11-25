# Geometry extraction quality notes

This detector is a candidate generator. Its `high` and `medium` geometry labels describe line-support heuristics; neither certifies a source-engine zone or its trading value.

Calibration frames were reviewed at 0, 480, 600, 3480, 5010, 7200, 10800 and 11400 recording seconds. Axis mapping uses at least five inlier price ticks, rejects implausible/OCR-mangled numbers, fits linear and log alternatives and records residuals. The right pane frequently needs log mapping.

Earlier detector versions paired unrelated edges in overlapping regions. Version 4 adds narrow vertical-border contrast checks. For example, it removes the incorrectly truncated 4H supply candidate at 7200 seconds that version 3 paired from an outer edge and an internal overlap boundary. It still misses the genuine broad supply rectangle there; the manual screenshot therefore has its own approximate bounds.

`geometry_qa_sample.csv` and the five `geometry_qa_page_*.jpg` sheets retain a reproducible 20-observation sample from the **pilot version 3** output, seed 20260930. They show both recognizable boxes and ambiguous interior strips. They are diagnostic material, not a final-version accuracy estimate. Some labels/borders remain unreadable and source-ID correctness cannot be certified from these crops.

Remaining examples of concern include narrow internal blue strips at 5010/11400 seconds and overlapping green regions at 3480/10800 seconds. A strong colored vertical line can be shared by several boxes; a correct pixel-to-price fit does not resolve the pairing. These candidates remain explicitly unverified in the exported dataset and do not enter any claimed performance statistic.

No recall estimate is available because a complete independently labelled source-zone ground truth was not supplied. Faint, inverted, consumed, clipped and occluded zones are undercovered. Scene refinements improve visual coverage, but cannot reconstruct market bars skipped by the accelerated replay.

The eight numbered descriptive screenshots are separate from these diagnostic QA sheets. Their captions state what was visually observed and what cannot be inferred about an executable trade.
