"""Offline, deliberately conservative blinded-pair evaluation primitives.

This repository does not implement proprietary CIK and makes no efficacy claims.
"""
from __future__ import annotations

import hashlib
import os
import json
import random
import secrets
from pathlib import Path
from typing import Any

SCHEMA = "0.1"


class BenchError(ValueError):
    """Invalid study input, conflicting labels, or invalid evidence."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            doc = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise BenchError("Top-level JSON value must be an object")
    return doc


def write_json(path: str | Path, doc: dict[str, Any]) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as stream:
        json.dump(doc, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def write_private_json(path: str | Path, doc: dict[str, Any]) -> None:
    """Create a private key as a new 0600 file; never overwrite existing paths."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(dest, flags, 0o600)
    except OSError as exc:
        raise BenchError("Private key output must be a new, unused path") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(doc, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise



def write_new_json(path: str | Path, doc: dict[str, Any]) -> None:
    """Create JSON output exclusively. Never replace an existing file or symlink."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(dest, flags, 0o644)
    except OSError as exc:
        raise BenchError("Output must be a new, unused path") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(doc, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

def _required_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchError(f"{field} must be a nonempty string")
    return value


def _check_schema(doc: dict[str, Any]) -> None:
    if doc.get("schema_version") != SCHEMA:
        raise BenchError(f"schema_version must be {SCHEMA!r}")


def validate_pairs(doc: dict[str, Any]) -> list[dict[str, str]]:
    _check_schema(doc)
    _required_nonempty_string(doc.get("study_id"), "study_id")
    pairs = doc.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise BenchError("pairs must contain at least one item (zero pairs cannot pass)")
    seen: set[str] = set()
    validated: list[dict[str, str]] = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            raise BenchError(f"pairs[{index}] must be an object")
        clean = {field: _required_nonempty_string(pair.get(field), f"pairs[{index}].{field}") for field in ("pair_id", "case_id", "baseline", "treatment")}
        if clean["pair_id"] in seen:
            raise BenchError(f"Duplicate pair_id: {clean['pair_id']}")
        seen.add(clean["pair_id"])
        validated.append(clean)
    return validated


def prepare(doc: dict[str, Any], *, seed: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    pairs = validate_pairs(doc)
    random_seed = seed if seed is not None else secrets.randbits(64)
    rng = random.Random(random_seed)
    packet_pairs: list[dict[str, str]] = []
    mapping: dict[str, dict[str, str]] = {}
    for pair in pairs:
        first_is_treatment = bool(rng.getrandbits(1))
        labels = {"A": "treatment", "B": "baseline"} if first_is_treatment else {"A": "baseline", "B": "treatment"}
        mapping[pair["pair_id"]] = labels
        packet_pairs.append({
            "pair_id": pair["pair_id"],
            "case_id": pair["case_id"],
            "response_a": pair[labels["A"]],
            "response_b": pair[labels["B"]],
        })
    packet = {"schema_version": SCHEMA, "study_id": doc["study_id"], "pairs": packet_pairs}
    key = {"schema_version": SCHEMA, "study_id": doc["study_id"], "packet_sha256": sha256(packet), "seed": random_seed, "mapping": mapping}
    return packet, key


def evaluate(packet: dict[str, Any], key: dict[str, Any], judgments: dict[str, Any]) -> dict[str, Any]:
    """Summarize blind judgments. A completed report is NOT evidence of CIK efficacy."""
    _check_schema(packet)
    _check_schema(key)
    _check_schema(judgments)
    study_id = _required_nonempty_string(packet.get("study_id"), "packet.study_id")
    if key.get("study_id") != study_id or judgments.get("study_id") != study_id:
        raise BenchError("Study ID mismatch")
    packet_checksum = sha256(packet)
    if key.get("packet_sha256") != packet_checksum:
        raise BenchError("Packet/key checksum mismatch")
    if judgments.get("packet_sha256") != packet_checksum:
        raise BenchError("Judgments must identify the exact blinded packet SHA-256")

    items = packet.get("pairs")
    if not isinstance(items, list) or not items:
        raise BenchError("Packet must contain at least one pair")
    pair_ids: set[str] = set()
    for ix, pair in enumerate(items):
        if not isinstance(pair, dict):
            raise BenchError(f"packet.pairs[{ix}] must be an object")
        pid = _required_nonempty_string(pair.get("pair_id"), "packet.pair_id")
        _required_nonempty_string(pair.get("response_a"), "packet.response_a")
        _required_nonempty_string(pair.get("response_b"), "packet.response_b")
        if pid in pair_ids:
            raise BenchError(f"Duplicate packet pair_id: {pid}")
        pair_ids.add(pid)
    mappings = key.get("mapping")
    if not isinstance(mappings, dict) or set(mappings) != pair_ids:
        raise BenchError("Invalid key mapping: missing/extra pairs")
    for pid in pair_ids:
        val = mappings[pid]
        if not isinstance(val, dict) or set(val) != {"A", "B"} or set(val.values()) != {"baseline", "treatment"}:
            raise BenchError(f"Invalid key labels for pair {pid}")

    records = judgments.get("judgments")
    if not isinstance(records, list):
        raise BenchError("judgments must be a list")
    seen: set[str] = set()
    stats = {"baseline_wins": 0, "treatment_wins": 0, "ties": 0,
             "baseline_critical_failures": 0, "treatment_critical_failures": 0}
    for ix, entry in enumerate(records):
        if not isinstance(entry, dict):
            raise BenchError(f"judgments[{ix}] must be an object")
        pid = _required_nonempty_string(entry.get("pair_id"), "judgment.pair_id")
        if pid not in pair_ids or pid in seen:
            raise BenchError(f"Unknown or duplicate judgment pair_id: {pid}")
        seen.add(pid)
        winner = entry.get("winner")
        if winner not in ("A", "B", "tie"):
            raise BenchError("winner must be 'A', 'B', or 'tie'")
        failures = entry.get("critical_failures", [])
        if not isinstance(failures, list) or any(not isinstance(label, str) or label not in ("A", "B") for label in failures) or len(set(failures)) != len(failures):
            raise BenchError("critical_failures must be a list of distinct 'A'/'B' labels")
        if winner == "tie":
            stats["ties"] += 1
        else:
            stats[f"{mappings[pid][winner]}_wins"] += 1
        for label in failures:
            stats[f"{mappings[pid][label]}_critical_failures"] += 1

    missing = sorted(pair_ids - seen)
    if missing:
        status = "BLOCKED_INCOMPLETE"
    elif stats["baseline_critical_failures"] or stats["treatment_critical_failures"]:
        status = "BLOCKED_CRITICAL_FAILURE"
    else:
        status = "EVALUATED_NO_EFFICACY_CLAIM"
    return {
        "schema_version": SCHEMA,
        "study_id": study_id,
        "packet_sha256": sha256(packet),
        "status": status,
        "total_pairs": len(pair_ids),
        "judged_pairs": len(seen),
        "missing_pair_ids": missing,
        **stats,
        "claim": "No real-model effectiveness or statistical significance is established by this tool.",
    }
