# Cart total does not change after adding an item

The checkout page reads `Cart.total()` before and after the customer adds an
item to the basket. The second read still shows the old amount, so customers
see a total that is missing whatever they just added.

```python
cart = Cart()
cart.add("apple", 150)
print(cart.total())   # 150
cart.add("bread", 249)
print(cart.total())   # 150  <- expected 399
```

Reloading the page fixes it, which points at the memoised total rather than at
the arithmetic. Removing an item looks like it has the same problem.
