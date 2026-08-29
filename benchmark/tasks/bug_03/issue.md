# Config loader dies on any setting that contains an equals sign

Our deploy config is a flat `key = value` file. It has worked fine until
someone added a URL with a query string, and now every deploy fails before it
starts.

```
$ cat deploy.conf
region = eu-west-1
callback = https://example.com/hook?token=abc
```

```
  File "config.py", line 18, in parse_config
    key, value = line.split("=")
ValueError: too many values to unpack (expected 2)
```

Only the first equals sign separates the key from the value; everything after
it is part of the value. Comment lines and blank lines already work and should
keep working.
