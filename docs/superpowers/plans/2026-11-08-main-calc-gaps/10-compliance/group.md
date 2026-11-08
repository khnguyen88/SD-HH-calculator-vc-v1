# Group 10: Spec Compliance

One task: add the print-large-output confirmation warning that the spec (Phase 7) requires
before `printAllDetailSheets()` can run to 100+ pages.

## Acceptance

Clicking "Detail" (the Print All Detail button in the topbar) when `state.outletStructures`
has at least one facility with more than 200 stage rows shows a `window.confirm` prompt
naming the estimated page count. Clicking OK proceeds; Cancel aborts.
