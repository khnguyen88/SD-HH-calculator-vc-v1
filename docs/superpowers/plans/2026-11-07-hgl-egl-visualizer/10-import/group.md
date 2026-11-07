# Group 10: Import — data ingress from .json and .xlsx

**Purpose:** Accept imported data in either format, normalize into the in-memory shape, and auto-layout structures if coordinates are missing.

**Tasks:**
- `task-04-json-schema-validator.md` — validate the imported JSON matches schemaVersion 1
- `task-05-json-importer.md` — load a .json file into `state.imported`
- `task-06-xlsx-importer-sheets.md` — parse the main app's .xlsx export (4 sheets) into `state.imported`
- `task-07-autolayout-no-coords.md` — layered-graph auto-layout for structures lacking x/y

**Group acceptance criteria:**
- Drag-dropping or file-selecting a valid JSON populates `state.imported` with structures, pipes, outfall, config, kbTable.
- Drag-dropping or file-selecting the fixture `.xlsx` (from task-35) populates the same shape.
- An import missing all `x/y` coordinates on structures renders successfully (auto-layout assigns positions).
- A malformed import (missing `schemaVersion`, wrong `sourceApp`, negative lengths) is rejected with a specific error message in the toolbar; no `state.imported` mutation.

**Spec references:** §2.1 (input formats), §2.2 (in-memory shape), §2.3 (auto-layout), §B.1 (sheet names).
