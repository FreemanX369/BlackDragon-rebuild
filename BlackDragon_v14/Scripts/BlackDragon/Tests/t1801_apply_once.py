#!/usr/bin/env python3
"""One-shot T18.01 patcher executed by the canonical workflow.

It applies the large ExecutionLayer CloseAllAccount replacement in-place, then
finalizes verify-current.yml back to read-only canonical CI and deletes itself.
Every mutation is exact-match guarded; ambiguity fails closed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXEC = ROOT / "BlackDragon_v14/Include/BlackDragon/ExecutionLayer.mqh"
WF = ROOT / ".github/workflows/verify-current.yml"
SELF = Path(__file__).resolve()

old_close = '''   int CloseAllAccount()
   {
      int sent = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong tic = PositionGetTicket(i);
         if(tic != 0 && ClosePositionEx(tic)) sent++;
      }
      if(sent > 0) Log_Info("Exec", "CloseAllAccount: " + (string)sent + " close request(s) sent (all symbols/magics)");
      return sent;
   }
'''

new_close = '''   int CloseAllAccount()
   {
      // T18.01: snapshot account positions before any mutation, then realize
      // the strongest current cash cushion first. This does not reduce close
      // urgency or scope: every snapshotted ticket is still submitted through
      // the existing ClosePositionEx/ExecutionLayer primitive in this call.
      int total = PositionsTotal();
      if(total <= 0) return 0;

      ulong tickets[];
      double cushions[];
      ArrayResize(tickets, total);
      ArrayResize(cushions, total);
      int count = 0;
      for(int i = total - 1; i >= 0; i--)
      {
         ulong tic = PositionGetTicket(i);
         if(tic == 0) continue;
         tickets[count] = tic;
         cushions[count] = PositionGetDouble(POSITION_PROFIT) +
                           PositionGetDouble(POSITION_SWAP);
         count++;
      }
      ArrayResize(tickets, count);
      ArrayResize(cushions, count);

      // Stable insertion sort: descending cash cushion, then ascending ticket.
      // The pure comparator also puts non-finite observations last.
      for(int i = 1; i < count; i++)
      {
         ulong keyTicket = tickets[i];
         double keyCushion = cushions[i];
         int j = i - 1;
         while(j >= 0 &&
               Recovery_AccountFlattenBeforePure(keyCushion, keyTicket,
                                                 cushions[j], tickets[j]))
         {
            tickets[j + 1] = tickets[j];
            cushions[j + 1] = cushions[j];
            j--;
         }
         tickets[j + 1] = keyTicket;
         cushions[j + 1] = keyCushion;
      }

      int sent = 0;
      for(int i = 0; i < count; i++)
         if(tickets[i] != 0 && ClosePositionEx(tickets[i])) sent++;

      if(sent > 0)
         Log_Info("Exec", "CloseAllAccount: " + (string)sent +
                  " close request(s) sent cushion-ordered (all symbols/magics)");
      return sent;
   }
'''

src = EXEC.read_text(encoding="utf-8")
if src.count(old_close) != 1:
    raise SystemExit(f"CloseAllAccount authority mismatch: expected exactly 1 old block, got {src.count(old_close)}")
EXEC.write_text(src.replace(old_close, new_close), encoding="utf-8")

wf = WF.read_text(encoding="utf-8")
if "contents: write # T1801_ONE_SHOT" not in wf:
    raise SystemExit("temporary write permission marker missing")
wf = wf.replace("contents: write # T1801_ONE_SHOT", "contents: read", 1)

begin = "      # T1801_ONE_SHOT_BEGIN\n"
end = "      # T1801_ONE_SHOT_END\n"
if wf.count(begin) != 1 or wf.count(end) != 1:
    raise SystemExit("one-shot workflow markers missing or duplicated")
a = wf.index(begin)
b = wf.index(end, a) + len(end)
wf = wf[:a] + wf[b:]

anchor = '          python3 "BlackDragon_v14/Scripts/BlackDragon/Tests/t18_fluid_source_contract.py" | tee "build-current-model/t18-fluid-source.log"\n'
extra = (
    '          python3 "BlackDragon_v14/Scripts/BlackDragon/Tests/t1801_hardening_model.py" | tee "build-current-model/t1801-hardening.log"\n'
    '          python3 "BlackDragon_v14/Scripts/BlackDragon/Tests/t1801_ab_matrix.py" --self-test | tee "build-current-model/t1801-ab.log"\n'
)
if wf.count(anchor) != 1:
    raise SystemExit("T18 source-contract anchor missing or duplicated")
if "t1801_hardening_model.py" not in wf:
    wf = wf.replace(anchor, anchor + extra, 1)

old_native = r"@{N='RunRecoveryIdentityTests';P='Recovery T14 identity tests:\s*(\d+) passed,\s*(\d+) failed';E=17}"
new_native = r"@{N='RunRecoveryIdentityTests';P='Recovery T14/T18\.01 identity tests:\s*(\d+) passed,\s*(\d+) failed';E=24}"
if old_native not in wf:
    raise SystemExit("native identity expectation authority missing")
wf = wf.replace(old_native, new_native, 1)

WF.write_text(wf, encoding="utf-8")
SELF.unlink()
print("T18.01 one-shot patch applied: CloseAllAccount cushion-order; canonical workflow finalized; patcher removed")
