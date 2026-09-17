# Cog Build Evaluator

Independent acceptance planning and evidence assessment for a Cog-building Op.
This is a separate context Cog from cog-author and from the older demo evaluator.

## Run

```sh
pixi install
pixi run test
pixi run resolve
pixi run check -- --deep
pixi run ask -- --bundle examples/sample-bundle.json
```

The default model reference is workspace-relative. Independent installations
must supply an available compatible model with `resolve` or `use`. Both CLI and
HTTP use the same schema and envelope v1. Model identity is recorded per result.

## Plan, execute, review

1. Invoke `ask` with `operation: plan`, the accepted work contract and candidate
   files. The author's exported `eval-plan.json` has this shape. Every criterion
   receives test coverage across happy, insufficient, adversarial and boundary
   cases. These are test specifications, not automatically executable commands.
2. The Builder Op executes cases in its authorized environment. This evaluator
   does not execute candidate code. Preserve observed outputs and test outcomes.
3. Attach evidence, switch to `operation: review`, and invoke `ask` again.

Each evidence record contains `id`, `criterion_id`, `candidate_sha256`, `kind`
(`execution` or `inspection`), `status` (`passed`, `failed`, `not_run`), and
`text` containing the actual observation. Compute the candidate fingerprint with:

```sh
pixi run python scripts/fingerprint.py candidate-review.json
```

The fingerprint covers canonical UTF-8 JSON of the accepted contract and the
complete supplied file list sorted by path (object keys sorted, separators
`,` and `:`, Unicode unescaped). Evidence is excluded from its own fingerprint.
Changing a source byte or the contract invalidates old evidence. The Op is
responsible for supplying a complete snapshot and truthful execution records.
The digest authenticates neither the caller nor execution.

## Result meanings

| Classification | Meaning |
|---|---|
| planned | Test cases proposed; no claim they ran |
| pass | Every criterion has cited passed execution evidence and no error findings |
| revise | Failed criterion or source-grounded error finding |
| insufficient_evidence | At least one criterion remains not tested |
| abstained | Task could not be assessed; reason supplied |

A reviewer can reject a test's apparent success when its actual observation
contradicts the contract. A failed execution cannot be silently ignored.
Inspection or an author's assertion cannot establish a runtime pass. Every
assessment cites matching criterion evidence and a verbatim quote; source
findings quote the exact candidate file. Mechanical grounding does not establish
semantic correctness. `pass` is an assessment, not human approval or release.

## Verification

`pixi run test` exercises missing/stale evidence, false passes, fabricated quotes,
criterion coverage, source findings, candidate identity, malformed inputs and
envelope behavior with a mocked model. `pixi run eval` runs four model-backed
fixtures, including source injection and claims unsupported by execution evidence.
The test suite does not establish the judgment quality of any live model.

```sh
pixi run python ../cog-smith/src/cogsmith_cli.py check . --tests
pixi run python ../cog-spec/tools/validate_cog.py .
```

Only src/task_logic.py is author-owned under src; shared Smith machinery remains
hash-verified. The Op owns execution, retries, durable records and final Gates.

## Workbench suite integration

The declared `composition` interface lets workbench prepare the packaged context
and run this Cog's existing checks around an external harness turn. Workbench
can execute planned cases against an exact packaged source snapshot and produce
a fingerprinted review request. Its execution status describes envelope and
packaged-check completion; this evaluator still assesses the acceptance criteria.
Subscription compositions are labeled as system evidence, never bare-model
benchmarks. Separate author/evaluator Cogs do not prove model independence.

### Executable case boundary

Every planned case input is one concrete bundle that validates against the candidate's
accepted input schema and is sent unchanged to that Cog. Matrices, procedures, output
mutation instructions and input-construction recipes are not supported case inputs.
Invalid-input validation, output mutation, capacity and external-side-effect checks
need separately supplied execution evidence. Ordinary successful turns do not prove
those properties. The reviewer must retain insufficient evidence where necessary.
