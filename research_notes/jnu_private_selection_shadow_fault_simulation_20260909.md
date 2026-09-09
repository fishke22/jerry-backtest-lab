# JNU Selection Transaction Atomicity / Rollback Fault-Injection Shadow Simulation

Stage: \`PRIVATE_SELECTION_TRANSACTION_ATOMICITY_ROLLBACK_FAULT_INJECTION_SHADOW_SIMULATION_SYNTHETIC_ONLY\`

This stage executes the frozen seven-step transaction sequence only against repo-external disposable shadow copies of the three authoritative production-state JSON files.

The simulator performs real shadow-side:
1. lock acquisition;
2. CAS verification;
3. preimage backup with SHA-256 sidecars;
4. synthetic shadow mutation;
5. post-write semantic verification;
6. rollback when a fault is injected;
7. immutable repo-external final receipt.

Fault injection is deterministic at every transaction step. Mutation-step faults occur after the first shadow file write. Rollback-step faults simulate an interruption after the first restore, then resume from checksum-verified preimage backups. Final-receipt faults force rollback before a simulated receipt retry.

Additional test conditions deliberately create stale shadow CAS and corrupt preimage backups. Both fail before shadow mutation.

Rollback must restore all three shadow files byte-for-byte and SHA-256-for-SHA-256 to their preimage. The authoritative production files are never locked, backed up or written; their bytes and hashes are checked before and after every simulation.

This is a mechanics simulation only. It does not enable real COMMIT/APPLY, credentials, KMS calls, key creation or activation.
