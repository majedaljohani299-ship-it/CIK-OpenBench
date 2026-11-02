# Checklist before publishing a new public repository

1. Review README, LICENSE (MIT), and every file for confidential or proprietary information. Nothing from existing non-public repositories should be copied.
2. Ensure `python tools/run_tests.py` completes and records nonzero executed tests; try negative tests and the synthetic CLI demo.
3. Create **one** new public GitHub repository. Suggested name: `CIK-OpenBench`. Do not switch the visibility of existing private repos.
4. Upload only this reviewed package, not any private mappings in `out/`. Verify the GitHub public view and Actions results.
5. Show evidence of actual community use and maintenance only after it exists: releases, issues, PR reviews, reproducible adoption; no invented star/download figures.
6. When considering the OpenAI Codex for Open Source application, verify the latest conditions and do not submit confidential details. Program approval is discretionary and a new empty repo alone is insufficient.

## Status at creation

- New local source: created, not an original historic CIK runner
- Offline synthetic tests: execute locally and record results before release
- Real independent model A/B: NOT RUN
- Public repo and adoption: NOT ESTABLISHED
- OpenAI application: NOT SUBMITTED
