# T17.26 incident-fix source import — 2026-09-08

## Package and scope
This branch imports the 419 tracked files from BD-T1726-Incident-Fix-Source.zip, the latest fixed source package delivered in this conversation. It is v15.03 / T17.26 with the September 8 tester-stop fix; it is not the separately discussed v15.04 / T17.27 candidate.

Source ZIP SHA-256: 745e5fd1aabdc09b0285fbafbd79772846e053c74243cca5d3e5fa0f961e5314
Local source commit: 02894b9e35729a95227d91bf182956bbbc861958
Original T17.26 upstream reference: 209dcdfb64bd18f454127cc21497c099f542452e

Read START_HERE.md first. Active verification records are in BlackDragon_v14/docs/vibecode/T1726_INCIDENT_20260908/. Production entry point: BlackDragon_v14/Experts/BlackDragon/BlackDragon.mq5.

## Problem and fix
The incident log stopped during recovery reconciliation after a partial close and broker SL. The protective proof could miss a current-second deal when selecting history through TimeCurrent(), making recovery not ready and stopping the tester.

- RecoveryArcsStackHardened.mqh expands the protective-repair history selection to TimeCurrent()+1 and adds bounded mismatch diagnostics. Ownership, proof equality, cash accounting and schema remain unchanged.
- RecoveryDca.mqh records the first tester-stop request and suppresses repeated stop requests.
- RecoveryDcaT1713.mqh records that recovery previously reached ready, preventing a later runtime failure from being labeled initialization failure.
- Regression tests, a native history-boundary probe and governance records accompany the source.
- All 150 inputs and defaults are unchanged. The version banner remains v15.03 / T17.26; hashes identify this patch.

## Existing verification evidence
These results were collected before this repository import; this upload is not a new compile or tester run.

| Check | Result |
| --- | --- |
| Host production-method integration | 222/222 PASS, UBSan/bounds enabled |
| Source-contract checks | 234 PASS |
| Mutation reverting the history horizon | 27 checks fail, mutation killed |
| Native isolated history probe | Old range missed 7/8 callbacks; expanded range found 8/8 |
| Full EA native compile | 0 errors, 0 warnings |
| Tester job | BT-20260908-083024-AAB184 |
| Instrument / period | XAUUSDm / M1 |
| Requested interval | 2026.08.26–2026.09.08 |
| Last tick | 2026.09.07 23:59:58 |
| Model / delay | Real ticks, model 4 / fixed 150 ms |
| Deposit / leverage | USD 10,000 / 1:1000 |
| Input matching | 150/150 |
| Completion | No TesterStop, stopout, protective mismatch, reconcile-required or runtime error |
| Net profit / final balance | USD 15,035.13 / USD 25,035.13 |
| Profit factor / maximum drawdown | 1.28 / 19.94% |
| Trades / deals | 2,095 / 4,082 |
| Ticks / bars | 2,744,200 / 12,249 |

## Limits and residual observations
One nonfatal broker rejection 10016 appeared twice in the log for the same modification. State was retained and the position later closed by market; successful SL retry is not established.
PY-to-RH trim counter was zero, so targeted trim acceptance is not established.
The replay used a different broker server and terminal build from the incident, so exact original-tape parity remains unverified.
Historical documentation and workflow branch references are preserved as supplied; this import does not assert a new GitHub Actions run.
The archive's extra raw BUILD-RECEIPT.json and native evidence logs are not published here because they contain runtime/account metadata. Sanitized verification records are included.

## Binary provenance
The prior native build produced 776,882 bytes.
EX5 SHA-256: 7d81a3434854de5d95886a2ed2b8904deb0f0b1aeaacc5225381bf32dd0286c3
Flattened source SHA-256: de82f54447645c44bd8b7bb5e0b8c8207ca36c509a3a846564ed83cd5328ae36

The binary remains on the tester host; this source import does not include an EX5 download. The PR is a draft and has not been merged.
