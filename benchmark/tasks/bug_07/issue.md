# Multi-unit orders with a promotion are undercharged

Finance reconciled a day of orders against the pricing spec and found every
discounted order for more than one unit is a cent or two light, always in the
customer's favour.

```
7 x milk @ 0.99 with SUMMER20 (20% off)
charged 5.53, spec says 5.54
```

Single-unit orders reconcile exactly, and orders with no promotion reconcile
exactly, so it only shows up once a promotion meets a quantity above one.

The pricing rules are written at the top of `promotions.py`. Whatever the code
is doing does not match them.
