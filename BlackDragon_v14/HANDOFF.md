# BlackDragon v15.03 / T17.26 — current handoff

Source fix for 20260906 tester-stop incident, explicitly approved by owner. Read `docs/vibecode/T17_26_protective_sl/HANDOVER.md` and `NATIVE_RUNBOOK.md`.

60 host regression/source groups, 364 production assertions (132 new), 14 mutation cases and 13 UBSan/bounds fixtures are enrolled. Delivery `verification/HOST_GATE_RESULTS.json` is the authority for executed outcomes. 35 native scripts enrolled but not run here; no EX5 included. Native compile/test/restart/profile remain pending; release/forward/live/merge=false.

All EA input values/types/order/defaults preserved. TesterStop remains for actual unknown/reconcile state. Atomic ledger writer upgrades to version 2 with version-1 loader; protect state backups and use an isolated tester terminal.
