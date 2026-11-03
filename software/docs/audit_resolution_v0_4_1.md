# Seventh audit resolution — NHANES-CardioBench 0.4.1

| Finding | Correction | Verification |
|---|---|---|
| 1. Deep candidate JSON breaks resume | Predecode depth bound 128; response bound 32; serialization bound; schema 4 checkpoint | Deep output recorded as failure; partial run resumes |
| 2. Contract and scorer disagree | Shared field specifications, known reasons, integer minima, string cleaning | Invalid responses rejected; retained strings pass; all 312 mutations valid |
| 3. Review accepts invented answer fields | Task-family validation without comparing gold; form/input hashes and full rationale/date/concern retention | Invalid forms rejected; different but well-shaped proposals retained |
| 4. Format errors cannot retry | Parsed shape errors are ADAPTER_FORMAT_ERROR, separate failure counts | Explicit retry preserves history; ordinary wrong answers not retried |
| 5. Incomplete task/gold preflight | Required typed family inputs and gold shape validation | Empty requests/gold rejected before run directory creation; reject fixtures retained |
| 6. Platform newline drift | Six resources written as UTF-8 bytes, frozen bytes in .gitattributes | Byte-identical regeneration; non-Linux execution still pending |
| 7. Packages/evidence outside integrity coverage | Outer ARTIFACTS_SHA256.json binds core plus all packages, validation and review files; runtime write protection | Modified/missing/added artifact fails; frozen output collision rejected |
| 8. Secondary diagnostic contradicts score | Recompute adjusted error; retain primary_error | W11 adjusted success has null error and primary EVIDENCE_MISMATCH |
| 9. Deep dependency chains crash | Iterative DFS, disconnected cycle checks and explicit graph limits | 1201-node chain succeeds; disconnected cycle and size excess reject |

No independent human review, external model evaluation, remote CI or non-Linux run
is represented by these automated tests. Blank review forms remain pending.
Checksums detect modification against supplied manifests, not authenticity.
Mutation protocol 1.1 changes 34 of 312 variants; historical results are retained.
