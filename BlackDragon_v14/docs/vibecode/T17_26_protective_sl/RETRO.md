# T17.26 retro

Defect 1: two ownership classifiers disagree when a valid own SL has a large fill gap. Fixed by shared immutable proof; current spread no longer defines ownership.

Defect 2: the accounting cursor was also used to exclude topology proof. A newer callback could hide an older unconsumed SL. Six production-router/refresh permutations now lock the receipt-based rule.

Defect 3: protective refresh could retire geometry before journaling actual cash/proof. Both now commit atomically; partial receipt failures block persistence. Fresh GetLayer prevents an old local layer copy from overwriting newly settled cash.

Verification deliberately caught reverse-callback failure before handover. The initial new fixture had 67 passing checks yet did not expose that ordering; expanded composition coverage did. Do not infer native acceptance from passing pure or host tests.

The 3 new mutants restore fill-distance rejection, drop protective proof, or reintroduce cursor exclusion. All must be killed by behavior assertions, not compilation failure. Existing 11 mutations remain enrolled.

Single-agent role separation was sequential, not an independent human audit. Canonical vkmql-check/mql5-retro-init tools and native backend were unavailable; full runtime retro guard acceptance remains UNTESTABLE. No universal skill files changed, no benchmark claim, no strategy/default changes, no live eligibility.
