# Group 30: Data Consistency

One task: fix the TR-55 detail calc sheet (opened via "⤢ Detail" on a TR-55 drainage-area row)
to show substituted formula values, matching every other detail sheet in the app.

## Acceptance

Opening a TR-55 drainage-area detail sheet shows e.g.:
```
Tt = 0.007(0.24 × 100)^0.8 / (3.6^0.5 × 0.02^0.4) = 0.1234 hr
```
Not the bare template `Tt = 0.007(nL)^0.8 / (P2^0.5 × s^0.4)`.
