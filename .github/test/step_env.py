"""Print the env: of one step of action.yml as shell export lines.

Usage: step_env.py STEP_ID [--outputs STEP=FILE] [INPUT=VALUE ...]

${{ inputs.NAME }} becomes the VALUE given for NAME, else the default of that
input in action.yml. ${{ steps.STEP.outputs.NAME }} becomes the value of NAME
in FILE, the $GITHUB_OUTPUT that STEP wrote, and is empty when no FILE is
given for STEP. Any other expression, and an input that action.yml does not
declare, is an error, so a test never runs a step with a value the action
would not give it.
"""

import re
import shlex
import sys

import yaml

EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}")

args = sys.argv[1:]
step_id = args.pop(0)
outputs_files = {}
overrides = {}
while args:
    arg = args.pop(0)
    if arg == "--outputs":
        step, _, path = args.pop(0).partition("=")
        outputs_files[step] = path
    else:
        name, _, value = arg.partition("=")
        overrides[name] = value

action = yaml.safe_load(open("action.yml"))
inputs = {name: str(spec.get("default", "")) for name, spec in action["inputs"].items()}
unknown = sorted(set(overrides) - set(inputs))
if unknown:
    sys.exit(f"not an input of action.yml: {', '.join(unknown)}")

outputs = {}
for step, path in outputs_files.items():
    outputs[step] = {}
    for line in open(path):
        name, _, value = line.rstrip("\n").partition("=")
        outputs[step][name] = value


def resolve(match):
    expression = match.group(1).strip()
    found = re.fullmatch(r"inputs\.([A-Za-z0-9_-]+)", expression)
    if found:
        name = found.group(1)
        if name not in inputs:
            sys.exit(f"step {step_id} reads inputs.{name}, which action.yml does not declare")
        return overrides.get(name, inputs[name])
    found = re.fullmatch(r"steps\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)", expression)
    if found:
        return outputs.get(found.group(1), {}).get(found.group(2), "")
    sys.exit(f"step {step_id} has an expression this test cannot give a value: ${{{{ {expression} }}}}")


step = next(s for s in action["runs"]["steps"] if s.get("id") == step_id)
for name, value in (step.get("env") or {}).items():
    print(f"export {name}={shlex.quote(EXPRESSION.sub(resolve, str(value)))}")
