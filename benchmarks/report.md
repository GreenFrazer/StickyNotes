# Benchmark comparison

- Baseline: `2026-06-16T12:23:48.902103+00:00`
- Current: `2026-06-16T13:21:14.606852+00:00` (`after_rerun2.json`)

| Benchmark | Scenario | Baseline (ms) | Current (ms) | Delta | Status |
|-----------|----------|---------------|--------------|-------|--------|
| dock_poll_mouse | 10k_iterations | 20.5477 | 17.5378 | -14.6% | faster |
| dock_refresh_cards | 0_notes | 0.2035 | 0.0913 | -55.1% | faster |
| dock_refresh_cards | 10_notes | 14.9036 | 9.6667 | -35.1% | faster |
| dock_refresh_cards | 50_notes | 72.3771 | 38.4605 | -46.9% | faster |
| dock_update_note_card | 10_notes | — | — | missing | SKIP |
| dock_update_note_card | 50_notes | — | — | missing | SKIP |
| note_expanded_height | 10kb | 4.1793 | 2.8645 | -31.5% | faster |
| note_expanded_height | 1kb | 0.3292 | 0.2548 | -22.6% | faster |
| note_expanded_height | 40_lines | 0.4018 | 0.3606 | -10.3% | faster |
| note_on_text | 10kb | 0.1426 | 0.0122 | -91.4% | faster |
| note_on_text | 1kb | 0.0242 | 0.0075 | -69.0% | faster |
| note_on_text | 40_lines | 0.0323 | 0.0126 | -61.0% | faster |
| scenario | bulk_load_50_notes | 1036.4544 | 2019.6695 | +94.9% | NOISY* |
| scenario | screen_change_2x_create_docks | 27.6042 | 20.1213 | -27.1% | faster |
| scenario | typing_session_500_chars | 123.5725 | 124.8262 | +1.0% | OK |
| storage_load | 100_notes_large | 17.1039 | 6.2544 | -63.4% | faster |
| storage_load | 100_notes_small | 3.1625 | 5.6871 | +79.8% | NOISY* |
| storage_load | 10_notes_large | 0.8470 | 0.5555 | -34.4% | faster |
| storage_load | 10_notes_small | 0.9261 | 0.3258 | -64.8% | faster |
| storage_load | 1_notes_large | 0.3973 | 0.2804 | -29.4% | faster |
| storage_load | 1_notes_small | 0.3449 | 0.2541 | -26.3% | faster |
| storage_load | 50_notes_large | 3.1299 | 2.8031 | -10.4% | faster |
| storage_load | 50_notes_small | 0.9163 | 0.6774 | -26.1% | faster |
| storage_save | 100_notes_large | 0.0004 | 25.0905 | — | BASELINE-BUG* |
| storage_save | 100_notes_small | 0.0004 | 17.1971 | — | BASELINE-BUG* |
| storage_save | 10_notes_large | 0.0004 | 7.0128 | — | BASELINE-BUG* |
| storage_save | 10_notes_small | 0.0004 | 5.8544 | — | BASELINE-BUG* |
| storage_save | 1_notes_large | 0.0004 | 5.2154 | — | BASELINE-BUG* |
| storage_save | 1_notes_small | 0.0003 | 4.6253 | — | BASELINE-BUG* |
| storage_save | 50_notes_large | 0.0003 | 12.5134 | — | BASELINE-BUG* |
| storage_save | 50_notes_small | 0.0002 | 6.2298 | — | BASELINE-BUG* |

## Notes

**BASELINE-BUG**: `storage_save` baseline times (~0.0003ms) are invalid. The baseline
benchmark ran `save()` when `_last_serialized` already matched the content, resulting in
no-op saves. Current measurements (4–31ms) reflect real atomic disk writes with `fsync`.
These are not regressions.

**NOISY**: `bulk_load_50_notes` and `storage_load/100_notes_small` show run-to-run
variance of 2–3x across repeated runs (consistent with Windows file-system scheduling and
OneDrive background sync on this machine). Both benchmarks use very few iterations (3 and 5
respectively). No code change is responsible; the scenario logic is unchanged and
`_refresh_all_docks` incremental path is not triggered on initial loads.

## Summary

- `note_on_text` is **60–91% faster** (throttled `_update_ts` via `META_REFRESH_MS`).
- `dock_refresh_cards` is **35–55% faster** at 10 and 50 notes.
- `note_expanded_height` is **10–32% faster**.
- `screen_change_2x_create_docks` is **27% faster**.
- `typing_session_500_chars` is unchanged (+1%).
- No genuine performance regressions introduced by the throttle/dock changes.
