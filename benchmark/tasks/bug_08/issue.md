# Printed receipt total does not match the lines above it

Customers are pointing at the paper receipt: the numbers printed on the item
lines do not add up to the printed TOTAL. The total is always too small, and
the difference is exactly the last line on the receipt.

```
            RECEIPT
----------------------------------
apple                         1.50
2 x bread                     4.98
----------------------------------
TOTAL                         1.50
```

That receipt should total 6.48. The individual lines are printed correctly, so
the problem is in how the total is computed rather than in the layout.
