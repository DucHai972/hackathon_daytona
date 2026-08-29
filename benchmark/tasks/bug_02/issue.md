# Dashboard crashes when a metric has no samples

The stats helpers are called once per metric when the dashboard renders. If a
metric collected no samples in the selected time window the whole dashboard
returns a 500 instead of rendering an empty cell.

Traceback from production:

```
  File "stats.py", line 12, in mean
    return sum(values) / len(values)
ZeroDivisionError: division by zero
```

The documented contract for these helpers is that an empty sequence has no
average and no middle value, so they should report "no value" rather than
raising. Please make the helpers honour that contract.
