# Corrupt profile silently boots the account on the free plan

A paying customer was downgraded to the free plan for six hours. Their profile
record on disk had been truncated by a bad deploy, and instead of failing the
request the service quietly handed out the default profile. Nobody was paged
because nothing errored.

```python
open("profile.json", "w").write('{"plan": "pro"')   # truncated
load_profile("profile.json")
# -> {'plan': 'free'}   no exception, no log line
```

A profile that is genuinely absent should still fall back to the default — new
signups depend on that. A profile that exists but cannot be read is a different
situation and has to surface as a `CorruptRecord`, all the way out to the
caller.
