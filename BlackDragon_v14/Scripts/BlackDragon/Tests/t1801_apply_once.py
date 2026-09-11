#!/usr/bin/env python3
"""One-shot T18.01 ExecutionLayer patcher.

This bootstrap mutates source only. Workflow finalization is intentionally
performed later by the GitHub connector because GitHub Actions tokens cannot
push workflow-file changes without workflows permission.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXEC = ROOT / "BlackDragon_v14/Include/BlackDragon/ExecutionLayer.mqh"
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

# Do not let the earlier provenance step leak a generated file into the source
# commit when the workflow uses `git add -A`.
prov = ROOT / "build-current-model/PROVENANCE.txt"
if prov.exists():
    prov.unlink()
SELF.unlink()
print("T18.01 one-shot source patch applied: CloseAllAccount cushion-order; patcher removed")
