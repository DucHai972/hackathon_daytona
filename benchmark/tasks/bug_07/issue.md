# Discounted orders are charged the wrong amount

Finance reconciled yesterday's orders and found discounted multi-unit orders
are off by a cent or two, always in the customer's favour.

```python
order_total_cents("milk", 3, percent=33)   # 3 x 99c, 33% off
# -> 198, finance expects 199
```

Two rules from the pricing spec that the reconciliation script checks:

* A discount applies to the **line total**, not to each unit separately.
* Money is rounded **half up** to the nearest cent, so 2.5c becomes 3c.

Undiscounted orders and the catalogue lookups are fine.
