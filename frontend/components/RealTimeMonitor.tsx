
import React, { useState } from 'react';
import { api } from '../services/api';
import { COLORS } from '../constants';
import { CallMetric } from '../types';
import { getWebSocket } from '../services/websocket';

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

    // Poll every 3 seconds as fallback
    const interval = setInterval(fetchActive, 3000);

    // Also listen to WebSocket for real-time updates
    const ws = getWebSocket();

    const handleCallUpdate = (data: any) => {
      console.log('Call update received:', data);
      fetchActive(); // Refresh when changes detected
    };

    ws.on('call_started', handleCallUpdate);
    ws.on('call_updated', handleCallUpdate);
    ws.on('call_ended', handleCallUpdate);

    return () => {
      clearInterval(interval);
      ws.off('call_started', handleCallUpdate);
      ws.off('call_updated', handleCallUpdate);
      ws.off('call_ended', handleCallUpdate);
    };
  }, []);

  const [monitoringId, setMonitoringId] = useState<string | null>(null);
  const [overridingId, setOverridingId] = useState<string | null>(null);

  const getLiveDuration = (timestamp: string) => {
    const start = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', paddingTop: '24px' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#0F172A', marginBottom: '4px', fontFamily: 'Inter, system-ui, sans-serif' }}>
            Live Queue
          </h2>
          <p style={{ fontSize: '14px', color: '#94A3B8' }}>
            Monitor active calls in real-time
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '12px', color: '#94A3B8' }}>
            Updated: {lastUpdated.toLocaleTimeString()}
          </span>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 14px', backgroundColor: '#F1F5F9', borderRadius: '8px',
          }}>
            <span style={{
              width: '8px', height: '8px', borderRadius: '50%',
              backgroundColor: '#10B981', display: 'inline-block',
            }} />
            <span style={{ fontSize: '13px', fontWeight: '600', color: '#0F172A' }}>
              {activeCalls.length} Active
            </span>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 14px', backgroundColor: '#FFF7ED', borderRadius: '8px',
          }}>
            <span style={{ fontSize: '13px', fontWeight: '600', color: COLORS.primary }}>
              WebSocket Connected
            </span>
          </div>
        </div>
      </div>

      {activeCalls.length === 0 ? (
        <div style={{
          backgroundColor: '#FFFFFF', borderRadius: '16px', padding: '64px',
          textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }}>
          <div style={{
            width: '64px', height: '64px', borderRadius: '16px', backgroundColor: '#F1F5F9',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
          }}>
            <svg width="28" height="28" fill="none" stroke="#94A3B8" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
          </div>
          <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#0F172A', marginBottom: '8px' }}>No Active Calls</h3>
          <p style={{ fontSize: '14px', color: '#94A3B8', maxWidth: '320px', margin: '0 auto 16px' }}>
            When calls come in, they will appear here in real-time. The monitor refreshes every 3 seconds.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#06B6D4', display: 'inline-block', animation: 'pulse 2s infinite' }} />
            <span style={{ fontSize: '12px', fontWeight: '600', color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Listening for incoming calls...</span>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          {activeCalls.map((call) => {
            const isMonitoring = monitoringId === call.id;
            const isOverriding = overridingId === call.id;

            return (
              <div key={call.id} style={{
                backgroundColor: '#FFFFFF', borderRadius: '16px', padding: '20px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                borderTop: `3px solid ${isOverriding ? '#EF4444' : isMonitoring ? '#10B981' : '#06B6D4'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      width: '36px', height: '36px', borderRadius: '10px',
                      backgroundColor: '#F1F5F9', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <svg width="18" height="18" fill="none" stroke="#64748B" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#0F172A' }}>{call.caller}</h4>
                      <span style={{ fontSize: '11px', fontWeight: '500', color: '#94A3B8', textTransform: 'uppercase' }}>{call.language || 'en-US'}</span>
                    </div>
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: '600', color: COLORS.primary, fontFamily: 'monospace' }}>{getLiveDuration(call.timestamp)}</span>
                </div>

                <div style={{
                  backgroundColor: '#F8FAFC', borderRadius: '10px', padding: '12px', marginBottom: '16px',
                  border: '1px solid #E2E8F0',
                }}>
                  <span style={{ fontSize: '11px', fontWeight: '600', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Live Stream</span>
                  <p style={{ fontSize: '13px', color: '#64748B', fontStyle: 'italic' }}>
                    {call.transcript && call.transcript.length > 0
                      ? `"${call.transcript[call.transcript.length - 1].text}"`
                      : "Listening for input..."}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setMonitoringId(isMonitoring ? null : call.id)}
                    style={{
                      flex: 1, padding: '8px', borderRadius: '8px', border: '1px solid #E2E8F0',
                      backgroundColor: isMonitoring ? '#10B981' : '#FFFFFF',
                      color: isMonitoring ? '#FFFFFF' : '#64748B',
                      fontWeight: '600', fontSize: '12px', cursor: 'pointer', transition: 'all 0.2s',
                    }}
                  >
                    Monitor
                  </button>
                  <button
                    onClick={() => setOverridingId(isOverriding ? null : call.id)}
                    style={{
                      flex: 1, padding: '8px', borderRadius: '8px', border: '1px solid #E2E8F0',
                      backgroundColor: isOverriding ? '#EF4444' : '#FFFFFF',
                      color: isOverriding ? '#FFFFFF' : '#64748B',
                      fontWeight: '600', fontSize: '12px', cursor: 'pointer', transition: 'all 0.2s',
                    }}
                  >
                    Control
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
