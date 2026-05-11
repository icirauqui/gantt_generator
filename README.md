# Gantt PNG Generator

Generate the two sample-style Gantt diagrams:

```bash
UV_CACHE_DIR=.uv-cache uv run python main.py
```

The default input is `gantt_data.json`. Use another data file with:

```bash
UV_CACHE_DIR=.uv-cache uv run python main.py --data path/to/data.json
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
