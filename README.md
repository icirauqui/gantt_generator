# Gantt PNG Generator

Generate the default actual/progress Gantt diagram:

```bash
uv run python main.py
```

The default input is `gantt_data.json`. Export a named image to `exports/` with:

```bash
uv run python main.py --data gantt_data.json --output-dir exports --output-name r4
```

Choose which chart to render with `--chart actual` or `--chart plan`. The old two-file behavior is still available with:

```bash
uv run python main.py --chart both
```

The JSON file should define `current_period`, optional `periods`, and a dynamic `stages` list:

```json
{
  "current_period": 20,
  "periods": ["octubre-22", "noviembre-22"],
  "stages": [
    {
      "name": "Stage 1",
      "plan_start": 1,
      "plan_duration": 1,
      "actual_start": 1,
      "actual_duration": 1
    }
  ]
}
```

`current_period` controls the vertical orange marker in the actual/plan chart. Period and stage numbers are 1-based.
