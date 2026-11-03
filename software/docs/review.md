# Independent review procedure

Status: materials prepared; zero independent reviewers and zero adjudications.
A coordinator gives each reviewer reviewer_inputs.json, frozen sources/ and only
that reviewer's blank CSV. Keep expected_answers_after_review.json and the other
reviewer's work separate until both submissions are committed with identities and
dates. The released benchmark is public, so blinding cannot be guaranteed.

Reviewers independently enter a complete proposed_response_json and source-grounded
rationale for each of 104 checks, noting policy concerns and ambiguity. Preserve
both initial submissions. Compare status, answer, evidence and reason separately;
record disagreements and denominators before consensus. An adjudicator records
both proposals, final response, rationale, identity and date in adjudication.csv.
Do not infer agreement from blank rows or pending status. Update gold only after
reviewed decisions and version the changed benchmark; do not silently rewrite it.
Actual agreement rates require completed human submissions and are not supplied.

# Development tutorials

examples/development_examples.json supplies four authored examples: indirect label
leakage, cyclic dependencies, weighted synthetic execution and duplicate join keys.
They include expected responses for practice and introduce no scored tasks or split
changes. The automated tutorial regression verifies all four with the reference
implementation. Independent evaluation of those examples has not been performed.

Validate actual completed submissions and compute pre-adjudication field agreement with:
`python -m cardiobench.review --reviewer-a A.csv --reviewer-b B.csv --out comparison.json`
Blank, missing, duplicate, malformed and mixed-reviewer rows are rejected. Two distinct reported reviewer IDs are required. The utility reports disagreements and keeps adjudication pending. Identity, expertise and independent work remain coordinator responsibilities; software cannot certify them. The supplied forms remain blank.


## Review format 2 and input commitments

The supplied review_input_sha256 column is populated before distribution. Keep it
unchanged on every submitted row. reviewer_inputs.json includes its complete
identity: format 2, suite version, contract 1.2, core manifest SHA-256, release
metadata SHA-256, and canonical-JSON hashes of tasks, catalog and candidate
contracts. Compare verifies the release first and requires both submissions to
match the exact current identity. File hashes preserve each submitted CSV as well.
These are reviewer-retained commitments, not signatures or proof of independence.
Unbound older forms are rejected. Do not insert a current hash into an old review;
review the new inputs and submit a new form, or use the original software/inputs.

CSV is UTF-8 (an initial BOM is accepted), with strict quoting and exactly the
seven supplied columns. Limits: 16 MiB raw file; 65536 Unicode characters per field;
65536 UTF-8 bytes per proposed_response_json. The JSON depth rules still apply.
Quoted commas/newlines are supported. Oversized fields, malformed quoting and
invalid UTF-8 produce controlled errors without a comparison output. A CSV parser
error identifies the physical line when available; column attribution is not
always available from Python's CSV parser.
