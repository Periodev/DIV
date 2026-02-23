# Cross-Implementation Trace Comparison — Test Workflow

> Purpose: verify that Python core (`timeline_system.py`, `game_controller.py`, …)
> and GDScript core (`Timeline.gd`, `GameController.gd`, …) produce identical
> game states for any given level + move sequence.

---

## Prerequisites

| Tool | Path |
|---|---|
| Python 3.10+ | `python` or `python3` |
| Godot 4.5.1 console | `D:/Godot/Godot_4.5.1/Godot_v4.5.1-stable_win64_console.exe` |
| Working directory | `D:/DIV/DIV_Godot` |

---

## 1. Run both trace runners

```bash
# Python side
python tools/trace_runner.py <level_idx> "<moves>" > tmp/py.json

# GDScript side (strip engine header line)
D:/Godot/Godot_4.5.1/Godot_v4.5.1-stable_win64_console.exe \
  --headless --script res://scripts/TraceRunner.gd \
  --path godot \
  -- <level_idx> "<moves>" 2>/dev/null \
  | grep -v "^Godot Engine" > tmp/gd.json
```

**Examples:**

```bash
python tools/trace_runner.py 0 ""              # initial state only
python tools/trace_runner.py 1 "UURR"          # 4 moves
python tools/trace_runner.py 0 "UUDDVTULRC"   # branch + switch + merge
```

Level index mapping:
- `0` = Level 0-1 (tutorial)
- `1` = Level 1-1
- … or use the level id string: `python tools/trace_runner.py 0-1 "UURR"`

---

## 2. Diff outputs

```bash
diff tmp/py.json tmp/gd.json
```

If the files are identical, `diff` exits 0 (no output).

---

## 3. Structural comparison (find first diverging step)

```python
# tools/diff_trace.py  (run as: python tools/diff_trace.py tmp/py.json tmp/gd.json)
import json, sys

py = json.load(open(sys.argv[1]))
gd = json.load(open(sys.argv[2]))
print(f"Steps: py={len(py)} gd={len(gd)}")

diffs = []
for i, (ps, gs) in enumerate(zip(py, gd)):
    if ps == gs:
        continue
    def find_diff(a, b, path=""):
        if type(a) != type(b):
            diffs.append(f"TYPE {path}: {type(a).__name__} vs {type(b).__name__}")
            return
        if isinstance(a, dict):
            for k in sorted(set(a) | set(b)):
                find_diff(a.get(k), b.get(k), f"{path}.{k}")
        elif isinstance(a, list):
            for j in range(max(len(a), len(b))):
                find_diff(
                    a[j] if j < len(a) else None,
                    b[j] if j < len(b) else None,
                    f"{path}[{j}]")
        else:
            if a != b:
                diffs.append(
                    f"step[{i}]({ps['move']!r}) {path}:\n"
                    f"  py = {a!r}\n"
                    f"  gd = {b!r}")
    find_diff(ps, gs)
    break   # stop at first diverging step

if diffs:
    for d in diffs[:30]:
        print(d)
    sys.exit(1)
else:
    print("IDENTICAL")
```

---

## 4. Canonical JSON schema

Both sides produce **identical** JSON. Keys are alphabetically sorted at every
level (`sort_keys=True` in Python, default in Godot `JSON.stringify`).

```json
[
  {
    "move": "",
    "state": {
      "collapsed": false,
      "current_focus": 0,
      "has_branched": false,
      "main_branch": {
        "entities": [
          {
            "collision": 1,
            "direction": [0, 1],
            "fused_from": [],
            "holder": -1,
            "pos": [1, 6],
            "type": 0,
            "uid": 0,
            "weight": 1,
            "z": 0
          }
        ],
        "grid_size": 7,
        "next_uid": 5,
        "terrain": {
          "0,0": 1,
          "1,0": 8
        }
      },
      "sub_branch": null,
      "victory": false
    },
    "step": 0
  },
  ...
]
```

**Encoding rules** (both sides must follow):

| Field | Encoding |
|---|---|
| `terrain` keys | `"x,y"` strings, sorted by (x ascending, then y ascending) |
| `terrain` values | int matching `Enums.TerrainType` (FLOOR=0 … HOLE=9) |
| `entities` | array sorted by `uid` ascending |
| `holder` | int; `−1` = not held, `0` = held by player |
| `fused_from` | sorted int array (empty = `[]`) |
| `direction` | `[dx, dy]` array |
| `pos` | `[x, y]` array |
| `type` | int (PLAYER=0, BOX=1) |

---

## 5. Move character reference

| Char | Action |
|---|---|
| `U` `D` `L` `R` | Move up/down/left/right |
| `V` | Branch (diverge) |
| `C` | Merge (normal converge) |
| `F` | Fetch-merge |
| `T` | Switch focus (DIV 0 ↔ DIV 1) |
| `X` | Adaptive: drop if holding, converge if shadow ahead, else pickup |
| `P` | Pickup |
| `O` | Drop |
| `Z` | Undo |

---

## 6. CI integration pattern

```bash
#!/usr/bin/env bash
# scripts/ci_trace_check.sh
# Run a suite of level+moves pairs and verify Python==GDScript for each.
set -e

GODOT="D:/Godot/Godot_4.5.1/Godot_v4.5.1-stable_win64_console.exe"
CASES=(
  "0 ''"
  "1 'UURR'"
  "0 'UUDDVTULRC'"
  "2 'LLUURRVVTCC'"
)

mkdir -p tmp
PASS=0; FAIL=0

for case in "${CASES[@]}"; do
  idx=$(echo $case | awk '{print $1}')
  moves=$(echo $case | awk '{print $2}' | tr -d "'")
  python tools/trace_runner.py $idx "$moves" > tmp/py_ci.json
  "$GODOT" --headless --script res://scripts/TraceRunner.gd \
    --path godot -- $idx "$moves" 2>/dev/null \
    | grep -v "^Godot Engine" > tmp/gd_ci.json
  if diff -q tmp/py_ci.json tmp/gd_ci.json > /dev/null; then
    echo "PASS  level=$idx moves='$moves'"
    ((PASS++))
  else
    echo "FAIL  level=$idx moves='$moves'"
    python tools/diff_trace.py tmp/py_ci.json tmp/gd_ci.json | head -20
    ((FAIL++))
  fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
```

---

## 7. When to run

- After any change to `Timeline.gd`, `Physics.gd`, `GameLogic.gd`, `GameController.gd`
- After any change to `timeline_system.py`, `physics.py`, `game_logic.py`, `game_controller.py`
- Before merging a PR that touches core game logic

The workflow catches **logic divergence at the exact step level**, making it
easy to locate which action triggered the disagreement and which field differs.
