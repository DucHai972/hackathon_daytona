# A corrupt settings file is silently ignored

`load_settings()` is supposed to fall back to the default only when the file is
genuinely absent. A file that exists but contains broken JSON is a real problem
and must be surfaced as a `ConfigError` so the operator sees it.

Right now a truncated settings file boots the service on default settings with
no warning at all. We lost an hour to this last week because the service looked
healthy while running with the wrong configuration.

```python
open("settings.json", "w").write("{not json")
load_settings("settings.json", default={"mode": "safe"})
# -> {'mode': 'safe'}, no error, no log line
```

Missing-file fallback should keep working exactly as it does today.
