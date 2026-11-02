# CIK OpenBench — public-safe experimental benchmark

**Status: prototype (0.2.0), offline tests only; no measured improvement of any AI model.**

CIK stands for *Cognitive Interaction Kernel*. This is a **new, independently written public-facing tool** for evaluating hypotheses about AI output quality with blinded A/B pairs, rather than a release of the unpublished proprietary implementation or datasets, historical runner, or unpublished intellectual property.

**Project founder and public lead: ماجد الجهني**. The name is published with the founder’s express authorization; no personal contact or identification details are included.

## What the tool actually does

- Creates randomized, blinded A/B response packets from baseline/treatment pairs.
- Optionally tests **judge position consistency** by showing both A/B orientations without disclosing the baseline/treatment mapping.
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

## Optional: check whether order changes the judge's decision

A common problem with human or AI judges is *position bias*: choosing the first or second answer because of placement rather than merit. Run:

```sh
python -m cik_openbench prepare --input examples/synthetic_pairs.json --packet out/cb_packet.json --key out/cb_private_key.json --seed 7 --counterbalance
```

This creates **two opposite orientations per input pair** (six blinded comparisons from three inputs), shuffles their order, and saves the pair relationships **only in the private key** (the packet only marks the counterbalanced mode). The evaluator must independently supply one judgment for **each packet pair ID** using the normal `judgments.json` format and packet checksum. When scoring, the tool detects disagreements between the two orientations and returns `BLOCKED_POSITION_INCONSISTENCY`. Both orientations choosing the *same underlying response* (or both a tie) counts as stable. Incomplete evaluations and critical failures still block scoring first.

**Limitations:** The 2× observations are not independent samples. Swapped copies may be recognizable to a judge, and a consistent judgment is *not* proof of factual accuracy, absence of bias, statistical significance, or benefit from CIK. This feature is an optional stability diagnostic, not a substitute for independent raters, controls, or real model experiments. Never publish the private mapping key or sensitive responses.

## Input schema (v0.1)

`pairs.json` has `schema_version`, `study_id`, and nonempty `pairs`, each including `pair_id`, `case_id`, `baseline`, `treatment` as nonempty strings. Distinct `pair_id` is required for repeated trials of the same case. `prepare` outputs an A/B packet and a separate key with SHA-256 for traceability. `judgments.json` has `schema_version`, `study_id`, the exact `packet_sha256` from the blinded packet, and judgments with `pair_id`, `winner` (`A`, `B`, `tie`) and optional `critical_failures` (an array of A/B labels).

## Limitations

- This is not a statistical test or an automatic quality judge. An independent judge and precommitted scoring rubric are required in real studies.
- Blinding is only valid when the judge has no access to the key or original labeled inputs. Do not publish keys or private benchmark materials.
- A hash proves agreement between two specific files, **not** the identity or authenticity of their author, external model, or test run.
- Source data provenance, holdout independence, repeatability across real models, and experimental statistical uncertainty remain to be established separately.
- Public repository and initial CI runs have been verified; independent adoption, genuine external use, and real-model efficacy **have not** been established by this demo.

## Research integrity

No effect of CIK on GPT or another model is asserted. A/B comparisons require genuinely distinct pre-registered treatments and a baseline, controls for leakage, repeated paired trials and an independent holdout. Never replace historical CIK evaluation artifacts with synthetic examples or present generated files as original experimental records.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [docs/PUBLISH_CHECKLIST.md](docs/PUBLISH_CHECKLIST.md). MIT-licensed code written specifically for this starter; review the license terms before public release.
