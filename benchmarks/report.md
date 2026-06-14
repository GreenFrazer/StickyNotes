# Benchmark comparison

- Baseline: `2026-06-14T17:09:44.373818+00:00`
- Current: `2026-06-14T17:09:44.373818+00:00`

| Benchmark | Scenario | Baseline (ms) | Current (ms) | Delta | Status |
|-----------|----------|---------------|--------------|-------|--------|
| dock_poll_mouse | 10k_iterations | 6.1816 | 6.1816 | +0.0% | OK |
| dock_refresh_cards | 0_notes | 0.0020 | 0.0020 | +0.0% | OK |
| dock_refresh_cards | 10_notes | 1.7142 | 1.7142 | +0.0% | OK |
| dock_refresh_cards | 50_notes | 8.6897 | 8.6897 | +0.0% | OK |
| note_expanded_height | 10kb | 3.5782 | 3.5782 | +0.0% | OK |
| note_expanded_height | 1kb | 0.3577 | 0.3577 | +0.0% | OK |
| note_expanded_height | 40_lines | 0.1983 | 0.1983 | +0.0% | OK |
| note_on_text | 10kb | 0.0201 | 0.0201 | +0.0% | OK |
| note_on_text | 1kb | 0.0052 | 0.0052 | +0.0% | OK |
| note_on_text | 40_lines | 0.0046 | 0.0046 | +0.0% | OK |
| scenario | bulk_load_50_notes | 1296.8232 | 1296.8232 | +0.0% | OK |
| scenario | screen_change_2x_create_docks | 5.2192 | 5.2192 | +0.0% | OK |
| scenario | typing_session_500_chars | 50.2489 | 50.2489 | +0.0% | OK |
| storage_load | 100_notes_large | 1.6540 | 1.6540 | +0.0% | OK |
| storage_load | 100_notes_small | 0.5568 | 0.5568 | +0.0% | OK |
| storage_load | 10_notes_large | 0.1975 | 0.1975 | +0.0% | OK |
| storage_load | 10_notes_small | 0.0910 | 0.0910 | +0.0% | OK |
| storage_load | 1_notes_large | 0.0511 | 0.0511 | +0.0% | OK |
| storage_load | 1_notes_small | 0.0408 | 0.0408 | +0.0% | OK |
| storage_load | 50_notes_large | 0.8360 | 0.8360 | +0.0% | OK |
| storage_load | 50_notes_small | 0.2897 | 0.2897 | +0.0% | OK |
| storage_save | 100_notes_large | 0.0003 | 0.0003 | +0.0% | OK |
| storage_save | 100_notes_small | 0.0002 | 0.0002 | +0.0% | OK |
| storage_save | 10_notes_large | 0.0003 | 0.0003 | +0.0% | OK |
| storage_save | 10_notes_small | 0.0002 | 0.0002 | +0.0% | OK |
| storage_save | 1_notes_large | 0.0002 | 0.0002 | +0.0% | OK |
| storage_save | 1_notes_small | 0.0002 | 0.0002 | +0.0% | OK |
| storage_save | 50_notes_large | 0.0002 | 0.0002 | +0.0% | OK |
| storage_save | 50_notes_small | 0.0002 | 0.0002 | +0.0% | OK |

**Result: PASS** — no scenario regressed beyond threshold.
