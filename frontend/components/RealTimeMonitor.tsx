
import React, { useState } from 'react';
import { api } from '../services/api';
import { COLORS } from '../constants';
import { CallMetric } from '../types';

const AudioVisualizer = ({ active, color = COLORS.secondary }: { active: boolean, color?: string }) => (
  <div className="flex items-end gap-[1px] h-3 px-1">
    {[...Array(6)].map((_, i) => (
      <div
        key={i}
        className="w-[1px] rounded-full transition-all duration-300"
        style={{
          backgroundColor: color,
          height: active ? `${30 + Math.random() * 70}%` : '2px',
          animation: active ? `wave ${0.4 + Math.random()}s ease-in-out infinite` : 'none',
          animationDelay: `${i * 0.1}s`
        }}
      ></div>
    ))}
  </div>
);

const RealTimeMonitor: React.FC = () => {
  const [activeCalls, setActiveCalls] = useState<CallMetric[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  React.useEffect(() => {
    const fetchActive = async () => {
      try {
        const calls = await api.getActiveCalls();
        setActiveCalls(calls);
        setLastUpdated(new Date());
      } catch (e) {
        console.error(e);
      }
    };

    fetchActive();
    const interval = setInterval(fetchActive, 3000); // Poll every 3 seconds for more real-time updates
    return () => clearInterval(interval);
  }, []);
  const [monitoringId, setMonitoringId] = useState<string | null>(null);
  const [overridingId, setOverridingId] = useState<string | null>(null);

  // Calculate live duration for active calls
  const getLiveDuration = (timestamp: string) => {
    const start = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-500 pb-20 lg:pb-0">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold font-display text-white tracking-tight">Live Ops</h2>
        <div className="flex items-center gap-3">
          <span className="text-[8px] text-slate-500 font-mono">
            Updated: {lastUpdated.toLocaleTimeString()}
          </span>
          <div className="flex items-center gap-2 px-3 py-1 bg-slate-900/50 border border-white/5 rounded-lg">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">{activeCalls.length} Active</span>
          </div>
        </div>
      </div>

      {activeCalls.length === 0 ? (
        <div className="glass p-12 rounded-2xl border border-white/5 flex flex-col items-center justify-center text-center space-y-4">
          <div className="w-16 h-16 bg-slate-900/80 rounded-2xl flex items-center justify-center border border-white/5">
            <svg className="w-8 h-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white mb-1">No Active Calls</h3>
            <p className="text-[10px] text-slate-500 max-w-xs">
              When calls come in, they will appear here in real-time. The monitor refreshes every 3 seconds.
            </p>
          </div>
          <div className="flex items-center gap-2 text-[8px] text-slate-600">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-50"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            <span className="uppercase tracking-widest font-bold">Listening for incoming calls...</span>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeCalls.map((call) => {
            const isMonitoring = monitoringId === call.id;
            const isOverriding = overridingId === call.id;

            return (
              <div
                key={call.id}
                className={`glass p-4 rounded-2xl border-t-2 transition-all duration-300 relative overflow-hidden ${isMonitoring ? 'border-t-emerald-500' : isOverriding ? 'border-t-rose-500' : 'border-t-cyan-500'
                  }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border transition-colors ${isOverriding ? 'bg-rose-500/20 border-rose-500/30 text-rose-400' : 'bg-slate-950 border-white/5 text-slate-500'
                      }`}>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white leading-tight">{call.caller}</h4>
                      <span className="text-[8px] font-black text-slate-500 uppercase tracking-widest">{isOverriding ? 'Override' : call.language || 'en-US'}</span>
                    </div>
                  </div>
                  <div className="text-[10px] font-mono text-violet-400 font-bold">{getLiveDuration(call.timestamp)}</div>
                </div>

                <div className="bg-black/20 rounded-xl p-3 border border-white/5 mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Neural Stream</span>
                    <AudioVisualizer active={true} color={isOverriding ? COLORS.danger : isMonitoring ? COLORS.success : COLORS.secondary} />
                  </div>
                  <p className="text-[10px] text-slate-400 italic line-clamp-1">
                    {call.transcript && call.transcript.length > 0
                      ? `"${call.transcript[call.transcript.length - 1].text}"`
                      : "Listening for input..."}
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setMonitoringId(isMonitoring ? null : call.id)}
                    className={`flex-1 group py-2 rounded-lg border transition-all ${isMonitoring ? 'bg-emerald-500 border-emerald-400' : 'bg-white/5 border-white/5 hover:bg-white/10'
                      }`}
                  >
                    <div className={`text-[9px] font-black uppercase tracking-tighter ${isMonitoring ? 'text-white' : 'text-slate-300'}`}>Monitor</div>
                    <div className={`text-[7px] font-bold uppercase opacity-60 ${isMonitoring ? 'text-white' : 'text-slate-500'}`}>Listen Only</div>
                  </button>
                  <button
                    onClick={() => setOverridingId(isOverriding ? null : call.id)}
                    className={`flex-1 group py-2 rounded-lg border transition-all ${isOverriding ? 'bg-rose-600 border-rose-500' : 'bg-white/5 border-white/5 hover:bg-white/10'
                      }`}
                  >
                    <div className={`text-[9px] font-black uppercase tracking-tighter ${isOverriding ? 'text-white' : 'text-slate-300'}`}>Control</div>
                    <div className={`text-[7px] font-bold uppercase opacity-60 ${isOverriding ? 'text-white' : 'text-slate-500'}`}>Barge-In</div>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default RealTimeMonitor;
