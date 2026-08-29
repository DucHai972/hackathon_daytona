# API limit can be doubled by timing requests around the minute mark

A customer on the 2-requests-per-60-seconds plan pushed four requests through
in about two seconds and none of them were rejected:

```
12:00:59.1  POST /v1/jobs   202
12:00:59.4  POST /v1/jobs   202
12:01:01.2  POST /v1/jobs   202   <- should have been 429
12:01:01.6  POST /v1/jobs   202   <- should have been 429
```

They are staying under the cap on paper but doing double the work in practice,
and support has seen the same pattern from three other accounts. Whatever
window the limiter is keeping does not seem to line up with the last 60
seconds of actual traffic.
