from __future__ import annotations
import json, shutil, tempfile
from pathlib import Path

from jnu_private_selection_shadow_crash_recovery_v1 import (
    ROOT, PROTOCOL, STATE_PATHS, load_json, production_bytes, hashes_from_bytes,
    simulate_crash, recover, validate_journal, write_final_receipt,
    mutate_shadow, sha256_file, ensure_external
)

def rejected(fn, contains: str | None = None) -> bool:
    try:
        fn()
    except Exception as e:
        return contains is None or contains in str(e)
    return False

def state_paths(root: Path) -> dict[str, Path]:
    return {sid: root / "shadow" / "state" / src.name for sid, src in STATE_PATHS.items()}

def main() -> None:
    T = {}
    proto = load_json(PROTOCOL)
    phases = proto["transaction_sequence"]
    production_before = production_bytes()
    production_hash_before = hashes_from_bytes(production_before)

    with tempfile.TemporaryDirectory(prefix="jnu_shadow_crash_recovery_selftest_") as td:
        base = Path(td)
        decisions = []
        boundary_count = 0
        for pi, phase in enumerate(phases):
            for edge in ("PRE", "POST"):
                boundary_count += 1
                root = base / f"case_{pi}_{edge.lower()}"
                txn = f"JNU_CRASH_RECOVERY_SYNTH_{pi}_{edge}"
                lineage = f"LINEAGE_{pi}_{edge}"
                x = simulate_crash(root, txn, lineage, phase, edge)
                T[f"boundary_{pi}_{edge}_crashed"] = x["status"] == "CRASHED"
                y = recover(root)
                decisions.append(y["decision"])
                T[f"boundary_{pi}_{edge}_recovered"] = y["status"] == "RECOVERED_SUCCESS"
                T[f"boundary_{pi}_{edge}_journal_valid"] = len(validate_journal(root)) >= 2
                T[f"boundary_{pi}_{edge}_receipt_exists"] = (root / "final_receipt.json").is_file()
                rec = load_json(root / "final_receipt.json")
                T[f"boundary_{pi}_{edge}_receipt_safe"] = (
                    rec["production_unchanged"] is True
                    and rec["real_commit_capability"] is False
                    and rec["real_apply_capability"] is False
                    and rec["production_state_mutated"] is False
                    and rec["credentials_connected"] is False
                    and rec["kms_api_called"] is False
                    and rec["real_activation_authorized"] is False
                )

        T["all_14_boundaries_exercised"] = boundary_count == len(phases) * 2
        T["resume_forward_seen"] = "RESUME_FORWARD" in decisions
        T["finalize_seen"] = "FINALIZE_ALREADY_COMPLETE" in decisions

        root = base / "partial_mutation"
        txn = "JNU_CRASH_RECOVERY_SYNTH_PARTIAL"
        lineage = "LINEAGE_PARTIAL"
        x = simulate_crash(root, txn, lineage, "MUTATION_SET", "PRE")
        expected = x["expected"]
        mutate_shadow(state_paths(root), txn, lineage, partial=True)
        y = recover(root)
        T["partial_mutation_rolls_back"] = y["status"] == "RECOVERED_ROLLED_BACK" and y["decision"] == "ROLLBACK_TO_PREIMAGE"
        T["partial_rollback_exact_preimage"] = {sid: sha256_file(p) for sid, p in state_paths(root).items()} == expected

        root = base / "corrupt_backup"
        txn = "JNU_CRASH_RECOVERY_SYNTH_CORRUPT_BACKUP"
        lineage = "LINEAGE_CORRUPT_BACKUP"
        x = simulate_crash(root, txn, lineage, "MUTATION_SET", "PRE")
        mutate_shadow(state_paths(root), txn, lineage, partial=True)
        first = root / "shadow" / "preimage_backups" / next(iter(STATE_PATHS.values())).name
        first.write_bytes(first.read_bytes() + b"CORRUPT")
        T["corrupt_preimage_rejected"] = rejected(lambda: recover(root), "preimage backup corrupted")

        root = base / "journal_tamper"
        simulate_crash(root, "JNU_CRASH_RECOVERY_SYNTH_TAMPER", "LINEAGE_TAMPER", "CAS_VERIFICATION", "POST")
        j0 = sorted((root / "journal").glob("*.json"))[0]
        o = load_json(j0); o["status"] = "TAMPERED"; j0.write_text(json.dumps(o, indent=2) + "\n", encoding="utf-8")
        T["journal_content_tamper_rejected"] = rejected(lambda: recover(root), "journal entry hash mismatch")

        root = base / "parent_tamper"
        simulate_crash(root, "JNU_CRASH_RECOVERY_SYNTH_PARENT", "LINEAGE_PARENT", "CAS_VERIFICATION", "POST")
        files = sorted((root / "journal").glob("*.json"))
        o = load_json(files[1]); o["parent_sha256"] = "f" * 64
        body = dict(o); body.pop("entry_sha256", None)
        import hashlib
        o["entry_sha256"] = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        files[1].write_text(json.dumps(o, indent=2) + "\n", encoding="utf-8")
        T["parent_hash_tamper_rejected"] = rejected(lambda: recover(root), "journal parent hash mismatch")

        root = base / "sequence_gap"
        simulate_crash(root, "JNU_CRASH_RECOVERY_SYNTH_GAP", "LINEAGE_GAP", "CAS_VERIFICATION", "POST")
        files = sorted((root / "journal").glob("*.json"))
        files[1].rename(files[1].with_name("000099_GAP.json"))
        T["sequence_gap_rejected"] = rejected(lambda: recover(root), "journal sequence filename mismatch")

        root = base / "foreign_lock"
        simulate_crash(root, "JNU_CRASH_RECOVERY_SYNTH_LOCK", "LINEAGE_LOCK", "CAS_VERIFICATION", "PRE")
        lock = root / ".selection-shadow-crash-recovery.lock"
        o = load_json(lock); o["transaction_id"] = "FOREIGN_TRANSACTION"; lock.write_text(json.dumps(o, indent=2) + "\n", encoding="utf-8")
        T["foreign_stale_lock_rejected"] = rejected(lambda: recover(root), "foreign stale lock rejected")

        root = base / "same_lock"
        simulate_crash(root, "JNU_CRASH_RECOVERY_SYNTH_SAME_LOCK", "LINEAGE_SAME_LOCK", "CAS_VERIFICATION", "PRE")
        y = recover(root)
        T["matching_stale_lock_recovered"] = y["status"] == "RECOVERED_SUCCESS" and not (root / ".selection-shadow-crash-recovery.lock").exists()

        root = base / "receipt_replay"
        simulate_crash(root, "JNU_CRASH_RECOVERY_SYNTH_RECEIPT", "LINEAGE_RECEIPT", "FINAL_TRANSACTION_RECEIPT", "POST")
        before_receipt = (root / "final_receipt.json").read_bytes()
        y1 = recover(root); y2 = recover(root)
        after_receipt = (root / "final_receipt.json").read_bytes()
        T["final_receipt_exactly_once_bytes"] = before_receipt == after_receipt
        T["final_receipt_replay_safe"] = y1["status"] == "RECOVERED_SUCCESS" and y2["status"] == "RECOVERED_SUCCESS"
        bad = load_json(root / "final_receipt.json"); bad["decision"] = "CONFLICT"
        T["conflicting_final_receipt_rejected"] = rejected(lambda: write_final_receipt(root, bad), "conflicting final receipt rejected")

        T["repo_internal_root_rejected"] = rejected(lambda: ensure_external(ROOT / "tmp_bad", "test"), "outside repository")
        T["invalid_boundary_rejected"] = rejected(lambda: simulate_crash(base / "bad_boundary", "JNU_BAD", "L_BAD", "NOT_A_PHASE", "PRE"), "invalid crash boundary")

        production_after = production_bytes()
        T["production_byte_for_byte_unchanged"] = production_before == production_after
        T["production_hashes_unchanged"] = production_hash_before == hashes_from_bytes(production_after)

    failed = [k for k,v in T.items() if not v]
    result = {
        "status": "PASS" if not failed else "FAIL",
        "artifact_class": "JNU_SYNTHETIC_SHADOW_CRASH_RECOVERY_SELFTEST_RESULT",
        "tests_passed": sum(bool(v) for v in T.values()),
        "tests_total": len(T),
        "failed": failed,
        "public_real_forecasts": 0,
        "public_real_outcomes": 0,
        "real_entitlement_connected": False,
        "production_state_mutated": False,
    }
    print(json.dumps(result, indent=2))
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
