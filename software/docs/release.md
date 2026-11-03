# Complete delivery validation

The source/sdist and installed wheel contain a core manifest. The full delivery
ZIP additionally carries one current wheel, one sdist, current validation and
review materials, their archived historical versions, and an outer manifest.
`verify --require-artifacts` and `tools/check_release.py` require that complete
profile. Plain `verify` permits a genuinely core-only distribution with no outer
files; a partial outer tree is an error, not an installed-core exception.

The complete-delivery-v8 profile checks package Name/Version metadata, embedded
core manifest equality and every embedded core file. Its required installation
reports bind the exact package SHA-256, installed version and installed core
manifest. Required review material must match current tasks, catalog, contracts
and core identity. A re-created outer manifest cannot make stale packages pass.
The installation checker defaults to packages/ and installs outside the source
in clean virtual environments. It also rebuilds the same supplied sdist offline,
validates the rebuilt wheel, and verifies/reproduces/parses sources after install.
Prepare the pinned build tools using requirements-build.txt before validation.
The bootstrap may use the network; installation and rebuilding do not acquire dependencies.
Reports remain operator-generated evidence, not signed attestations.

## Maintainer order

Keep staging evidence outside the source tree while updating it. Do not retain
old outer files in the current source during staging. Archive previous results,
validation and review materials under clearly named version directories. Never
relabel old results as current. No participant data or human decisions are generated.

1. Finish source, tests, docs and resource generation. Refresh the core manifest
   using tools/refresh_manifest.py. Run all unit tests and byte regeneration.
   Copy the successful log and regeneration report into results/paper and freeze
   environment.lock.json. Refresh the core manifest.
2. Reproduce into a fresh external staging directory. Copy only the five
   reproduction outputs into results/paper, then refresh the final core manifest.
   Verification format 2 preserves the exact pre-reproduction manifest snapshot;
   only those five output digests may differ from the final core. Tests, code,
   resources, documentation, environment and regeneration evidence must agree.
3. Run tools/check_release.py --core-only and save its output externally. This is
   explicitly a staging gate, not a complete-delivery certification. Generate
   current blank review materials externally with tools/prepare_review.py.
4. Prepare the builder with python -m pip install -r requirements-build.txt.
   Build the wheel and sdist from the final core into a fresh external package
   directory (for example python -m build --no-isolation --outdir ../staged_packages).
   Run tools/check_installation.py --package-dir ../staged_packages
   --out ../staged_validation/installation.json
   --sdist-out ../staged_validation/sdist_build.json. This explicit override tests
   that exact pair; its recorded hashes must match the final shipped packages.
5. Run tools/check_runtime.py --out ../staged_runtime. Copy its full output tree
   into staged_validation, including first/final checkpoints, requests and process
   reproduction files. It records actual five-to-thirty-two resume and timing,
   bound to the final core and inputs. Keep core/code unchanged.
6. Copy the exact staged packages to packages/, staged validation to validation/
   and bound blank materials to review_materials/. Include release_gate.json from
   the core staging gate. Preserve previous evidence in versioned subdirectories.
7. Run tools/freeze_artifacts.py. It refuses missing/mismatched packages/evidence.
   Then run verify --require-artifacts and tools/check_release.py. Store final gate
   output outside frozen trees; do not overwrite evidence after its checksum is
   frozen. Package exactly the files listed in both manifests and the manifests.

If core bytes change after step 2, regenerate the bindings, packages and reports;
do not patch hashes onto stale forms or installation records. The outer manifest
excludes itself; the core excludes outer packages/evidence to avoid hash cycles.
Only maintainers intentionally refresh manifests. Runtime commands never do so.

CI explicitly rebuilds into dist/ and passes --package-dir dist to the installation
checker. This tests that CI build; it does not substitute for delivery packages/.
The default checker never selects dist/ merely because that directory exists.
Linux was tested locally; Windows/macOS and remote matrix execution remain pending.

## Content checks in profile 4

Staging, timing and resume evidence must bind the current core and six input files.
The process report requires a positive finite duration and the recorded reproduction
file hash; archived predictions are rescored and summary/mutation counts checked.
Resume validation checks the first five and final development checkpoints, request
hashes, current task/gold/policy/code/adapter bindings, correct captured responses,
preserved first attempts and reported unchanged final checkpoint hash. Operator
records remain unsigned observations, not independent proof of execution.

Prepared review files must contain exact current expected responses, blank bound
A/B rows, complete pending adjudication rows and canonical preparation instructions.
Human decisions must be preserved separately and released through a new reviewed
profile/version; these blank files cannot imply completed independent validation.

Package members must be portable relative names: no roots, drives, dot/empty
components, reserved Windows names, links, file/directory conflicts or case-folded
duplicates. Extraction rechecks resolved containment before each write. Core
verification uses the explicitly requested root, including installed resource roots.


## Version 0.4.4 evidence and release hygiene

All four saved resume projections (predictions, traces, score and run manifest)
are reconstructed from the final checkpoint and compared in full. Installation
report format 2 requires six ordered successful observations: module verification,
module reproduction, source parsing, console help, console verification and console
reproduction. JSON observations are compared with the current finite inventory;
commands and exit codes are checked. The sdist report additionally requires the
offline build command/result and rebuilt wheel identity bound to the current core.
These are internal consistency checks of unsigned observations, not execution
attestations. Wheel entry points, pure-Python tag/layout, RECORD coverage/digests
and allowed installed payload are validated before installation.

The runtime checker resolves --out relative to the caller before changing the
child working directory. Its verification_scope records whether the timed command
checked only core resources or also a complete outer delivery. Release staging
uses the former. Do not compare measurements with different verification scopes.

Before freezing, stop current runs and ensure no run.lock or .tmp/.part/.partial
files remain in current packages, validation or review materials. The gate rejects
such residue; it never removes a live lock. Historical version directories preserve
earlier evidence unchanged, including explicitly historical process residue.

## Version 0.4.5 complete report and package checks

All deterministic reproduction fields are compared in full with reconstruction:
per-task rows, families, splits, historical and extension subsets, primary and
alternative evidence results, both lexical methods, traces, comparison rows,
mutation records, release data and input/code hashes. Context predictions are
now archived explicitly. CSV bytes must match the reconstructed per-task report.
The primary results/paper report is checked by check_release.py; process reports
are checked by complete-delivery verification. The primary report's core hash
records its staging snapshot, before inclusion in the final core, and is not a
self-hash. Process evidence binds the final core.

Timing requires 30 finite positive raw observations, an integer matching count,
and exact recomputation of median/minimum/maximum. This establishes consistency,
not independent clock or host authentication. Installed package filenames and
.dist-info/source roots must match nhanes_cardiobench and the current version;
wheel tags remain py3-none-any. Requires-Python must be >=3.10, with no runtime
Requires-Dist dependencies, matching the release's standard-library-only contract.
Installation of both the exact wheel and an offline sdist rebuild remains required.

Only v0_3_1 and v0_4_0 through v0_4_7 are registered historical directories for
residue exemptions. Current and unknown version directories receive the same
lock and temporary-file checks as other current paths. History is never relabelled.

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
