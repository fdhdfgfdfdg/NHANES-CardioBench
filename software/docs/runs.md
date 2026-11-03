# Reproducible trusted adapter runs

The runner is for trusted local Python adapters. It is not an isolation boundary.
The default track is provided-context. Closed-book omits the catalog from stdin;
it does not prevent the adapter from reading local files or using the network.
No remote API, cost or network activity is automatically monitored. Declare these
using --disclosure for external model runs. Missing disclosure is recorded as
unknown, never as zero cost or zero external calls.

## Start and continue

From the extracted source directory:

```sh
python -m cardiobench run-adapter --adapter examples/trusted_reference_adapter.py --split development --out results/example_run --max-cases 5
python -m cardiobench run-adapter --adapter examples/trusted_reference_adapter.py --split development --out results/example_run --resume
```

The adapter is a disclosed positive control, not a model competitor. All selected
checks remain in the score denominator even during a partial run. --max-cases
limits the number of new attempts in this invocation; omit it to finish the run.
Use the same timeout, track, prompt and disclosure to resume. A successful case
is never rerun. Failed cases are terminal by default; --resume --retry-failed
explicitly adds one new attempt to each failed case and retains previous attempts.
The final score uses the latest attempt and reports the total attempt count.
Retry policies must be identical in any competitive comparison.

## Binding and archive

checkpoint.json is the authoritative atomic checkpoint, containing run identity,
configuration and attempt history. It binds the selected tasks, catalog, gold,
Python/platform, adapter file, all runner module files, prompt text, output limits,
timeout, access track and disclosure. Each request has an archived canonical JSON
file and SHA-256 digest. A resume validates the binding and request archive before
continuing. Hashes detect changes relative to the stored record, not authenticity
against an operator who replaces records and their hashes.

predictions.json, traces.json, score.json and run_manifest.json are derived files.
They are replaced individually after each committed case; a resume reconstructs
them from checkpoint.json after an interrupted report write. They do not form one
atomic transaction. An interrupted external call with no committed result may be
repeated on resume; remote side effects are therefore not exactly-once operations.

Only one writer may use an output directory. run.lock is removed on ordinary exit
or handled interruption. After a hard kill, confirm the recorded process is no
longer active before manually removing a stale lock. Fresh runs refuse nonempty
output directories; use a new directory or explicit --resume.

The working directory defaults to the adapter directory; --adapter-cwd overrides it.
Declare every external input with repeated --dependency-file PATH and relevant
installed distributions with repeated --dependency-package NAME. Their file hashes
and installed versions are bound on every case and resume. --environment-file JSON
sets allowlisted nonsecret variables: OMP_NUM_THREADS, OPENBLAS_NUM_THREADS,
MKL_NUM_THREADS, PYTHONHASHSEED, LANG, LC_ALL and TZ. Effective values (including
inherited values) are recorded. Other environment variables are inherited, not
recorded. Undeclared imports/files, credentials, provider state and model weights
are outside this fingerprint. This is not a hermetic runtime or determinism proof.

## Limits and errors

The timeout is a positive finite number (default 30 seconds). --stdout-limit and
--stderr-limit are positive byte counts, defaulting to 1,000,000 and 64,000.
Capture is bounded while streams are read. Overflow and timeout preserve the
retained prefixes and record a failed case. On POSIX the runner terminates the
adapter process group; on other platforms only the direct process is terminated.
Only Linux/CPython 3.12.14 has been tested for this release. It is not a security
sandbox, a disk quota, a CPU quota or a network restriction.

--prompt-file adds UTF-8 prompt text to each request and stores its hash.
--disclosure accepts JSON with nonplaceholder system/version, provider, access
policy, retry policy and cost/unavailable-reason fields. Its condition must match
provided_context or closed_book. This validates presence and track consistency,
not truthfulness or provider provenance. Controlled retrieval is still external.

## Version 0.3.1 validation boundaries (historical)

CLI export, score and run-adapter verify the installed or source release before
processing candidate inputs. Empty selections are errors. Standalone score hashes
the exact UTF-8 response bytes it parses. Invalid UTF-8 stdout or unpaired JSON
surrogates fail a case; stderr remains a replacement-decoded diagnostic. Stream
hashes and byte counts describe retained raw prefixes, not bytes discarded after
a limit. Numeric responses beyond binary-float range fail comparison without
aborting the remaining checks.

Resume validates required state fields, types, timezone-aware timestamps, durations,
and terminal-success history. It reconstructs each expected request and compares
both its archive and every historical attempt digest. Recomputing a checksum does
not bypass these structural checks, but they do not authenticate operator records.
Code fingerprints intentionally prevent resuming a 0.2.0 run under 0.3.1. Keep the
original software for those runs. No checkpoint migration is provided.

## Version 0.3.1 evidence and write protection (historical)

The schema-2 binding includes the actual gold object used by the Python scoring
API, separately from the frozen gold file hash. Checkpoints retain Base64 raw
stdout/stderr prefixes and verify byte counts, hashes and decoded text. Success
requires exit code zero and a schema-valid response equal to parsed stdout.
Attempt timestamps must lie within the recorded run interval. Launch failures
remain distinguishable and may be explicitly retried. Checksums are not signatures.

Outputs cannot alias candidate inputs (including symlinks/hardlinks) or overwrite
release files and protected source, test, example, documentation and frozen-result
directories. Output directories cannot contain declared input files. This guards
ordinary mistakes; it does not prevent adversarial filesystem races.

Checkpoint writes fsync the temporary file, atomically replace the target and fsync
the parent directory on POSIX. Fault tests cover failed replacement, report failure,
SIGINT, SIGKILL after a committed case, and descendant-held pipes. Power-loss and
all filesystem/platform durability behavior are not established. After SIGKILL,
operators must also stop any surviving adapter processes before removing a stale
lock. Uncommitted attempts can execute again. Earlier releases need their original
software; no automatic checkpoint migration is provided.

## Version 0.3.1 failure evidence and execution boundaries (historical)

Resume reconciles exit failures, invalid UTF-8 and response-parsing failures with
captured bytes and exit status. Unknown failure labels are rejected. Launch failures
cannot contain captured text. An output-limit record must retain a full limited
stream. Timeout and overflow observations cannot be independently proven from a
checkpoint alone, and records remain unauthenticated operator evidence.

Python API calls deep-copy task, gold, catalog and option objects at entry. Task
IDs must match [A-Za-z0-9][A-Za-z0-9_-]{0,127} and be unique; every selected ID needs
a schema-valid gold response. Limits/max-cases require positive integers, not
booleans or fractional numbers. Invalid inputs fail before creating run outputs.

Declared bindings are checked again after every adapter call, including the final
case. A mismatch or unavailable bound file prevents committing that result. Restore
the original inputs before resuming, or start a new run. A discarded external call
may still have incurred cost or side effects and may be repeated on resume. These
boundary checks are not continuous monitoring: changes reverted between checks,
undeclared inputs and remote provider state remain outside the guarantee.

CLI JSON writes share the checkpoint writer: random temporary filename, file fsync,
atomic replacement and POSIX directory fsync. An existing predictable .tmp symlink
is not opened or overwritten. This mitigates accidental/stale-path collisions; it
is not an adversarial filesystem sandbox or universal power-loss guarantee.

## Version 0.4.0 changes

Checkpoint schema 3 binds the resolved adapter pathname, actual launch command and executable path in addition to content, working directory and previous configuration. Renaming an entry point prevents resume even if bytes match. Evidence-policy bytes are bound. Old checkpoints require their original software.

Runner reports and scoring JSON/CSV writes use protected random-temporary-file atomic replacement; the source parser protects both the installed release and custom source inputs. Shared task validation rejects duplicate IDs and incomplete metadata before output creation or scoring.

Optional disclosure is explicitly classified as local_control or external. Supplied forms reject remaining placeholders, non-boolean access flags and mismatched versions. External forms require dated provenance, generation settings or explicit reasons for unavailable settings, context/tool budgets and archive locations. Supplied task/catalog hashes, subset and timeout must match the actual run. The runner records actual hashes automatically; it cannot authenticate self-reported provider use, cost, identities or independence. Omitting disclosure remains an explicit unknown local run, never a completed external-model experiment.


## Version 0.4.1 failure and checkpoint semantics

Checkpoint schema 4 binds contract 1.1 and the task-family response descriptors.
The runner validates task-shaped answers before committing them as successful.
`ADAPTER_RESPONSE_ERROR` denotes malformed/deep JSON, `ADAPTER_FORMAT_ERROR`
denotes a parsed response violating the task contract, and process/timeout errors
remain execution failures. Reports separate execution_failed_cases,
format_failed_cases, incorrect_answer_cases and evidence_mismatch_cases. Only
execution/format failures can be retried with `--resume --retry-failed`; valid
but incorrect answers remain completed results. All attempts and retained raw
bytes remain archived. Resume revalidates the same contract and capture evidence.

Task nesting is bounded at 64, response and disclosure nesting at 32, and general
checkpoint JSON nesting at 128, leaving envelope headroom. Depth is checked before
JSON decoding and before serialization; deeply nested candidates cannot create
unreadable committed state. Older checkpoint versions require the corresponding
older software. There is no automatic checkpoint migration.

All six generated resource files are written as explicit UTF-8 bytes with LF;
.gitattributes disables checkout conversion for frozen file hashes. Windows/macOS
and remote CI remain configured but unexecuted in this local delivery.

Runtime writers protect core files, ARTIFACTS_SHA256.json and packages/, validation/,
review_materials/. Installation checks write to results/ci by default. Maintainers
freeze evidence with tools/freeze_artifacts.py only after building and reviewing it.


## Version 0.4.2 compatibility

Schema 4 now binds contract 1.2 and the corrected code. Earlier checkpoints require
their original software; no silent migration occurs. The two-argument grade API
is removed: callers must supply the task. Review forms separately use format 2
input commitments and bounded CSV parsing. Complete delivery verification now
checks package metadata/core content and evidence identities in addition to hashes;
see docs/release.md. Runtime write protection includes archived results/v0_4_1.

## Version 0.4.4 delivery consistency

The four derived reports are still individually replaceable during a live run.
For a frozen complete delivery, every saved projection must equal reconstruction
from its authoritative checkpoint. Current locks and temporary output block release
freezing; historical directories retain their original records. The runtime
validation tool resolves output paths against the caller and records verification
scope. Contract 1.2 and checkpoint schema 4 are retained with updated code bindings.

## Version 0.4.5 input limits

Contract 1.3 rejects reserved Windows device IDs and case-folding ID collisions
before creating an output directory. Integers have at most 4096 decimal digits
across task and JSON validation; INTEGER_LIMIT_EXCEEDED is the stable error code.
The released workloads are unchanged. Checkpoint schema 4 now binds contract 1.3
and updated code, so earlier runs require their original software.

## Version 0.4.6 verification and environment checks

Verification format 2 stores the exact observed core manifest, checks its digest,
and reconciles every count, type, metadata observation and artifact-scope field.
Only primary results may use the earlier staging snapshot, with differences
limited to their five reproduction output files. Process and installation
observations and the complete staging gate bind the final core. Gate test counts
are recomputed from the test source. Unknown verification claims are rejected.
The complete-delivery-v6 profile restricts sdist members and validates generated
configuration, metadata, entry points, dependency links and source lists.

Contract 1.4 requires Python int_max_str_digits to be 0 or at least 4096.
Incompatible settings raise INCOMPATIBLE_INTEGER_ENVIRONMENT before JSON work;
the library does not modify the setting. Integers above 4096 decimal digits
still raise INTEGER_LIMIT_EXCEEDED. Resume rejects timeout durations shorter
than the configured threshold minus min(0.001 seconds, 0.001 times threshold).
This checks internal consistency of recorded events, not independent timing
attestation. Prior code/contract bindings cannot silently resume as this version.

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
