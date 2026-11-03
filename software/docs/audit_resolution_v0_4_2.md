# Eighth audit resolution NHANES CardioBench 0.4.2

| Finding | Correction | Regression evidence |
|---|---|---|
| 1 Review forms not bound to reviewed release | Format 2 row commitment covers tasks, catalog, response contracts, suite and core manifest; comparison verifies core first | Tampered release and rehashed changed release both reject old forms; current complete synthetic forms compare |
| 2 Gates accept stale or absent packages | Complete delivery profile requires one wheel and sdist with matching metadata, embedded core and exact installation-report hashes | Rehashed stale/missing packages, stale reports and missing review files reject; actual shipped wheel and offline sdist rebuild installed outside source |
| 3 W11 policy leaks through reused IDs | Version plus complete task fingerprint gates alternatives | Unrelated and modified W11 tasks fail adjusted evidence; original W11 alternative remains valid |
| 4 Public grade infers ambiguous schemas | grade(actual, expected, task) requires the task; no inference | Two-argument/None calls fail explicitly; C15 string answer is format-invalid; W14 well-shaped wrong answer is answer mismatch |
| 5 Preflight and runtime disagree | Shared clean-code and fixture-input validators | Nonfinite strings fail both; valid right outcomes sharing an age-column name pass both; rejection fixtures retained |
| 6 Long CSV input raises traceback | 16 MiB file, 65536-character field and 65536-byte response bounds; strict CSV and UTF-8 errors | 140000-character rationale returns exit 2 without traceback/output; limits, quoted newlines and malformed quoting covered |

The 35 new regression methods use synthetic review records, never human reviews.
The complete local suite and final package evidence accompany the delivery. Tests
are software checks, not new independent benchmark workloads or clinical evidence.
Earlier audit resolutions are preserved separately. Hashes bind records to inputs
but neither authenticate reviewers nor constitute publisher signatures. Real
human adjudication, external model experiments, non-Linux runs and remote CI remain
pending. There is no silent migration of old forms or checkpoints.
