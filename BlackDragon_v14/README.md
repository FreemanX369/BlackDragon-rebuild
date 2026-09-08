# BlackDragon v15.03 — T17.26 protective SL fix

Entry point: `Experts/BlackDragon/BlackDragon.mq5`. Installation folder name v14 is retained for path compatibility. This is one current EA. Source builds on upstream PR28 branch `feat/t17-full-pyramid` at `40c424cf`.

T17.25 baseline includes: durable operation outcomes/consumer ACK, atomic replay receipts/corrections, indexed PositionBook, incremental campaign history, bounded retention, local diagnostics and validation-only profit oracle. Inputs/defaults are preserved. Read the [handover](docs/vibecode/BD_PR28_REMEDIATION/HANDOVER.md), [implementation matrix](docs/vibecode/BD_PR28_REMEDIATION/IMPLEMENTATION_REPORT.md) and [native runbook](docs/vibecode/BD_PR28_REMEDIATION/NATIVE_BUILD_RUNBOOK.md).

T17.26 fixes broker SL identity, receipt-before-topology settlement and reversed callback order. Read the [current handover](docs/vibecode/T17_26_protective_sl/HANDOVER.md) and [native runbook](docs/vibecode/T17_26_protective_sl/NATIVE_RUNBOOK.md).

## Verification

60 host regression/source groups; 364 production-fixture assertions; 14 mutation cases; 13 UBSan/bounds fixtures. Exact execution outcomes are in the delivery manifest. Reproduce with:

```bash
python3 BlackDragon_v14/Scripts/BlackDragon/Tests/run_host_gates.py --out /absolute/new/output
```

Run that command from the directory containing BlackDragon_v14. Native MetaEditor compile and 35 scripts remain owner-pending. Full PRD native/benchmark acceptance is incomplete; release/forward/live/merge are false. No EX5 or native speedup claim accompanies this source handover.

## Source map

| Area | Purpose |
|---|---|
| Experts/BlackDragon | Single EA entry point |
| Include/BlackDragon | Runtime modules; old T17 Base names are reachable compatibility layers |
| Scripts/BlackDragon/Tests | 42 C++ models, 35 native scripts, production adapters and source/benchmark validators |
| Sets | Preserved input presets |
| docs/vibecode/T17_26_protective_sl | Current incident fix authority, handover and native runbook |
| docs/vibecode/BD_PR28_REMEDIATION | Prior T17.25 PRD implementation and evidence history |
| docs/vibecode/archive | Frozen historical governance |

Copy Experts, Include and Scripts into a separate terminal MQL5 folder, or use BuildCandidate.ps1. Preserve the state migration/rollback rules in the runbook. Dashboard remains removed; ShowWmfSignals arrows remain optional. Recovery WAIT_RESET/ARMED blocks Core DCA while Pyramid ADD follows settings; EXHAUSTED blocks risk additions and preserves risk-reducing exits.
