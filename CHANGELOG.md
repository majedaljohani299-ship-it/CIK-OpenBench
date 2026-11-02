## 0.2.0 — Position-consistency check (2026-11-02)

- Add optional double-orientation A/B evaluation to identify judgment instability caused by answer position; validate pair matching and fail closed when scores disagree.
- Keep existing one-orientation behavior intact and preserve privacy of original labels in the private key.
- Update GitHub Actions to current Node 24-compatible upstream actions and minimum read-only workflow permissions.
- The tool still does not claim model efficacy or solve factual hallucinations automatically.

# Changelog

## 0.1.2 — 2026-11-02
- Identify the founder publicly as ماجد الجهني, without disclosing private contact details.
- Add explicit public attribution and software citation metadata.
- Ensure CLI-generated outputs use exclusive creation and refuse overwriting existing files.
- Strengthen tests for pre-existing outputs and symlink edge cases.

## 0.1.1 — 2026-11-02
- Private unblinding keys now use exclusive creation and owner-only filesystem permissions where supported.
- CLI refuses to overwrite source or output files during preparation.
- Added negative tests for key permissions, duplicate outputs, and input/output collisions.

## 0.1.0 — 2026-11-02
- Initial original-source, offline blinded A/B packet generator and judgment summarizer.
- Basic structural, integrity, and critical-failure checks.
- Synthetic demo and unit tests only; no real model evaluation.
