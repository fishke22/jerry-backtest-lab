from __future__ import annotations
import argparse, hashlib, json, os, shutil
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config" / "jnu_private_selection_shadow_crash_recovery_protocol_v1.json"
STATE_PATHS = {
    "PROVIDER_SELECTION_SHORTLIST": ROOT / "config" / "jnu_provider_selection_shortlist_v1.json",
    "PRODUCTION_KEY_CUSTODY_CURRENT": ROOT / "config" / "jnu_production_key_custody_current_v1.json",
    "PROVIDER_TERM_READINESS_CURRENT": ROOT / "config" / "jnu_provider_term_readiness_current_v1.json",
}
ZERO_HASH = "0" * 64

def canonical_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def canonical_hash(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_external(path: Path, label: str) -> Path:
    p = path.expanduser().resolve()
    root = ROOT.resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return p
    raise RuntimeError(f"{label} must be outside repository")

def load_json(path: Path) -> dict:
    x = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x, dict):
        raise RuntimeError(f"{path} must contain an object")
    return x

def atomic_write_new_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = load_json(path)
        if canonical_hash(existing) == canonical_hash(obj):
            return
        raise RuntimeError(f"immutable file conflict: {path.name}")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def production_bytes() -> dict[str, bytes]:
    return {sid: p.read_bytes() for sid, p in STATE_PATHS.items()}

def hashes_from_bytes(raw: dict[str, bytes]) -> dict[str, str]:
    return {sid: hashlib.sha256(data).hexdigest() for sid, data in raw.items()}

def ensure_production_unchanged(before: dict[str, bytes]) -> dict[str, str]:
    after = production_bytes()
    if after != before:
        raise RuntimeError("authoritative production state changed")
    return hashes_from_bytes(after)

def init_external_transaction(root: Path, transaction_id: str, lineage_id: str) -> tuple[dict[str, Path], dict[str, str]]:
    root = ensure_external(root, "crash-recovery root")
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("crash-recovery root must be empty or absent")
    root.mkdir(parents=True, exist_ok=True)
    (root / "journal").mkdir()
    (root / "shadow" / "state").mkdir(parents=True)
    raw = production_bytes()
    expected = hashes_from_bytes(raw)
    paths = {}
    for sid, src in STATE_PATHS.items():
        p = root / "shadow" / "state" / src.name
        p.write_bytes(raw[sid])
        paths[sid] = p
    meta = {
        "version": "1.0",
        "artifact_class": "JNU_SYNTHETIC_SHADOW_CRASH_RECOVERY_TRANSACTION_META",
        "mode": "SYNTHETIC",
        "transaction_id": transaction_id,
        "lineage_id": lineage_id,
        "production_preimage_sha256": expected,
        "created_at_utc": now_utc(),
        "real_commit_capability": False,
        "real_apply_capability": False,
        "production_state_mutated": False,
    }
    atomic_write_new_json(root / "transaction_meta.json", meta)
    return paths, expected

def journal_files(root: Path) -> list[Path]:
    return sorted((root / "journal").glob("*.json"))

def append_journal(root: Path, transaction_id: str, lineage_id: str, phase: str, edge: str, status: str, details: dict | None = None) -> dict:
    files = journal_files(root)
    seq = len(files) + 1
    parent = ZERO_HASH if not files else load_json(files[-1])["entry_sha256"]
    base = {
        "version": "1.0",
        "artifact_class": "JNU_SYNTHETIC_SHADOW_CRASH_RECOVERY_JOURNAL_ENTRY",
        "sequence": seq,
        "transaction_id": transaction_id,
        "lineage_id": lineage_id,
        "phase": phase,
        "edge": edge,
        "status": status,
        "parent_sha256": parent,
        "details": details or {},
        "production_effect": False,
    }
    base["entry_sha256"] = canonical_hash(base)
    name = f"{seq:06d}_{phase}_{edge}.json"
    atomic_write_new_json(root / "journal" / name, base)
    return base

def validate_journal(root: Path) -> list[dict]:
    files = journal_files(root)
    out = []
    parent = ZERO_HASH
    txn = None
    lineage = None
    for idx, p in enumerate(files, start=1):
        e = load_json(p)
        if not p.name.startswith(f"{idx:06d}_"):
            raise RuntimeError("journal sequence filename mismatch")
        if e.get("sequence") != idx:
            raise RuntimeError("journal sequence gap or replay")
        if e.get("parent_sha256") != parent:
            raise RuntimeError("journal parent hash mismatch")
        body = dict(e)
        got = body.pop("entry_sha256", None)
        if got != canonical_hash(body):
            raise RuntimeError("journal entry hash mismatch")
        if txn is None:
            txn = e.get("transaction_id")
            lineage = e.get("lineage_id")
        if e.get("transaction_id") != txn or e.get("lineage_id") != lineage:
            raise RuntimeError("journal mixed transaction/lineage")
        parent = got
        out.append(e)
    return out

def write_lock(root: Path, transaction_id: str, lineage_id: str) -> Path:
    p = root / ".selection-shadow-crash-recovery.lock"
    obj = {
        "transaction_id": transaction_id,
        "lineage_id": lineage_id,
        "created_at_utc": now_utc(),
        "mode": "SYNTHETIC",
    }
    atomic_write_new_json(p, obj)
    return p

def clear_matching_stale_lock(root: Path, transaction_id: str, lineage_id: str) -> None:
    p = root / ".selection-shadow-crash-recovery.lock"
    if not p.exists():
        return
    x = load_json(p)
    if x.get("transaction_id") != transaction_id or x.get("lineage_id") != lineage_id:
        raise RuntimeError("foreign stale lock rejected")
    p.unlink()

def backup_preimage(root: Path, paths: dict[str, Path], expected: dict[str, str]) -> dict[str, Path]:
    bdir = root / "shadow" / "preimage_backups"
    bdir.mkdir(parents=True, exist_ok=True)
    out = {}
    for sid, p in paths.items():
        dst = bdir / p.name
        if not dst.exists():
            shutil.copy2(p, dst)
        if sha256_file(dst) != expected[sid]:
            raise RuntimeError(f"preimage backup hash mismatch: {sid}")
        side = Path(str(dst) + ".sha256")
        if not side.exists():
            side.write_text(expected[sid] + "\n", encoding="utf-8")
        if side.read_text(encoding="utf-8").strip() != expected[sid]:
            raise RuntimeError(f"preimage sidecar mismatch: {sid}")
        out[sid] = dst
    return out

def verify_preimages(root: Path, expected: dict[str, str]) -> dict[str, Path]:
    bdir = root / "shadow" / "preimage_backups"
    out = {}
    for sid, src in STATE_PATHS.items():
        p = bdir / src.name
        side = Path(str(p) + ".sha256")
        if not p.is_file() or not side.is_file():
            raise RuntimeError(f"preimage backup missing: {sid}")
        sha = sha256_file(p)
        if sha != expected[sid] or side.read_text(encoding="utf-8").strip() != sha:
            raise RuntimeError(f"preimage backup corrupted: {sid}")
        out[sid] = p
    return out

def shadow_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {sid: sha256_file(p) for sid, p in paths.items()}

def mutate_shadow(paths: dict[str, Path], transaction_id: str, lineage_id: str, partial: bool = False) -> dict[str, str]:
    for idx, sid in enumerate(STATE_PATHS):
        p = paths[sid]
        obj = load_json(p)
        obj["_synthetic_shadow_crash_recovery"] = {
            "transaction_id": transaction_id,
            "lineage_id": lineage_id,
            "production_effect": False,
        }
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        if partial and idx == 0:
            break
    return shadow_hashes(paths)

def verify_shadow_mutation(paths: dict[str, Path], transaction_id: str, lineage_id: str) -> None:
    for sid, p in paths.items():
        obj = load_json(p)
        marker = obj.get("_synthetic_shadow_crash_recovery")
        if marker != {"transaction_id": transaction_id, "lineage_id": lineage_id, "production_effect": False}:
            raise RuntimeError(f"shadow mutation verification failed: {sid}")

def rollback_exact(paths: dict[str, Path], backups: dict[str, Path], expected: dict[str, str]) -> None:
    for sid, dst in paths.items():
        shutil.copy2(backups[sid], dst)
    if shadow_hashes(paths) != expected:
        raise RuntimeError("rollback did not restore exact preimage")

def final_receipt_object(root: Path, transaction_id: str, lineage_id: str, decision: str, expected: dict[str, str], final_hashes: dict[str, str], production_after: dict[str, str]) -> dict:
    chain = validate_journal(root)
    return {
        "version": "1.0",
        "artifact_class": "JNU_SYNTHETIC_SHADOW_CRASH_RECOVERY_FINAL_RECEIPT",
        "mode": "SYNTHETIC",
        "transaction_id": transaction_id,
        "lineage_id": lineage_id,
        "decision": decision,
        "journal_entries": len(chain),
        "journal_head_sha256": chain[-1]["entry_sha256"] if chain else ZERO_HASH,
        "shadow_preimage_sha256": expected,
        "shadow_final_sha256": final_hashes,
        "production_sha256_after": production_after,
        "production_unchanged": True,
        "real_commit_capability": False,
        "real_apply_capability": False,
        "production_state_mutated": False,
        "credentials_connected": False,
        "kms_api_called": False,
        "real_activation_authorized": False,
    }

def write_final_receipt(root: Path, receipt: dict) -> dict:
    p = root / "final_receipt.json"
    if p.exists():
        current = load_json(p)
        if canonical_hash(current) != canonical_hash(receipt):
            raise RuntimeError("conflicting final receipt rejected")
        return current
    atomic_write_new_json(p, receipt)
    return receipt

def simulate_crash(root: Path, transaction_id: str, lineage_id: str, crash_phase: str, crash_edge: str) -> dict:
    proto = load_json(PROTOCOL)
    if crash_phase not in proto["transaction_sequence"] or crash_edge not in {"PRE", "POST"}:
        raise RuntimeError("invalid crash boundary")
    before = production_bytes()
    paths, expected = init_external_transaction(root, transaction_id, lineage_id)
    lock = None
    for phase in proto["transaction_sequence"]:
        append_journal(root, transaction_id, lineage_id, phase, "PRE", "STARTED")
        if phase == crash_phase and crash_edge == "PRE":
            ensure_production_unchanged(before)
            return {"status": "CRASHED", "phase": phase, "edge": "PRE", "expected": expected}
        if phase == "LOCK_ACQUISITION":
            lock = write_lock(root, transaction_id, lineage_id)
        elif phase == "CAS_VERIFICATION":
            if shadow_hashes(paths) != expected:
                raise RuntimeError("synthetic shadow CAS mismatch")
        elif phase == "PRIVATE_PREIMAGE_BACKUP":
            backup_preimage(root, paths, expected)
        elif phase == "MUTATION_SET":
            mutate_shadow(paths, transaction_id, lineage_id)
        elif phase == "POST_WRITE_VERIFICATION":
            verify_shadow_mutation(paths, transaction_id, lineage_id)
        elif phase == "ROLLBACK_ON_PARTIAL_FAILURE":
            pass
        elif phase == "FINAL_TRANSACTION_RECEIPT":
            prod_after = ensure_production_unchanged(before)
            rec = final_receipt_object(root, transaction_id, lineage_id, "SUCCESS", expected, shadow_hashes(paths), prod_after)
            write_final_receipt(root, rec)
        append_journal(root, transaction_id, lineage_id, phase, "POST", "COMPLETE")
        if phase == crash_phase and crash_edge == "POST":
            ensure_production_unchanged(before)
            return {"status": "CRASHED", "phase": phase, "edge": "POST", "expected": expected}
    if lock and lock.exists():
        lock.unlink()
    return {"status": "COMPLETE", "expected": expected}

def recover(root: Path) -> dict:
    root = ensure_external(root, "crash-recovery root")
    meta = load_json(root / "transaction_meta.json")
    transaction_id = meta["transaction_id"]
    lineage_id = meta["lineage_id"]
    expected = meta["production_preimage_sha256"]
    before = production_bytes()
    if hashes_from_bytes(before) != expected:
        raise RuntimeError("production CAS changed since synthetic transaction started")
    validate_journal(root)
    clear_matching_stale_lock(root, transaction_id, lineage_id)
    paths = {sid: root / "shadow" / "state" / src.name for sid, src in STATE_PATHS.items()}
    receipt_path = root / "final_receipt.json"

    if receipt_path.exists():
        verify_shadow_mutation(paths, transaction_id, lineage_id)
        decision = "FINALIZE_ALREADY_COMPLETE"
        append_journal(root, transaction_id, lineage_id, "RECOVERY", "POST", decision)
        original = load_json(receipt_path)
        ensure_production_unchanged(before)
        return {"status": "RECOVERED_SUCCESS", "decision": decision, "receipt": original}

    marker_count = 0
    valid_marker_count = 0
    for sid, p in paths.items():
        obj = load_json(p)
        marker = obj.get("_synthetic_shadow_crash_recovery")
        if marker is not None:
            marker_count += 1
            if marker == {"transaction_id": transaction_id, "lineage_id": lineage_id, "production_effect": False}:
                valid_marker_count += 1

    if 0 < marker_count < len(paths) or valid_marker_count != marker_count:
        backups = verify_preimages(root, expected)
        rollback_exact(paths, backups, expected)
        decision = "ROLLBACK_TO_PREIMAGE"
        append_journal(root, transaction_id, lineage_id, "RECOVERY", "POST", decision)
        prod_after = ensure_production_unchanged(before)
        rec = final_receipt_object(root, transaction_id, lineage_id, decision, expected, shadow_hashes(paths), prod_after)
        write_final_receipt(root, rec)
        return {"status": "RECOVERED_ROLLED_BACK", "decision": decision, "receipt": rec}

    if marker_count == 0:
        backup_preimage(root, paths, expected)
        mutate_shadow(paths, transaction_id, lineage_id)
        verify_shadow_mutation(paths, transaction_id, lineage_id)
        decision = "RESUME_FORWARD"
        append_journal(root, transaction_id, lineage_id, "RECOVERY", "POST", decision)
        prod_after = ensure_production_unchanged(before)
        rec = final_receipt_object(root, transaction_id, lineage_id, decision, expected, shadow_hashes(paths), prod_after)
        write_final_receipt(root, rec)
        return {"status": "RECOVERED_SUCCESS", "decision": decision, "receipt": rec}

    verify_shadow_mutation(paths, transaction_id, lineage_id)
    decision = "FINALIZE_ALREADY_COMPLETE"
    append_journal(root, transaction_id, lineage_id, "RECOVERY", "POST", decision)
    prod_after = ensure_production_unchanged(before)
    rec = final_receipt_object(root, transaction_id, lineage_id, decision, expected, shadow_hashes(paths), prod_after)
    write_final_receipt(root, rec)
    return {"status": "RECOVERED_SUCCESS", "decision": decision, "receipt": rec}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--transaction-id", required=True)
    ap.add_argument("--lineage-id", required=True)
    ap.add_argument("--crash-phase")
    ap.add_argument("--crash-edge", choices=["PRE", "POST"])
    ap.add_argument("--recover", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    if args.recover:
        result = recover(root)
    else:
        if not args.crash_phase or not args.crash_edge:
            raise SystemExit("--crash-phase and --crash-edge are required unless --recover")
        result = simulate_crash(root, args.transaction_id, args.lineage_id, args.crash_phase, args.crash_edge)
    safe = {k: v for k, v in result.items() if k not in {"receipt", "expected"}}
    print(json.dumps(safe, indent=2))

if __name__ == "__main__":
    main()
