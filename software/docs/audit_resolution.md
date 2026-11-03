# Fourteenth audit resolution NHANES CardioBench 0.4.8

The three reproduced 0.4.7 boundary findings are corrected below.

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| Array/null installation reports caused AttributeError | Require an object before reading either wheel or sdist report fields | Rehashed non-object report matrix and actual release CLI diagnostics |
| Very large timing integers caused OverflowError | Shared positive finite validator for all timing fields and timeout preflight | All scalar/raw timing positions, invalid numeric classes, ordinary positive values and core release CLI |
| Noncoding operation passed task/scoring preflight but failed the runner | Shared operation rule and descriptor construction; noncoding non-null values fail preflight | Each task family across preflight, score, live binding and archived binding; no output creation; valid null/omitted/coding cases |

## Version 0.4.8 controlled input validation

Installation and sdist evidence must be JSON objects before any report fields
are accessed. Arrays, null, strings, numbers and booleans receive a controlled
INSTALLATION_EVIDENCE_MUST_BE_OBJECT error, including after outer checksums
are refreshed. Release CLI validation errors use exit status 2 without a traceback.

Reproduction timing and live timeout preflight reuse the positive finite number
validator. Booleans, nonpositive or nonfinite values and integers too large for
a finite float are rejected explicitly; the 4096-digit general JSON integer
limit does not imply that such integers are suitable timing measurements.

A shared task operation rule is used by task preflight, response schemas,
scoring, live binding creation and archived descriptor validation. Noncoding
requests may omit operation or set it to null; any other value is rejected
with INVALID_TASK_OPERATION during task preflight. Coding requests require one
of unit, clean or convert_glucose. Other metadata fields remain permitted.
Task validation completes before run output is created. The frozen workload
inventory, expected responses, scoring rules and valid task behavior are unchanged.

Complete-delivery-v8 renews the suite and code bindings. Contract 1.4, checkpoint
schema 4, installation format 3, process format 1, verification format 2 and
review format 2 are retained. Earlier audit and evidence remain archived under
v0_4_7; old checkpoints and review forms require their matching software.
Local tests and installation are distinct from remote CI, Windows/macOS,
external-model evaluation, independent human review and public deposition,
which remain pending. Blank forms and synthetic tests are not human validation.

The full automated test log and offline byte-regeneration report are retained in
results/paper. Current validation/ records are generated from the final source
and exact shipped packages; validation/v0_4_7 retains prior observations without
relabeling. Checksums establish consistency, not independent authentication.
