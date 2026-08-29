# Back-to-back room bookings render as two separate blocks

The calendar view collapses a room's reservations into solid blocks. When one
booking ends exactly as the next begins the view still draws two blocks with a
hairline gap, and the tooltip reports "2 bookings" where staff expect one
continuous occupancy.

```
09:00-11:00  meeting room 3
11:00-12:30  meeting room 3
```

Drawn as two blocks. Expected: one block, 09:00-12:30.

Overlapping bookings collapse correctly, so only the exactly-adjacent case
looks wrong. The reporting export builds on the same helper and shows the same
split, which is starting to skew the occupancy figures.
