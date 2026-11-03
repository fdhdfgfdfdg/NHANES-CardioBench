Review format 2: retain review_input_sha256 exactly as supplied. It binds the
reviewed tasks, catalog, response contracts, suite version and core manifest.
Old unbound forms are rejected; do not assign a new hash to an old submission.
UTF-8 CSV limits: 16 MiB per file, 65536 characters per field, 65536 UTF-8
bytes per proposed response. Strict CSV parsing rejects malformed quoting.
Independent review has NOT been performed. All decisions are blank or pending.
Coordinator: distribute only reviewer_inputs.json, the frozen official snapshots,
and one blank reviewer CSV to each reviewer. Do NOT distribute the expected-answer
file or the other reviewer's form before independent responses are committed.
Review each response, evidence link, ambiguity and authored policy. Freeze both
forms before comparison with expected_answers_after_review.json. Resolve differences
in adjudication.csv with a named adjudicator, rationale and date. Keep unresolved
cases pending. Record identity and expertise with consent; do not infer agreement
from blank fields. These are preparation materials, not a blinding enforcement
system, inter-rater statistic or completed human validation. The comparison CLI validates
task-family response shape without consulting gold values; it preserves hashes,
review dates, rationales and concerns. Matching proposals are not verified truth.
