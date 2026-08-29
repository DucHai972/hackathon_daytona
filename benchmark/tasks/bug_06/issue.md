# Pipeline steps run in the wrong order and a cycle hangs the UI

Two reports from the release pipeline.

First, a step ran before the step it depends on:

```
pipeline: assets depends on deploy
executed: assets, deploy      <- assets built against the previous release
```

Second, someone defined `lint` depending on `format` and `format` depending on
`lint`. Instead of being told their pipeline is impossible, they got an order
back and the run failed halfway through with a confusing error.

The ordering rules are documented at the top of the module. The order the
scheduler actually returns does not follow them.
