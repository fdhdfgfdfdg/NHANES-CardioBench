# NHANES-CardioBench 0.4.8

An offline finite benchmark for semantic, coding, survey-design, declared dependency
and synthetic-execution decisions. Version 0.4.8 has 89 canonical workloads and
104 checks across 31 workflow groups: 32 development and 72 evaluation checks.
No participant records, clinical prediction experiments or external model calls
are included. The first 80 task objects and their gold responses retain the
0.3.1 definitions. The 24 new checks are separately specified synthetic cases,
not independent human annotations. The historical 16 execution variants share one
base workload; 12 additional execution workloads have distinct canonical IDs.

## Quick start

With Python 3.10 or newer, from the complete delivery ZIP root:

```sh
python -m cardiobench verify --require-artifacts
python -m cardiobench reproduce --out results/reproduced
python -m unittest discover -s tests -v
python tools/check_regeneration.py
python tools/check_release.py
```

The measured environment is CPython 3.12.14 on Linux. The configured Linux, Windows
and macOS CI matrix has not been run remotely. For an sdist checkout without outer evidence use `verify` and
`tools/check_release.py --core-only`; this is only a core staging check.
Runtime uses the Python standard
library only. Do not overwrite results/paper or results/v0_3_1; they preserve the
current and historical measurements. Historical 0.4.0 and 0.4.1 records are also retained. A version change does not retroactively
change the earlier published inventory or its claims.

## Install

The full software archive includes a wheel and source distribution in packages/:

```sh
python -m pip install --no-index --no-deps packages/nhanes_cardiobench-0.4.8-py3-none-any.whl
cardiobench verify
cardiobench reproduce --out results/reproduced
python -m cardiobench.sources
```

Run installed checks outside the source tree. setuptools and wheel are build-time
requirements only. An offline source build with those tools already available is
`python -m pip wheel --no-deps --no-build-isolation .`. No PyPI release is claimed.

## Measured local checks

- 13 frozen official snapshots; 383 occurrences from 12 component codebooks.
- 104/104 strict positive-control passes: 80/80 historical and 24/24 added checks.
- Label-only BM25 11/16; fixed context-field BM25 9/16 on the same semantic checks.
- 312/312 fixed response perturbations detected; the complete local regression suite passed (see results/paper/unit_test_log.txt).
- Source parsing and all six generated JSON resources rebuild offline.
- A separate evidence-policy result accepts two source-supported W11 alternatives;
  the primary strict metric remains unchanged. This author-defined policy has not
  received independent human adjudication.

Perfect positive-control scores show conformance to authored rules and routes,
not independent gold validity, model superiority or clinical performance.

## Candidate evaluation

```sh
python -m cardiobench export --split evaluation --track provided-context --out input.json
python -m cardiobench score --split evaluation --responses predictions.json --out score.json
python -m cardiobench run-adapter --adapter examples/trusted_reference_adapter.py --split development --out results/adapter --max-cases 5
python -m cardiobench run-adapter --adapter examples/trusted_reference_adapter.py --split development --out results/adapter --resume
```

Both export and adapter stdin include the same task-family response contract:
field names/types, reason-code vocabulary, evidence syntax, unit spellings and
comparison tolerances. These protocol rules contain no task-specific gold answer.
Closed-book omits the source catalog; filesystem/network isolation is the operator's
responsibility. Controlled retrieval is not implemented by this local runner.
The included adapter is an authored positive control, never a competitive model.

Responses require exactly status, answer, evidence and reason_code. Primary scores
use exact designated evidence sets. Reports separately label policy_adjusted scores
and their author-defined status. Missing and failed checks stay in the denominator.
Integer references are exact; float references use relative tolerance 1e-8 and
absolute tolerance 1e-10. Unknown response IDs, duplicate task IDs, malformed task
metadata, duplicate JSON keys and nonfinite JSON numbers are rejected.

## Numerical and operational guarantees

Synthetic execution validates one-to-one positive integer keys, nonnegative finite
ages, finite outcomes and nonnegative finite weights; only eligible positive weights
enter the mean. It uses exact rational arithmetic on decimal input representations
and rounds only the final quotient to a finite float. Extreme stress values are
synthetic numerical cases, not physiologically plausible observations.

Schema-4 checkpoints bind the actual adapter path/launch command and interpreter,
code hashes, selected inputs, evidence policy and declared configuration. Same bytes
at a different adapter path cannot resume an old run. Failed cases stay terminal
unless --resume --retry-failed is explicit. New runs require an empty output folder.
JSON and CSV outputs and parser exports use protected atomic replacement. The runner
is for trusted adapters, not an adversarial sandbox. Undeclared inputs, remote state,
network use and cost are not monitored. See docs/runs.md for boundaries and recovery.

## Independent review and release readiness

```sh
python tools/prepare_review.py --out ../new_review_materials
python -m cardiobench.review --reviewer-a A.csv --reviewer-b B.csv --out comparison.json
```

The shipped forms are blank. The comparison utility rejects incomplete/duplicate
submissions and reports field agreement before adjudication; it does not establish
reviewer identity or independence. Complete docs/run_disclosure_template.json for
actual external experiments. Supplied disclosures validate types, placeholders,
version and declared bindings; unknown settings require explicit explanations.
No human review, external experiment, remote CI or public deposit is fabricated.
See docs/release_readiness.json and docs/audit_resolution.md for the five current audit items.

Source hashes identify frozen bytes, not authenticity when both data and manifests
are replaced. Only maintainers should refresh manifests after reviewed changes.
Code is MIT-licensed; official source notices remain. Repository: https://github.com/fdhdfgfdfdg/NHANES-CardioBench. No version or concept DOI has been assigned.
Authors: Chuanhao Nie (cnie30@gatech.edu; ORCID 0009-0006-4208-6414) and Yisong Chen (corresponding author; ychen841@gatech.edu; ORCID 0009-0009-4978-7565).
Affiliation: College of Computing, Georgia Institute of Technology, Atlanta, GA 30332, USA.
The supplied MIT copyright and third-party notices are retained.


## Audit revision 0.4.1

The 104 tasks and expected answers are unchanged. Contract 1.1 shares answer-field
specifications across export, scoring, adapter capture and reviewer validation.
Unknown reasons, invalid minima and extra fields are rejected; cleaning retains
nonmissing strings. See `docs/audit_resolution_v0_4_1.md` for those nine historical fixes.

The complete ZIP has two checksum layers: core `MANIFEST_SHA256.json`, and
`ARTIFACTS_SHA256.json` binding that manifest plus packages, validation evidence
and review materials. Use `verify --require-artifacts` in the extracted ZIP.
An installed wheel verifies its bundled core resources and explicitly reports
that outer delivery evidence is not bundled. Checksums are not publisher signatures.
New run reports go outside the frozen evidence directories (for example results/ci).

Response JSON has a maximum container depth of 32; general stored JSON has a
maximum depth of 128. Overdeep adapter output is a recorded failure, not a broken
checkpoint. Format failures are eligible for explicit retry; ordinary incorrect
answers are not. Checkpoint schema 4 requires v0.4.1; retain older software for old runs.

The 312 perturbations use protocol 1.1. Thirty-four non-answer variants were changed
to satisfy the shared format contract; all 312 now pass format validation and are
detected as incorrect. Historical v0.4.0 evidence remains in results/v0_4_0 and
must not be treated as the identical perturbation experiment.


## Audit revision 0.4.2

Version 0.4.2 resolved six findings without changing tasks, gold, catalog or
semantic routes. Review format 2 commits each row to the reviewed suite, core
manifest, tasks, catalog and contract descriptors. Comparison verifies the release
first and rejects old/unbound or mismatched forms. Identities remain self-reported.
CSV input is bounded and malformed/oversized input produces a controlled error.

Contract 1.2 requires `grade(actual, expected, task)`; omitted or None task values
are API errors. Update callers to supply the exact task. Response fields and
mutation protocol 1.1 remain unchanged. Checkpoint schema 4 now binds contract 1.2
and new code: keep the original software for earlier checkpoints.

W11 alternative evidence applies only to the exact versioned task fingerprint.
A custom task reusing its ID receives no release-specific exception. Cleaning and
execution preflight share validation with runtime, including nonfinite numeric
strings and outcome/age columns with the same name in different input tables.

The complete-delivery-v2 profile requires one current wheel, one current sdist,
installation evidence bound to their exact hashes, and current review materials.
Embedded package manifests and core bytes must match the source. The default
installation checker uses packages/, never an unrelated dist/ wheel; it also
builds the supplied sdist offline and tests that installed result. Maintainer
staging order and the explicitly separate CI rebuild are in docs/release.md.
Historical validation and blank forms remain separately labelled v0_4_1.

## Audit revision 0.4.6

The five current corrections are in docs/audit_resolution.md; the preceding six
are retained in docs/audit_resolution_v0_4_2.md. Task, gold, catalog and routes
remain byte-identical to 0.4.2. Complete-delivery-v3 validates current evidence
contents: bound staging, timing and resume reports, archived predictions and
checkpoints, exact expected answers, blank reviewer forms and pending adjudication.
Refreshing checksums cannot make malformed or stale required materials pass.
Completed human submissions belong outside this blank preparation profile.

Archive readers reject both POSIX and Windows roots, drive paths, noncanonical
components, reserved names and case-insensitive collisions; extraction additionally
checks destination containment. This portable path behavior is tested locally;
actual Windows/macOS installation and remote CI remain pending.

W11 alternatives require the exact task and gold fingerprints. Modified scoring
gold does not inherit the released exception. Core verification accepts an explicit
root and freezes only that root. Current protocol headings and historical audit
links are checked. Contract 1.2 and checkpoint schema 4 remain, with new version
and code bindings; earlier runs still require their original software.

Version 0.4.6 resolved the findings in docs/audit_resolution_v0_4_6.md. Previous audit
records are preserved in docs/audit_resolution_v0_4_1.md,
docs/audit_resolution_v0_4_2.md, docs/audit_resolution_v0_4_3.md and
docs/audit_resolution_v0_4_4.md. Complete-delivery-v5 reconciles every deterministic
reproduction field, saved predictions, CSV rows and timing summaries. Wheel and
sdist names, metadata and Python requirements must match this release. Only the
explicit historical-version allowlist exempts old process residue.

Version 0.4.5 contract 1.3 bounds integers at 4096 decimal digits and rejects reserved
Windows task IDs and case-insensitive duplicate IDs before outputs are created.
Oversized integers use INTEGER_LIMIT_EXCEEDED; NONFINITE_RESULT covers both
conversion and weighted analysis. Supported large integers are accumulated without
string conversion. The 104 tasks and their gold answers, catalog and routes are
unchanged. Checkpoint schema 4 and review format 2 remain, with updated suite,
contract and code bindings. Earlier runs/forms require their original software.
Actual non-Linux execution, independent reviews and external-model experiments
remain pending.

## Version 0.4.6 corrections

Verification format 2 reconciles all reported counts and flags against the core
and stores the exact manifest snapshot observed during reproduction. Primary
paper results are staged before their inclusion in the final core; only the five
reproduction output files may differ from that snapshot. Installation, process
and staging-gate records bind the final core. Complete-delivery-v6 checks the
entire staging-gate record and its test count. These unsigned records establish
internal consistency, not independent execution authentication.

Both wheel and sdist members are restricted to explicit allowlists. Generated
sdist configuration and metadata are validated before extraction or rebuilding.
Checkpoint timeout records must agree with their configured duration, allowing
at most 1 ms and 0.1% of the threshold as a rounding tolerance.

Contract 1.4 supports up to 4096 decimal digits per integer when Python's
int_max_str_digits setting is 0 (disabled) or at least 4096. Lower settings fail
before JSON processing or output creation with INCOMPATIBLE_INTEGER_ENVIRONMENT;
they are not reported as protocol input overflow. The library never changes this
process-wide setting. Use the interpreter default or a configured limit of 4096
or greater. The fixed 4096-digit protocol bound still applies when Python's limit
is disabled.

The preceding 0.4.5 audit is preserved in
[the 0.4.5 audit](docs/audit_resolution_v0_4_5.md); its results, validation and
review preparation remain archived under v0_4_5.

## Version 0.4.7 configuration, process and build checks

One shared validator checks the exact live and archived run-binding schema before
state is accepted: positive finite timeout, positive integer output limits, prompt
digest, task descriptors, hash formats, launch-command/interpreter/adapter agreement,
dependency fingerprints, allowlisted environment and disclosure cross-fields.
Archived absolute POSIX or Windows paths are checked syntactically; the original
host paths need not exist on the reviewing machine. Unsigned operator records
provide consistency checks, not independent proof of execution.

Process report format 1 records the actual argument list, interpreter, output
directory, exit code, stdout and stderr. The parsed stdout must equal the recorded
summary and output path. Total elapsed time must cover the sum of the sequential
first-reference, lexical, context-lexical and 30 warm-reference measurements,
allowing at most 1 ms and 0.1% of that sum as rounding tolerance. This lower bound
does not establish absolute clock accuracy or authenticate the report.

Installation report format 3 records the builder Python and pip/build/setuptools/
wheel versions and the SHA256 of requirements-build.txt. Before offline validation,
prepare the builder with `python -m pip install -r requirements-build.txt`.
CI uses this explicit bootstrap and `python -m build --no-isolation --outdir dist`.
The installation checker rejects missing or mismatched pinned tools before writing
reports; failed subprocess diagnostics include the command, stdout and stderr.
The sdist rebuild and package installation still use --no-index and --no-deps;
bootstrap may require network access and is outside the offline validation claim.
Ordinary runtime commands remain standard-library-only. Local Linux validation
is recorded separately; configured remote CI, Windows and macOS are not claimed
as executed.

Complete-delivery-v7 requires these current records. Contract 1.4, checkpoint
schema 4, verification format 2, review format 2, workload definitions and gold
answers remain unchanged; the suite/version and source bindings are renewed.
Earlier checkpoints and reviewer forms require their original software. The
0.4.6 audit, results, validation and review preparation remain archived.

Previous audit: [0.4.7 resolution](docs/audit_resolution_v0_4_7.md).
Previous audit: [0.4.6 resolution](docs/audit_resolution_v0_4_6.md).

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

Current audit: [0.4.8 resolution](docs/audit_resolution.md).
