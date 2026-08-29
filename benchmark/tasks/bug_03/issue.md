# Backup job fails whenever a path contains a space

The scheduler stores each job as a single command line and splits it before
running it. Any customer whose destination directory has a space in it gets a
broken run:

```
job:  pg_dump --out "/var/My Backups/db.sql"
argv: ['pg_dump', '--out', '"/var/My', 'Backups/db.sql"']
```

The quotes are being passed through as literal characters and the path is torn
in half. It also swallows an obviously malformed command instead of complaining
about it — `echo "oops` runs happily with a stray quote in the argument.

The splitting rules we need are written at the top of the module; the code
underneath does not implement them.
