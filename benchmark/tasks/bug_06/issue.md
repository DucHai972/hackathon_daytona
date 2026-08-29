# Leaderboard ties are in the wrong order

The leaderboard is documented as: highest score first, and players on the same
score listed alphabetically by name. The scores come out in the right order but
tied players appear in whatever order the database happened to return them.

```python
entries = [
    {"name": "zoe", "score": 10},
    {"name": "adam", "score": 10},
]
rank(entries)
# -> zoe, adam   (expected adam, zoe)
```

It looks stable rather than random, so the tie-break just is not being applied.
