//+------------------------------------------------------------------+
//| FluidRegimeEngine.mqh — T18.00 tick-fluid regime engine          |
//| Reduced-order market-state model; no PDE/CFD solver, no orders.   |
//| Inputs: native MT5 MqlTick price/time/tick-volume only.           |
//+------------------------------------------------------------------+
#ifndef BD_FLUID_REGIME_ENGINE_MQH
#define BD_FLUID_REGIME_ENGINE_MQH

#include "../Config.mqh"
#include "../Types.mqh"

input group "=== T18 Fluid Regime (tick-native) ==="
input bool   UseFluidRegime          = false;
input int    FluidMode               = 0;      // 0=SHADOW,1=DCA,2=DCA+PY,3=DCA+PY+RH child
input int    FluidFastWindow         = 16;
input int    FluidSlowWindow         = 96;
input double FluidReThreshold        = 2.00;   // heuristic transport/diffusion ratio
input double FluidCriticalThreshold  = 2.50;   // local concentration / quadratic stress

struct SFluidRegimeState
{
   bool   initialized;
   int    samples;
   double prevMid;
   double prevResidual;
   double volumeSlow;
   double velocity;
   double diffusion;
   double absFast;
   double absSlow;
   double energyFast;
   double energySlow;
   double marketRe;
   double concentration;
   double stress;
   double criticality;
   double confidence;
   int    direction;       // -1 down, 0 neutral, +1 up
   ulong  tickMsc;
   datetime lastLog;
};

SFluidRegimeState g_fluid;

int Fluid_FastWindow()
{
   return MathMax(2, FluidFastWindow);
}

int Fluid_SlowWindow()
{
   return MathMax(Fluid_FastWindow() + 1, FluidSlowWindow);
}

double Fluid_Clamp(const double v, const double lo, const double hi)
{
   return MathMax(lo, MathMin(hi, v));
}

double Fluid_Ema(const double previous, const double value, const int window)
{
   double alpha = 2.0 / ((double)MathMax(window, 1) + 1.0);
   return previous + alpha * (value - previous);
}

double Fluid_TickVolume(const MqlTick &tick)
{
   if(tick.volume_real > 0.0) return tick.volume_real;
   if(tick.volume > 0) return (double)tick.volume;
   // OTC symbols can expose no exchange trade volume on quote ticks.
   // One quote event is the deterministic last-resort tick-volume unit.
   return 1.0;
}

bool Fluid_Ready()
{
   return UseFluidRegime && g_fluid.initialized &&
          g_fluid.samples >= Fluid_SlowWindow();
}

string Fluid_StateText()
{
   if(!UseFluidRegime) return "OFF";
   if(!Fluid_Ready())
      return "WARMUP " + (string)g_fluid.samples + "/" + (string)Fluid_SlowWindow();
   string d = g_fluid.direction > 0 ? "UP" : g_fluid.direction < 0 ? "DOWN" : "NEUTRAL";
   return "dir=" + d +
          " ReM=" + DoubleToString(g_fluid.marketRe, 3) +
          " C=" + DoubleToString(g_fluid.concentration, 3) +
          " S=" + DoubleToString(g_fluid.stress, 3) +
          " crit=" + DoubleToString(g_fluid.criticality, 3) +
          " conf=" + DoubleToString(g_fluid.confidence, 3);
}

void Fluid_UpdateCurrentTick()
{
   if(!UseFluidRegime) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;
   if(tick.bid <= 0.0 || tick.ask <= 0.0 || tick.ask < tick.bid) return;

   double mid = 0.5 * (tick.bid + tick.ask);
   double rawVol = Fluid_TickVolume(tick);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0) point = _Point;
   if(point <= 0.0) return;

   if(!g_fluid.initialized)
   {
      g_fluid.initialized = true;
      g_fluid.samples = 1;
      g_fluid.prevMid = mid;
      g_fluid.prevResidual = 0.0;
      g_fluid.volumeSlow = rawVol;
      g_fluid.diffusion = 1.0;
      g_fluid.absFast = 0.0;
      g_fluid.absSlow = 0.0;
      g_fluid.energyFast = 0.0;
      g_fluid.energySlow = 0.0;
      g_fluid.marketRe = 0.0;
      g_fluid.concentration = 1.0;
      g_fluid.stress = 0.0;
      g_fluid.criticality = 1.0;
      g_fluid.confidence = 0.0;
      g_fluid.direction = 0;
      g_fluid.tickMsc = tick.time_msc;
      g_fluid.lastLog = 0;
      return;
   }

   const int fast = Fluid_FastWindow();
   const int slow = Fluid_SlowWindow();
   const double eps = 1e-9;
   double spread = MathMax(tick.ask - tick.bid, 0.0);
   double scale = MathMax(point, spread);
   double move = (mid - g_fluid.prevMid) / scale;

   g_fluid.volumeSlow = Fluid_Ema(g_fluid.volumeSlow, rawVol, slow);
   double volumeRelative = Fluid_Clamp(rawVol / MathMax(g_fluid.volumeSlow, eps), 0.25, 4.0);
   double impulse = move * volumeRelative;

   g_fluid.velocity = Fluid_Ema(g_fluid.velocity, impulse, fast);
   double residual = impulse - g_fluid.velocity;
   g_fluid.diffusion = Fluid_Ema(g_fluid.diffusion, MathAbs(residual), slow);
   g_fluid.absFast = Fluid_Ema(g_fluid.absFast, MathAbs(impulse), fast);
   g_fluid.absSlow = Fluid_Ema(g_fluid.absSlow, MathAbs(impulse), slow);

   double localEnergy = MathAbs(impulse) * volumeRelative;
   g_fluid.energyFast = Fluid_Ema(g_fluid.energyFast, localEnergy, fast);
   g_fluid.energySlow = Fluid_Ema(g_fluid.energySlow, localEnergy, slow);

   double lengthRatio = Fluid_Clamp(g_fluid.absFast / MathMax(g_fluid.absSlow, eps), 0.25, 4.0);
   g_fluid.marketRe = Fluid_Clamp(MathAbs(g_fluid.velocity) * lengthRatio /
                                  MathMax(g_fluid.diffusion, eps), 0.0, 100.0);
   g_fluid.concentration = Fluid_Clamp(g_fluid.energyFast /
                                       MathMax(g_fluid.energySlow, eps), 0.0, 10.0);
   double quadratic = MathAbs(residual * g_fluid.prevResidual);
   double stressRaw = quadratic /
                      MathMax(g_fluid.diffusion * g_fluid.diffusion, eps);
   g_fluid.stress = Fluid_Clamp(Fluid_Ema(g_fluid.stress, stressRaw, fast), 0.0, 10.0);
   g_fluid.criticality = MathMax(g_fluid.concentration, g_fluid.stress);
   g_fluid.confidence = Fluid_Clamp(MathAbs(g_fluid.velocity) /
                                    (MathAbs(g_fluid.velocity) + g_fluid.diffusion + eps),
                                    0.0, 1.0);

   double deadband = 0.35 * MathMax(g_fluid.diffusion, eps);
   g_fluid.direction = g_fluid.velocity > deadband ? 1 :
                       g_fluid.velocity < -deadband ? -1 : 0;

   g_fluid.prevMid = mid;
   g_fluid.prevResidual = residual;
   g_fluid.tickMsc = tick.time_msc;
   g_fluid.samples++;

   // Shadow/evidence heartbeat. Fixed cadence avoids another optimizer input.
   datetime now = TimeCurrent();
   if(FluidMode == 0 && Fluid_Ready() &&
      (g_fluid.lastLog == 0 || now - g_fluid.lastLog >= 60))
   {
      Print("Fluid SHADOW | ", Fluid_StateText());
      g_fluid.lastLog = now;
   }
}

bool Fluid_StrongTransport()
{
   return Fluid_Ready() && g_fluid.direction != 0 &&
          g_fluid.marketRe >= MathMax(FluidReThreshold, 0.0);
}

bool Fluid_DirectionAdverse(const int dir)
{
   if(g_fluid.direction == 0) return false;
   if(dir == BD_DIR_BUY) return g_fluid.direction < 0;
   if(dir == BD_DIR_SELL) return g_fluid.direction > 0;
   return false;
}

bool Fluid_AllowDca(const int coreDir)
{
   if(!UseFluidRegime || FluidMode < 1 || !Fluid_Ready()) return true;
   return !(Fluid_StrongTransport() && Fluid_DirectionAdverse(coreDir));
}

bool Fluid_AllowPyramid(const int dir)
{
   if(!UseFluidRegime || FluidMode < 2 || !Fluid_Ready()) return true;
   if(g_fluid.criticality >= MathMax(FluidCriticalThreshold, 0.0)) return false;
   return !(Fluid_StrongTransport() && Fluid_DirectionAdverse(dir));
}

bool Fluid_AllowRecoveryHedge(const int hedgeDir, const bool initialChild)
{
   // First RH child is protective legacy behavior and is never gated.
   if(initialChild) return true;
   if(!UseFluidRegime || FluidMode < 3 || !Fluid_Ready()) return true;
   return !(Fluid_StrongTransport() && Fluid_DirectionAdverse(hedgeDir));
}

bool Fluid_HasCoreExposure(const int dir)
{
   long wantedType = dir == BD_DIR_BUY ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_TYPE) != wantedType) continue;
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(magic == (long)Magic || (flag_Hand_Ord && magic == 0)) return true;
   }
   return false;
}

// Used by the new-series/Pyramid filter chain. A seed has no same-side Core
// exposure and therefore remains byte-for-behavior legacy; existing Core sides
// get the PY-only Fluid gate.
bool Fluid_AllowNewSeriesChain(const int dir)
{
   if(!Fluid_HasCoreExposure(dir)) return true;
   return Fluid_AllowPyramid(dir);
}

#endif // BD_FLUID_REGIME_ENGINE_MQH
