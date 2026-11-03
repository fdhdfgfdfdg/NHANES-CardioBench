# Eleventh audit resolution NHANES CardioBench 0.4.5

| Finding | Correction | Evidence |
|---|---|---|
| Contradictory reproduction fields pass the gate | Reconstruct all deterministic fields, three prediction archives and CSV; reconcile positive raw timings and statistics | Changed context/family/split/row/subset/trace/comparison/code fields, predictions, CSV and timings are rejected |
| Uninstallable wheels pass package validation | Canonical wheel/sdist names, dist-info/root identity, Python requirement and no runtime dependencies | Invalid names, directory identity and requirement/dependency metadata are rejected; both actual installation paths rerun |
| Very large integers fail inconsistently | Contract 1.3 input limit of 4096 decimal digits, direct integer rational conversion and a stable INTEGER_LIMIT_EXCEEDED reason | JSON/task boundaries, valid reference rejections and supported large-weight cancellation |
| Any version-like directory bypasses residue checks | Explicit older-version allowlist only | Current and unknown versions reject locks; registered history remains unchanged |
| Task IDs create incompatible Windows filenames | Shared preflight rejects reserved device names and case-folded duplicates | Negative cases fail before run output; ordinary names remain allowed |
| NONFINITE_RESULT description omits conversion | General numeric-result definition propagated through contract exports and manuscript | Exported contract 1.3 and reason/bound regression |

The 104-check inventory, review format 2, checkpoint schema 4 and mutation
protocol 1.1 remain. Complete-delivery-v5 and contract 1.3 replace their prior
versions. Earlier checkpoints and reviewer forms require their original software.
Tests use explicitly synthetic malformed records, never human review evidence.
Non-Linux runs, remote CI, independent adjudication, external model experiments
and permanent public deposition remain pending. Unsigned records establish
internal consistency, not independent authentication or proof of execution.
