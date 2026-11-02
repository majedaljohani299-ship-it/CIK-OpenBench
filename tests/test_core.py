import copy
import os
import tempfile
from pathlib import Path
import unittest

from cik_openbench import BenchError, evaluate, prepare
from cik_openbench.__main__ import main as cli_main
from cik_openbench.core import write_private_json
from cik_openbench.core import sha256

SAMPLE = {"schema_version": "0.1", "study_id": "synthetic-demo", "pairs": [
    {"pair_id": "S1", "case_id": "C1", "baseline": "2", "treatment": "4"},
    {"pair_id": "S2", "case_id": "C2", "baseline": "No", "treatment": "Yes"},
    {"pair_id": "S3", "case_id": "C3", "baseline": "Alpha", "treatment": "Beta"},
]}


def results(entries):
    return {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(prepare(SAMPLE, seed=7)[0]), "judgments": entries}


class BenchTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.key = prepare(SAMPLE, seed=7)

    def test_private_key_file_is_not_world_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "key.json"
            write_private_json(path, {"key": "synthetic-test-only"})
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(BenchError, "new, unused path"):
                write_private_json(path, {"key": "replacement"})
            self.assertIn("synthetic-test-only", path.read_text())

    def test_cli_prevents_overwriting_inputs_or_private_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "pairs.json"
            input_path.write_text(__import__("json").dumps(SAMPLE))
            packet = Path(tmp) / "packet.json"
            key = Path(tmp) / "key.json"
            self.assertEqual(cli_main(["prepare", "--input", str(input_path), "--packet", str(packet), "--key", str(key), "--seed", "7"]), 0)
            self.assertEqual(cli_main(["prepare", "--input", str(input_path), "--packet", str(packet), "--key", str(key), "--seed", "7"]), 2)
            self.assertEqual(cli_main(["prepare", "--input", str(input_path), "--packet", str(input_path), "--key", str(Path(tmp)/"other.json")]), 2)
            self.assertFalse((Path(tmp) / "other.json").exists())

    def test_cli_score_refuses_overwrite_and_input_alias(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.json"
            key = root / "key.json"
            judgment = root / "judgments.json"
            packet.write_text(json.dumps(self.packet))
            key.write_text(json.dumps(self.key))
            judgment.write_text(json.dumps(results([
                {"pair_id": "S1", "winner": "A"},
                {"pair_id": "S2", "winner": "B"},
                {"pair_id": "S3", "winner": "tie"},
            ])))
            report = root / "report.json"
            args = ["score", "--packet", str(packet), "--key", str(key), "--judgments", str(judgment), "--report", str(report)]
            self.assertEqual(cli_main(args), 0)
            self.assertEqual(cli_main(args), 2)
            self.assertIn("EVALUATED_NO_EFFICACY_CLAIM", report.read_text())
            alias_args = args[:-1] + [str(key)]
            self.assertEqual(cli_main(alias_args), 2)
            self.assertIn("packet_sha256", key.read_text())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks not supported")
    def test_cli_prepare_rejects_dangling_symlink_packet(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "input.json"
            inp.write_text(json.dumps(SAMPLE))
            p = root / "packet.json"
            target = root / "other.json"
            p.symlink_to(target)
            key = root / "key.json"
            status = cli_main(["prepare", "--input", str(inp), "--packet", str(p), "--key", str(key), "--seed", "7"])
            self.assertEqual(status, 2)
            self.assertFalse(target.exists())
            self.assertFalse(key.exists())

    def test_counterbalance_produces_opposite_orders_and_private_metadata(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        self.assertEqual(len(packet["pairs"]), 2 * len(SAMPLE["pairs"]))
        self.assertEqual(len(key["counterbalance_groups"]), len(SAMPLE["pairs"]))
        self.assertNotIn("counterbalance_groups", packet)
        self.assertEqual((packet, key), prepare(SAMPLE, seed=7, counterbalance=True))
        by_id = {p["pair_id"]: p for p in packet["pairs"]}
        for g in key["counterbalance_groups"]:
            a, b = by_id[g["first"]], by_id[g["swapped"]]
            self.assertEqual(a["response_a"], b["response_b"])
            self.assertEqual(a["response_b"], b["response_a"])
            self.assertEqual(a["case_id"], b["case_id"])
        self.assertTrue(set(by_id).isdisjoint({p["pair_id"] for p in SAMPLE["pairs"]}))

    def test_counterbalance_stable_judge_remains_no_efficacy_claim(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        entries = []
        for p in packet["pairs"]:
            labels = key["mapping"][p["pair_id"]]
            # Same underlying treatment wins regardless of left/right placement.
            winner = next(k for k, v in labels.items() if v == "treatment")
            entries.append({"pair_id": p["pair_id"], "winner": winner})
        report = evaluate(packet, key, {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": entries})
        self.assertEqual(report["status"], "EVALUATED_NO_EFFICACY_CLAIM")
        self.assertEqual(report["position_inconsistencies"], [])
        self.assertEqual(report["counterbalance_groups"], 3)

    def test_counterbalance_detects_left_side_preference(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        entries = [{"pair_id": p["pair_id"], "winner": "A"} for p in packet["pairs"]]
        report = evaluate(packet, key, {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": entries})
        self.assertEqual(report["status"], "BLOCKED_POSITION_INCONSISTENCY")
        self.assertEqual(len(report["position_inconsistencies"]), 3)

    def test_counterbalance_mixed_tie_and_winner_flags_instability(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        entries = [{"pair_id": p["pair_id"], "winner": "tie"} for p in packet["pairs"]]
        entries[0]["winner"] = "A"
        report = evaluate(packet, key, {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": entries})
        self.assertEqual(report["status"], "BLOCKED_POSITION_INCONSISTENCY")
        self.assertEqual(len(report["position_inconsistencies"]), 1)

    def test_counterbalance_missing_judgment_blocks_first(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        entries = [{"pair_id": p["pair_id"], "winner": "A"} for p in packet["pairs"][:-1]]
        report = evaluate(packet, key, {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": entries})
        self.assertEqual(report["status"], "BLOCKED_INCOMPLETE")

    def test_counterbalance_corrupted_pair_rejected(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        bad = copy.deepcopy(packet)
        by_id = {p["pair_id"]: p for p in bad["pairs"]}
        by_id[key["counterbalance_groups"][0]["swapped"]]["response_a"] = "tampered"
        key2 = copy.deepcopy(key)
        key2["packet_sha256"] = sha256(bad)
        doc = {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(bad), "judgments": []}
        with self.assertRaisesRegex(BenchError, "exact reversed"):
            evaluate(bad, key2, doc)

    def test_counterbalance_private_mode_cannot_be_silently_dropped(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        bad_key = copy.deepcopy(key)
        bad_key.pop("counterbalance_groups")
        doc = {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": []}
        with self.assertRaisesRegex(BenchError, "mode or private groups missing"):
            evaluate(packet, bad_key, doc)

    def test_counterbalance_incomplete_group_mapping_rejected(self):
        packet, key = prepare(SAMPLE, seed=7, counterbalance=True)
        bad_key = copy.deepcopy(key)
        bad_key["counterbalance_groups"].pop()
        doc = {"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": []}
        with self.assertRaisesRegex(BenchError, "cover every"):
            evaluate(packet, bad_key, doc)

    def test_cli_counterbalance_end_to_end(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp, packet_path, key_path, judge_path, report_path = [root / x for x in ("input.json", "packet.json", "key.json", "judgments.json", "report.json")]
            inp.write_text(json.dumps(SAMPLE))
            self.assertEqual(cli_main(["prepare", "--input", str(inp), "--packet", str(packet_path), "--key", str(key_path), "--seed", "7", "--counterbalance"]), 0)
            packet = json.loads(packet_path.read_text())
            judge_path.write_text(json.dumps({"schema_version": "0.1", "study_id": "synthetic-demo", "packet_sha256": sha256(packet), "judgments": [{"pair_id": pair["pair_id"], "winner": "A"} for pair in packet["pairs"]]}))
            self.assertEqual(cli_main(["score", "--packet", str(packet_path), "--key", str(key_path), "--judgments", str(judge_path), "--report", str(report_path)]), 2)
            self.assertEqual(json.loads(report_path.read_text())["status"], "BLOCKED_POSITION_INCONSISTENCY")

    def test_reproducible_seed(self):
        self.assertEqual((self.packet, self.key), prepare(SAMPLE, seed=7))

    def test_packet_hides_arm_names(self):
        for p in self.packet["pairs"]:
            self.assertNotIn("baseline", p)
            self.assertNotIn("treatment", p)
        self.assertNotIn("mapping", self.packet)

    def test_zero_pairs_disallowed(self):
        bad = {**SAMPLE, "pairs": []}
        with self.assertRaisesRegex(BenchError, "zero pairs"):
            prepare(bad)

    def test_duplicate_pair_disallowed(self):
        bad = copy.deepcopy(SAMPLE)
        bad["pairs"].append(copy.deepcopy(bad["pairs"][0]))
        with self.assertRaisesRegex(BenchError, "Duplicate pair"):
            prepare(bad)

    def test_no_judgment_is_not_pass(self):
        report = evaluate(self.packet, self.key, results([]))
        self.assertEqual(report["status"], "BLOCKED_INCOMPLETE")
        self.assertEqual(report["judged_pairs"], 0)

    def test_missing_pair_is_blocked(self):
        report = evaluate(self.packet, self.key, results([{"pair_id": "S1", "winner": "A"}]))
        self.assertEqual(report["status"], "BLOCKED_INCOMPLETE")
        self.assertEqual(report["missing_pair_ids"], ["S2", "S3"])

    def test_complete_score_is_not_efficacy_claim(self):
        doc = results([{"pair_id": "S1", "winner": "A"}, {"pair_id": "S2", "winner": "B"}, {"pair_id": "S3", "winner": "tie"}])
        report = evaluate(self.packet, self.key, doc)
        self.assertEqual(report["status"], "EVALUATED_NO_EFFICACY_CLAIM")
        self.assertEqual(report["baseline_wins"] + report["treatment_wins"] + report["ties"], 3)
        self.assertIn("No real-model effectiveness", report["claim"])

    def test_critical_failure_blocks(self):
        doc = results([{"pair_id": "S1", "winner": "A", "critical_failures": ["A"]}, {"pair_id": "S2", "winner": "B"}, {"pair_id": "S3", "winner": "tie"}])
        report = evaluate(self.packet, self.key, doc)
        self.assertEqual(report["status"], "BLOCKED_CRITICAL_FAILURE")
        self.assertEqual(report["baseline_critical_failures"] + report["treatment_critical_failures"], 1)

    def test_bad_labels_rejected(self):
        with self.assertRaisesRegex(BenchError, "winner"):
            evaluate(self.packet, self.key, results([{"pair_id": "S1", "winner": "treatment"}]))

    def test_unknown_pair_rejected(self):
        with self.assertRaisesRegex(BenchError, "Unknown"):
            evaluate(self.packet, self.key, results([{"pair_id": "not-present", "winner": "A"}]))

    def test_mismatched_judgment_packet_rejected(self):
        doc = results([{ "pair_id": "S1", "winner": "A" }])
        doc["packet_sha256"] = "0" * 64
        with self.assertRaisesRegex(BenchError, "Judgments must identify"):
            evaluate(self.packet, self.key, doc)

    def test_duplicate_judgment_rejected(self):
        with self.assertRaisesRegex(BenchError, "duplicate"):
            evaluate(self.packet, self.key, results([{"pair_id": "S1", "winner": "A"}, {"pair_id": "S1", "winner": "A"}]))

    def test_tampered_packet_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["pairs"][0]["response_a"] = "changed after blinding"
        self.assertNotEqual(sha256(packet), self.key["packet_sha256"])
        with self.assertRaisesRegex(BenchError, "checksum"):
            evaluate(packet, self.key, results([]))

    def test_nonboolean_critical_failures_rejected(self):
        with self.assertRaisesRegex(BenchError, "critical_failures"):
            evaluate(self.packet, self.key, results([{"pair_id": "S1", "winner": "tie", "critical_failures": "A"}]))

    def test_study_mismatch_rejected(self):
        with self.assertRaisesRegex(BenchError, "Study ID mismatch"):
            evaluate(self.packet, self.key, {"schema_version": "0.1", "study_id": "other", "packet_sha256": sha256(self.packet), "judgments": []})


if __name__ == "__main__":
    unittest.main()
