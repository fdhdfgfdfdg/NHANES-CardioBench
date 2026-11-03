# Protocol 0.4.8

## Scope and provenance

Twelve official 2017-2018 component codebooks and the official weighting tutorial
form the preserved corpus. The 383 entries are variable **occurrences**; repeated
SEQN and weight fields are not distinct constructs. Official variable names are
normalized to upper case for matching, while original URL anchors are preserved.
Source-page SHA-256 digests identify the actual retrieved snapshots. The source
corpus is frozen; live website changes do not silently replace it.

The supplied research outline motivated the scope and identified candidate error
types. Its informal model responses are not experimental observations and are
not redistributed or attributed as model performance. Gold annotations were
curated with AI assistance against the preserved sources; independent human dual
annotation has not been performed. Independent review should check each task,
gold field and evidence link, with disagreements logged before publication.

## Workload identity

In the historical inventory, semantic, coding, weight and dependency families each contain 16 canonical items.
The historical execution family contributes one canonical workload with 16 check variants. Version 0.4.0 adds 12 dependency and 12 execution workloads with distinct canonical IDs; six of each family are development checks and six are evaluation checks. Counts in 0.4.0 are 89 canonical workloads, 104 checks, 31 workflow groups, 32 development checks and 72 evaluation checks. No member of a workflow group crosses subsets. Shared
official facts and clinical constructs still occur across groups. Neither
workflow-group separation nor public release establishes training-data exclusion.
All reported results exhaust the specified finite inventory; no confidence
interval or population generalization is asserted from the small curated set.

## Five typed contracts

Semantic outputs identify the variable and component file. Coding outputs give
the unit or field-specific recoded/conversion values. Weight outputs identify
the weight and masked stratum/PSU fields. Dependency outputs give a sorted set
of excluded feature names. Execution outputs give joined row count, cohort count
and a weighted mean, or reject malformed fixtures using a declared reason code.

All responses have status, answer, evidence and reason_code. Answers require a
null reason code; abstention/rejection requires a nonempty one. Absent evidence
does not earn a joint pass even if the numerical answer is correct. Extra answer
fields cannot match the exact expected object. Evidence must be the exact
expected identifier set: valid but irrelevant source IDs cannot rescue an answer.
Identifier matching does not automatically establish explanatory entailment.

## Author-defined policies

1. Joint fasting/dietary weight selection is declined when no joint selection or
   nonresponse adjustment is supplied. This is a conservative release policy;
   it does not assert that joint dietary/laboratory analysis is impossible.
2. Dependency exclusion uses a declared directed graph. Any feature whose
   transitive dependency set intersects a declared label-source set is excluded.
   This does not discover unstated algebraic relations, measurement timing or
   all clinical proxies. Cyclic graphs are rejected before tracing.
3. Synthetic execution uses a one-to-one left join on SEQN, a stated age domain,
   nonmissing finite outcomes and positive finite weights. Zero weights are not
   eligible; negative weights and duplicate keys are invalid. A missing outcome
   or unmatched right record is excluded from the mean but retained in the left
   row count. Valid zero outcomes are retained. No variance or population estimate
   is computed from synthetic data.

## Baselines and controls

The positive control uses a separate authored semantic routing fixture and
deterministic operations. It tests scorer conformance and must never be ranked
as an independently generalizing model. Both routes and gold answers are omitted
from candidate exports. BM25 operates on official SAS labels, with k1=1.2 and
b=0.75, the shipped stop list and deterministic original-order tie breaking.
It neither uses question text/synonym expansion nor supports nonsemantic tasks.
This is an intentionally limited transparent retrieval baseline, not a claim
about state-of-the-art retrievers.

Three response perturbations per check alter content/reason, evidence or status.
The 312 perturbed records reuse the same 104 checks and are scorer sensitivity
tests. Their detection rate is not a clinical error-detection or model-safety rate.

## Fair comparison obligations

Fill the run-disclosure JSON for each actual external system. Freeze task/corpus
hashes and subsets; separate information-access tracks; document all prompts,
system/checkpoint versions, date, seeds or nondeterminism, tool limits, retries,
token limits, caches, hardware, complete requests/completions and incurred costs.
Unknown cost and training contamination must be reported as unknown, not zero.
Missing/failed outputs count against the chosen denominator. Limit results to
supported families and common tracks rather than ranking partial systems on
different denominators. If repeated runs or prompt variants are introduced,
retain canonical IDs and summarize within workflow groups before inference.

Demographic fairness is separate from equal information/resource access. This
release includes no patient-level prediction model and cannot estimate clinical
group disparities. The fixture demographic swap tests only that fields declared
irrelevant to the numerical recipe do not change its output. A later demographic
study requires real eligible data, suitable survey weights, group counts, design
uncertainty, and a justified clinical estimand.

## Timing and maintenance

Thirty warm in-process positive-control repetitions exclude installation,
metadata loading, download and rendering. A separate clean-interpreter command
measurement includes JSON loading, hashing, both builtin runners, perturbation
checks, repeat timings and report writing, but excludes acquiring Python and
extracting the archive. Shared host scheduling can change timings; recorded
runtime is a reproducibility aid, not a hardware or model speed ranking.

Version 0.4.8 denotes this supplied candidate distribution. No public tag, DOI,
online CI success or independent reviewer account is claimed. Corrected answers,
changed scope or grading thresholds require a new version and explicit result
differences; a future permanent deposit should preserve earlier frozen releases.

## First correctness revision 0.1.1 (historical)

The frozen v0.1.0 tasks and expected responses are retained byte-for-byte.
Version 0.1.1 makes integer references exact, validates answer field types against
the frozen expected contract, rejects whitespace-only reasons and nonempty
non-answer payloads, and rejects nonfinite JSON numbers including exponent
overflow. Non-answer tasks still grade unexpected answer content as an answer
mismatch; no alternative gold answers or evidence sets have been added.
Fixture keys are positive integers, ages and minimum age are finite nonnegative
numbers excluding booleans, all right outcomes are checked, and required fields
and row containers are validated before execution. Weighted arithmetic uses
50-digit Decimal intermediates and a finite binary-float result.

The 25 new regression methods are software tests, not additional benchmark
workloads. Development still has no dependency or execution tasks. Gold
adjudication, new independent workloads, package installation, model API runs,
full provenance orchestration and resumable execution are outside this revision.

## Second revision 0.2.0 (historical)

This revision adds an authoritative resumable checkpoint and installation
artifacts. docs/runs.md defines binding, failure, retry, access-track, concurrency
and capture-limit semantics. Completed failures remain in the denominator; an
explicit retry preserves prior attempts and scores the latest one. A checkpoint
contains one committed result per selected case and retains all retry attempts.
An interrupted external operation without a committed result can be repeated,
so resume does not promise exactly-once remote execution.

Source parsing uses only HTMLParser and frozen snapshots. The normalized section
text hash exactly reproduces the previous hashes. All 383 parsed records and the
task, gold, catalog and semantic-route files remain byte-identical to 0.1.1.
Release metadata documents the hash scheme. Full regeneration occurs in a
temporary tree and checks all five generated JSON files. The parser is tested
against these 12 codebooks; it is not a general scraper for later NHANES cycles.

There are 93 automated test methods (67 retained plus 26 added). A wheel and
source distribution are supplied, with installation checked locally on Linux
CPython 3.12.14. The CI matrix is configuration only, not cross-version evidence.
Independent annotation, new independent workloads and external model comparisons
remain future validation. No participant-level or clinical claim is added.

## Current scoring and numerical contracts

Candidate exports and adapter stdin include the same answer-free response contract: task-family fields, exact status/reason vocabulary, identifier syntax, canonical unit spellings and numeric comparison rules. Closed-book delivery includes this protocol but omits the source catalog. Neither export includes gold answers or positive-control routes.

Primary counts preserve strict evidence equality. A separate policy_adjusted result permits the documented alternative W11 evidence sets from GLU_J and TRIGLY_J, including both together. This is a versioned author-defined rule supported by frozen source entries, not completed independent adjudication or a new clinical-validity measure. Wrong answers and irrelevant additional evidence still fail.

Weighted computation now accumulates exact rational representations of decimal input strings and rounds only the final mean to a finite float. This removes the 50-digit Decimal cancellation error, including [1e100, 1, -1e100] under unit weights. Synthetic stress values need not be physiologically plausible. The historical numeric comparison tolerances remain unchanged.

Historical tasks and gold remain identical as objects for the first 80 checks. Results explicitly separate those 80 from the 24 added checks. Added tasks are author-curated synthetic designs, not independent human annotations. Public evaluation data are not claimed to be hidden or uncontaminated.


## Revision 0.4.1 contract alignment

Contract 1.1 derives exported schemas and task-family runtime validation from the
same field specifications. Protocol constraints supplement JSON Schema: integers
must be JSON integer tokens, all numbers finite, response depth at most 32,
and evidence identifiers nonblank. Global reason codes are enumerated. Coding
cleaning accepts retained number/string/null values; conversion accepts numbers.
Task preflight validates required request fields and gold response shape, while
malformed execution rejection fixtures remain deliberate benchmark inputs.
Dependency tracing is iterative, checks disconnected cycles and permits at most
10,000 nodes and 100,000 unique directed edges. Secondary-policy rows recompute
their own diagnostic while retaining primary_error.

Mutation protocol 1.1 replaces 34 historically invalid non-answer mutations with
a different enumerated reason or the other non-answer status. Task, gold, routes
and catalog are unchanged; old and new mutation protocols must be labelled.


## Revision 0.4.2 explicit task contracts

Contract 1.2 retains the response fields and numeric tolerances from 1.1, but
requires `grade(actual, expected, task)`. Omitting task raises TypeError; None
raises TASK_REQUIRED_FOR_ANSWER_SCHEMA. The scorer never guesses the cleaning or
conversion schema from expected values, including abstention gold. summarize
supplies each task explicitly. A caller must supply the actual task being scored.

Alternative evidence is restricted to the suite version and a canonical-JSON
SHA-256 of the entire original task. A reused ID or modified prompt/request does
not inherit a released exception. Custom tasks still receive primary scoring.
Cleaning validation and execution-fixture validation are shared with runtime.
Ordinary nonnumeric strings are retained, numeric nonfinite strings are invalid,
and literal missing codes are applied per codebook. Fixture validation distinguishes
left age/weight fields from right outcomes even if column names coincide. Deliberate
rejection fixtures are not forced to pass the answerable-input preflight.

## Revision 0.4.5 scoring gold binding

Alternative evidence now requires both the original task and complete gold response
fingerprints, in addition to suite version. A modified custom gold object receives
primary scoring without the released alternative. JSON key order has no effect on
canonical fingerprints. The 104 released tasks and gold responses are unchanged.
Complete-delivery-v3 checks evidence content and input bindings as described in
docs/release.md. Path tests include Windows semantics without claiming a Windows run.

## Version 0.4.4 numeric and delivery behavior

Glucose conversion scales decimal-input rational values, rounds to three decimal
places using ties-to-even and converts once to a finite float. A result outside
that range returns NONFINITE_RESULT; booleans and nonfinite inputs are invalid.
The factor remains 0.05551 and all released conversion answers are unchanged.
Contract 1.2 and mutation protocol 1.1 remain in effect. Complete-delivery-v4
validates derived reports and installed console observations as described in
release.md. The current suite/code binding prevents reuse of older checkpoints.

## Version 0.4.5 bounded integers and portable task IDs

Contract 1.3 defines a maximum of 4096 decimal digits for JSON and numeric task
integers (absolute value strictly below 10**4096). Preflight and JSON parsing
reject larger values using INTEGER_LIMIT_EXCEEDED; direct reference conversion
and execution return the same schema-valid rejection. Booleans remain excluded.
Integer-to-rational conversion uses the integer directly. No global interpreter
conversion limit is disabled. Supported 400-digit weights can still yield a small
finite weighted mean; out-of-range inputs are rejected even if cancellation would
produce a representable result. NONFINITE_RESULT describes a final conversion or
weighted result outside finite binary-float range.

Task IDs must also be portable request filenames: CON, PRN, AUX, NUL, COM1-COM9
and LPT1-LPT9 are forbidden case-insensitively. Distinct IDs whose case-folded forms
match are rejected before output creation. Ordinary names such as COM10 and
CONTEXT remain valid. These checks do not claim an actual Windows execution.

Complete-delivery-v5 validates the entire deterministic reproduction report,
three prediction archives, CSV output and internally consistent positive timing
observations. See release.md. Contract 1.3 changes protocol commitments while
preserving all 104 released tasks/gold responses and mutation protocol 1.1.

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
