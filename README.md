# CIK OpenBench — public-safe experimental benchmark

**Status: prototype (0.1.2), offline tests only; no measured improvement of any AI model.**

CIK stands for *Cognitive Interaction Kernel*. This is a **new, independently written public-facing tool** for evaluating hypotheses about AI output quality with blinded A/B pairs, rather than a release of the unpublished proprietary implementation or datasets, historical runner, or unpublished intellectual property.

**Project founder and public lead: ماجد الجهني**. The name is published with the founder’s express authorization; no personal contact or identification details are included.

## What the tool actually does

- Creates randomized, blinded A/B response packets from baseline/treatment pairs.
- Separates the randomization key from the judging packet; detects packet/key mismatch with SHA-256.
- Summarizes manually submitted judgments only after unblinding with the private key.
- Blocks incomplete or zero-judgment evaluations and flags critical failures.
- Always reports **NO EFFICACY CLAIM**: it does not call a model, establish statistical significance, or prove CIK works.
- Requires no API key, package installation, paid service, or external Python dependency to run.
- Refuses to overwrite pre-existing packet, key, or report paths through the command-line interface, including dangling symbolic links, to avoid accidental data loss.

## Reproduce the synthetic demo

Requires Python 3.10+.

```sh
python tools/run_tests.py
python -m cik_openbench prepare --input examples/synthetic_pairs.json --packet out/blind_packet.json --key out/private_key.json --seed 7
python -m cik_openbench score --packet out/blind_packet.json --key out/private_key.json --judgments examples/synthetic_judgments.json --report out/report.json
```

`out/` is intentionally gitignored. The private key is created with owner-only file permissions on POSIX systems; existing key files are never overwritten. Use fresh output paths for repeated runs. The example responses and judgments are **fabricated demonstrations**, not real model or user data. The demo produces the status `EVALUATED_NO_EFFICACY_CLAIM`; this only means the synthetic records were structurally evaluated without a critical-failure flag. Incomplete records produce `BLOCKED_INCOMPLETE`; critical failures produce `BLOCKED_CRITICAL_FAILURE`.

## Input schema (v0.1)

`pairs.json` has `schema_version`, `study_id`, and nonempty `pairs`, each including `pair_id`, `case_id`, `baseline`, `treatment` as nonempty strings. Distinct `pair_id` is required for repeated trials of the same case. `prepare` outputs an A/B packet and a separate key with SHA-256 for traceability. `judgments.json` has `schema_version`, `study_id`, the exact `packet_sha256` from the blinded packet, and judgments with `pair_id`, `winner` (`A`, `B`, `tie`) and optional `critical_failures` (an array of A/B labels).

## Limitations

- This is not a statistical test or an automatic quality judge. An independent judge and precommitted scoring rubric are required in real studies.
- Blinding is only valid when the judge has no access to the key or original labeled inputs. Do not publish keys or private benchmark materials.
- A hash proves agreement between two specific files, **not** the identity or authenticity of their author, external model, or test run.
- Source data provenance, holdout independence, repeatability across real models, and experimental statistical uncertainty remain to be established separately.
- Public repository creation, GitHub Actions checks, genuine contributors and adoption have **not** been established by this demo.

## Research integrity

No effect of CIK on GPT or another model is asserted. A/B comparisons require genuinely distinct pre-registered treatments and a baseline, controls for leakage, repeated paired trials and an independent holdout. Never replace historical CIK evaluation artifacts with synthetic examples or present generated files as original experimental records.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [docs/PUBLISH_CHECKLIST.md](docs/PUBLISH_CHECKLIST.md). MIT-licensed code written specifically for this starter; review the license terms before public release.
