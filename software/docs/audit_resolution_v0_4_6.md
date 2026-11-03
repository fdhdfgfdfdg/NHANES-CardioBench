# Twelfth audit resolution NHANES CardioBench 0.4.6

| Finding | Correction | Regression evidence |
|---|---|---|
| Verification observations and staging-gate counts were only partially checked | Verification format 2 retains the exact core-manifest snapshot and reconciles every field; the staging gate compares its complete schema and recomputed test count | Changed counts, booleans, metadata, snapshot bytes, source bindings and extra claims fail; only the five primary reproduction outputs may differ from the primary staging snapshot |
| Sdist members outside the core were accepted | Exact member allowlist plus constrained generated metadata, build configuration, entry point and source list | Extra Python/data files, build aliases, dependency links, entry points and incomplete source lists fail |
| Impossible timeout durations survived resume | A timeout must last at least its configured threshold, allowing min(1 ms, 0.1% of threshold) clock tolerance | Zero/short durations fail before derived reports are changed; actual timeout, completed resume and explicit retry are exercised |
| Python's lower integer string limit contradicted the 4096-digit contract | Contract 1.4 checks environment compatibility before JSON parsing, validation and canonical serialization; it reports INCOMPATIBLE_INTEGER_ENVIRONMENT separately from INTEGER_LIMIT_EXCEEDED | Limits 0, 4096 and 4300 preserve both signed boundaries; limit 640 fails clearly before CLI output; library code does not change the interpreter setting |

The finite workload and gold answers are unchanged. Complete-delivery-v6,
verification format 2 and contract 1.4 identify the new checks. Review format 2,
installation report format 2, checkpoint schema 4 and mutation protocol 1.1 remain.
Prior checkpoints and forms require their original bindings/software. Test
mutations and reviewer fixtures are explicitly synthetic; they do not represent
human validation. Actual release installation, reproduction and resume observations
are regenerated after the final core is frozen. Independent adjudication, external
models, Windows/macOS execution, remote CI and public deposition remain pending.
