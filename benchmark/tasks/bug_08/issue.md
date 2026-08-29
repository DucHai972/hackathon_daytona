# Printed receipt total does not match the lines above it

Customers are pointing at the paper receipt: the item lines do not add up to
the printed TOTAL. The total is always short by exactly the last line.

```
            RECEIPT
----------------------------------
apple                         1.50
2 x bread                     4.98
----------------------------------
TOTAL                         1.50
```

That receipt should total 6.48. The individual lines print correctly, so the
problem looks like it is in how the total is worked out rather than in the
layout.
