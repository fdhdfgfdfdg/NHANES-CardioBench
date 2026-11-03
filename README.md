# NHANES-CardioBench 0.4.8

A reproducible benchmark for AI-assisted NHANES survey-analysis preparation. The release uses frozen public metadata and synthetic fixtures, with no participant records or external model calls.

## Authors

**Chuanhao Nie** — College of Computing, Georgia Institute of Technology, Atlanta, GA 30332, USA. Email: cnie30@gatech.edu. ORCID: [0009-0006-4208-6414](https://orcid.org/0009-0006-4208-6414).

**Yisong Chen, corresponding author** — College of Computing, Georgia Institute of Technology, Atlanta, GA 30332, USA. Email: ychen841@gatech.edu. ORCID: [0009-0009-4978-7565](https://orcid.org/0009-0009-4978-7565).

## Download software and manuscript

- Download the complete [0.4.8 software ZIP](NHANES_CardioBench_v0.4.8.zip) and verify [SHA256SUMS.txt](SHA256SUMS.txt).
- Browse the expanded [software source and evidence](software/). In a Git clone, enter `software/` before running the commands below.
- The [v0.4.8 research release](https://github.com/fdhdfgfdfdg/NHANES-CardioBench/releases/tag/v0.4.8) contains the complete ZIP, wheel, source distribution, [updated manuscript](NHANES_CardioBench_v0_4_8_Complete.docx) and checksums.
- [Detailed user guide](software/README.md), [protocol](software/docs/protocol.md), [installation and release validation](software/docs/release.md), and [runner documentation](software/docs/runs.md).

## Quick start

Use CPython 3.10 or later. Runtime dependencies are Python's standard library only. From the extracted complete software root, or from `software/` in this repository:

```sh
python -m cardiobench verify --require-artifacts
python -m cardiobench reproduce --out results/reproduced
python -m unittest discover -s tests -v
```

Use a fresh output folder. Existing paper evidence and historical records are retained. The complete ZIP includes one wheel and one source distribution under `packages/`; installation can be performed offline with `--no-index --no-deps` as described in the detailed guide.

## Verified local results

- 13 frozen official snapshots; 383 variable occurrences from 12 component codebooks.
- 89 canonical workloads and 104 checks across five task families.
- Authored positive control: 104/104 strict joint passes.
- Label-only BM25: 11/16 semantic checks; context-field BM25: 9/16.
- All 312 format-valid response perturbations detected.
- All 445 automated test methods passed on CPython 3.12.14/Linux.
- Complete-delivery-v8 verification, byte regeneration, clean wheel installation, offline source-distribution rebuilding and five-to-thirty-two-case resume passed after the author metadata update.

The [publication workflow](https://github.com/fdhdfgfdfdg/NHANES-CardioBench/actions/workflows/publication.yml) expands the exact checksum-verified delivery into `software/` and tests the configured Linux, Windows and macOS combinations with Python 3.10, 3.12 and 3.13. CI resolves TEMP, TMP and TMPDIR to canonical runner paths for path comparisons, and stores generated CI evidence outside the frozen source tree. Completed [public CI jobs](https://github.com/fdhdfgfdfdg/NHANES-CardioBench/actions/runs/41610390028) have passed on Linux and Windows with Python 3.10, 3.12 and 3.13, and on macOS with Python 3.10 and 3.12. The linked run tracks the remaining configured combination and any later results. The manuscript states the combinations verified at its preparation checkpoint.

## Interpretation and provenance

The controls establish conformance to this finite, authored inventory. They do not establish independent annotation validity, clinical utility or generative-model superiority. Independent human adjudication and external-model experiments remain incomplete. Review forms are blank and adjudications remain pending.

The source ZIP was rebuilt only to synchronize publication metadata and the resulting integrity bindings. Runtime modules, tests, official metadata snapshots, task resources and maintainer tool code match the supplied 0.4.8 distribution byte-for-byte. Historical evidence is retained under its original version directories. The frozen source's earlier pending-CI wording describes its preparation stage; remote results are reported by the linked publication workflow.

MIT applies to code. The supplied copyright notice and official-source attribution notices are retained. No Zenodo DOI or Software Heritage registration is asserted for this release.
