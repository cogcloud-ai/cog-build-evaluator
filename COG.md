---
type: cog [0.1]
name: cog-build-evaluator
description: "Context Cog. Designs independent Cog acceptance cases and assesses supplied candidate evidence. Depends on a Cog providing an OpenAI-compatible model endpoint."
version: "0.1.0"
license: BSD-3-Clause
publisher: OpenTeams
manifest: cog.yaml
manifest_schema: openteams/cog-manifest [0.1]
---

# Cog Build Evaluator

Designs acceptance cases and evaluates supplied evidence for a candidate Cog.
The consumer is the Builder Op or a human reviewer. plan and review are selected
through the operation field of ask; HTTP uses the same contract.

Input: an accepted work contract, candidate source snapshot and candidate-bound
execution/inspection evidence. Output: test cases, one assessment per criterion,
and source-grounded findings. plan covers happy, insufficient, adversarial and
boundary cases; review distinguishes pass, fail and not_tested. Missing execution
evidence never becomes a pass. Evidence IDs, quotes, criterion coverage and the
relationship between individual assessments and the overall result are checked.

The Op executes test cases and supplies results. This Cog does not run untrusted
code, change candidates, authenticate evidence, or make release decisions.
The source fingerprint binds reports to supplied bytes, not to a proven execution.
Model judgment is fallible; deterministic checks and human acceptance remain
separate. Unsupported work abstains with a reason. Inspection is useful for
finding defects but is insufficient to establish runtime correctness.

## Use and verification

Install with `pixi install`, bind with `pixi run resolve` or `pixi run use`, then
check model identity with `pixi run check -- --deep`. Invoke with
`pixi run ask -- --bundle examples/sample-bundle.json`; `pixi run serve` exposes
the declared HTTP endpoint. `pixi run test` runs model-free tests;
`pixi run eval` executes declared fixtures against the bound model.

Results use envelope v1 with payload, problems and binding identity. An ok result
may contain contract problems; the caller's Gate decides acceptance. Locality is
declared in the manifest; the installed binding chooses a compatible model.
The workspace-relative default satisfier is optional convenience, not a bundled
model. Independent installations must supply their own model binding.
