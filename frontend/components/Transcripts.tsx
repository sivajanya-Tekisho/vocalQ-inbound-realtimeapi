
import React, { useState } from 'react';
import { api } from '../services/api';
import { CallMetric } from '../types';
import { COLORS } from '../constants';
import { getWebSocket } from '../services/websocket';

const Transcripts: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCall, setSelectedCall] = useState<CallMetric | null>(null);
  const [calls, setCalls] = useState<CallMetric[]>([]);
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [customDate, setCustomDate] = useState<string>('');

  React.useEffect(() => {
    const loadCalls = () => {
      api.getCalls().then(data => {
        const sorted = [...data].sort((a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );
        setCalls(sorted);
      }).catch(console.error);
    };

    loadCalls();

    // Listen to WebSocket for real-time updates
    const ws = getWebSocket();
    const handleNewCall = () => {
      console.log('New call detected - refreshing list');
      loadCalls();
    };

    ws.on('call_started', handleNewCall);
    ws.on('call_ended', handleNewCall);

    return () => {
      ws.off('call_started', handleNewCall);
      ws.off('call_ended', handleNewCall);
    };
  }, []);

  React.useEffect(() => {
    if (selectedCall && !selectedCall.transcript) {
      api.getCallDetails(selectedCall.id).then(details => {
        if (details) setSelectedCall(details);
      });
    }
  }, [selectedCall?.id]);

  const filterByDate = (call: CallMetric) => {
    if (dateFilter === 'all') return true;
    const callDate = new Date(call.timestamp);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (dateFilter === 'today') {
      const callDay = new Date(callDate); callDay.setHours(0, 0, 0, 0);
      return callDay.getTime() === today.getTime();
    }
    if (dateFilter === 'yesterday') {
      const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
      const callDay = new Date(callDate); callDay.setHours(0, 0, 0, 0);
      return callDay.getTime() === yesterday.getTime();
    }
    if (dateFilter === 'week') {
      const weekAgo = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7);
      return callDate >= weekAgo;
    }
    if (dateFilter === 'month') {
      const monthAgo = new Date(today); monthAgo.setMonth(monthAgo.getMonth() - 1);
      return callDate >= monthAgo;
    }
    if (dateFilter === 'custom' && customDate) {
      const selectedDate = new Date(customDate); selectedDate.setHours(0, 0, 0, 0);
      const callDay = new Date(callDate); callDay.setHours(0, 0, 0, 0);
      return callDay.getTime() === selectedDate.getTime();
    }
    return true;
  };

  const formatIndianTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-IN', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: true
    });
  };

  const filteredCalls = calls.filter(call =>
    filterByDate(call) && (
      (call.caller && call.caller.includes(searchTerm)) ||
      (call.intent && call.intent.toLowerCase().includes(searchTerm.toLowerCase()))
    )
  );

  const ConversationView = ({ call }: { call: CallMetric }) => (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px', borderBottom: '1px solid #E2E8F0',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        backgroundColor: '#FFFFFF', position: 'sticky', top: 0, zIndex: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={() => setSelectedCall(null)}
            style={{
              padding: '8px', borderRadius: '8px', backgroundColor: '#F1F5F9',
              border: 'none', cursor: 'pointer', color: '#64748B',
            }}
          >
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '700', color: '#0F172A' }}>{call.caller}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <span style={{ fontSize: '12px', color: '#94A3B8', fontWeight: '500' }}>{formatIndianTime(call.timestamp)} IST</span>
              <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: '#CBD5E1', display: 'inline-block' }} />
              <span style={{ fontSize: '12px', color: COLORS.primary, fontWeight: '600', textTransform: 'uppercase' }}>{call.intent}</span>
              <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: '#CBD5E1', display: 'inline-block' }} />
              <span style={{ fontSize: '12px', color: '#10B981', fontWeight: '600' }}>{call.token_usage || 0} tokens</span>
            </div>
          </div>
        </div>
        <span style={{
          padding: '4px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: '600',
          backgroundColor: call.sentiment === 'positive' ? '#ECFDF5' : call.sentiment === 'negative' ? '#FEF2F2' : '#F1F5F9',
          color: call.sentiment === 'positive' ? '#10B981' : call.sentiment === 'negative' ? '#EF4444' : '#64748B',
          textTransform: 'capitalize',
        }}>
          {call.sentiment}
        </span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}>
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
          {/* Summary */}
          <div style={{
            padding: '20px', borderRadius: '12px', marginBottom: '32px',
            backgroundColor: '#FFF7ED', border: '1px solid #FFEDD5',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <div style={{
                width: '24px', height: '24px', borderRadius: '6px', backgroundColor: COLORS.primary,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <svg width="14" height="14" fill="none" stroke="white" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span style={{ fontSize: '12px', fontWeight: '700', color: COLORS.primary, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Call Summary</span>
            </div>
            <p style={{ fontSize: '14px', color: '#92400E', lineHeight: '1.6' }}>"{call.summary || 'Summary processing...'}"</p>
          </div>

          {/* Chat Bubbles */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {call.transcript && call.transcript.length > 0 ? (
              call.transcript.map((part, idx) => (
                <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: part.speaker === 'ai' ? 'flex-start' : 'flex-end' }}>
                  <div style={{
                    maxWidth: '80%', padding: '14px 18px', borderRadius: '14px',
                    backgroundColor: part.speaker === 'ai' ? '#F1F5F9' : COLORS.primary,
                    color: part.speaker === 'ai' ? '#0F172A' : '#FFFFFF',
                    borderTopLeftRadius: part.speaker === 'ai' ? '4px' : '14px',
                    borderTopRightRadius: part.speaker === 'ai' ? '14px' : '4px',
                  }}>
                    <p style={{ fontSize: '14px', lineHeight: '1.6', margin: 0 }}>{part.text}</p>
                    <div style={{
                      marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px',
                      opacity: 0.6, justifyContent: part.speaker === 'ai' ? 'flex-start' : 'flex-end',
                    }}>
                      <span style={{ fontSize: '10px', fontWeight: '600', textTransform: 'uppercase' }}>
                        {part.speaker === 'ai' ? 'VocalQ AI' : 'Customer'}
                      </span>
                      <span style={{ fontSize: '10px', fontFamily: 'monospace' }}>
                        {new Date(part.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <p style={{ color: '#94A3B8', fontSize: '14px' }}>No transcript available for this record.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '16px 24px', borderTop: '1px solid #E2E8F0',
        backgroundColor: '#FFFFFF', display: 'flex', gap: '12px', justifyContent: 'center',
      }}>
        <button style={{
          padding: '10px 24px', backgroundColor: '#F1F5F9', border: '1px solid #E2E8F0',
          borderRadius: '8px', color: '#64748B', fontWeight: '600', fontSize: '13px', cursor: 'pointer',
        }}>Export Transcript</button>
        <button style={{
          padding: '10px 24px', backgroundColor: COLORS.primary, border: 'none',
          borderRadius: '8px', color: '#FFFFFF', fontWeight: '600', fontSize: '13px', cursor: 'pointer',
        }}>Sync to CRM</button>
      </div>
    </div>
  );

  return (
    <div style={{ paddingTop: '24px' }}>
      <div style={{ display: 'flex', gap: '32px', minHeight: 'calc(100vh - 140px)' }}>
        {/* List Pane */}
        <div style={{
          width: '380px', flexShrink: 0,
          display: selectedCall ? undefined : 'flex', flexDirection: 'column', gap: '20px',
        }}>
          <div>
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#0F172A', marginBottom: '16px', fontFamily: 'Inter, system-ui, sans-serif' }}>Call Records</h2>

            {/* Search */}
            <div style={{ position: 'relative', marginBottom: '12px' }}>
              <svg style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', width: '16px', height: '16px', color: '#94A3B8' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search calls..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%', padding: '12px 14px 12px 42px',
                  border: '1px solid #E2E8F0', borderRadius: '10px',
                  fontSize: '14px', color: '#0F172A', backgroundColor: '#FFFFFF',
                }}
              />
            </div>

            {/* Date Filter */}
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px' }}>
              <select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                style={{
                  padding: '10px 14px', border: '1px solid #E2E8F0', borderRadius: '8px',
                  fontSize: '13px', color: '#0F172A', backgroundColor: '#FFFFFF', cursor: 'pointer',
                }}
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="yesterday">Yesterday</option>
                <option value="week">Last 7 Days</option>
                <option value="month">Last 30 Days</option>
                <option value="custom">Select Date</option>
              </select>
              {dateFilter === 'custom' && (
                <input type="date" value={customDate} onChange={(e) => setCustomDate(e.target.value)}
                  style={{
                    padding: '10px 14px', border: '1px solid #E2E8F0', borderRadius: '8px',
                    fontSize: '13px', color: '#0F172A', backgroundColor: '#FFFFFF',
                  }}
                />
              )}
            </div>

            <p style={{ fontSize: '12px', color: '#94A3B8', fontWeight: '600', marginBottom: '16px' }}>
              {filteredCalls.length} {filteredCalls.length === 1 ? 'call' : 'calls'} found
            </p>
          </div>

          {/* Call List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }}>
            {filteredCalls.map((call) => (
              <div
                key={call.id}
                onClick={() => setSelectedCall(call)}
                style={{
                  padding: '16px', borderRadius: '12px', cursor: 'pointer',
                  backgroundColor: selectedCall?.id === call.id ? '#FFF7ED' : '#FFFFFF',
                  border: `1px solid ${selectedCall?.id === call.id ? '#FFEDD5' : '#E2E8F0'}`,
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (selectedCall?.id !== call.id) e.currentTarget.style.borderColor = '#CBD5E1';
                }}
                onMouseLeave={(e) => {
                  if (selectedCall?.id !== call.id) e.currentTarget.style.borderColor = '#E2E8F0';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                  <div>
                    <p style={{ fontSize: '14px', fontWeight: '600', color: '#0F172A' }}>{call.caller}</p>
                    <p style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>{formatIndianTime(call.timestamp)} IST</p>
                  </div>
                  <span style={{
                    padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: '600',
                    backgroundColor: call.intent === 'appointment' ? '#F0FDFA' : '#FDF4FF',
                    color: call.intent === 'appointment' ? '#0D9488' : '#A855F7',
                    textTransform: 'capitalize',
                  }}>
                    {call.intent}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', color: '#64748B', fontWeight: '500' }}>{call.status}</span>
                  <span style={{ width: '3px', height: '3px', borderRadius: '50%', backgroundColor: '#CBD5E1', display: 'inline-block' }} />
                  <span style={{ fontSize: '12px', color: '#64748B', fontWeight: '500' }}>{call.duration}s</span>
                  <span style={{ width: '3px', height: '3px', borderRadius: '50%', backgroundColor: '#CBD5E1', display: 'inline-block' }} />
                  <span style={{ fontSize: '12px', color: '#10B981', fontWeight: '500' }}>{call.token_usage || 0} tokens</span>
                </div>
                <p style={{ fontSize: '13px', color: '#94A3B8', fontStyle: 'italic', lineHeight: '1.5', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  "{call.summary}"
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Detail Pane */}
        <div style={{
          flex: 1, backgroundColor: '#FFFFFF', borderRadius: '16px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)', overflow: 'hidden',
          display: 'flex', flexDirection: 'column',
        }}>
          {selectedCall ? (
            <ConversationView call={selectedCall} />
          ) : (
            <div style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', padding: '48px',
            }}>
              <div style={{
                width: '72px', height: '72px', borderRadius: '16px', backgroundColor: '#F1F5F9',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px',
              }}>
                <svg width="32" height="32" fill="none" stroke="#CBD5E1" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
                </svg>
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: '700', color: '#0F172A', marginBottom: '8px' }}>Select a Call</h3>
              <p style={{ fontSize: '14px', color: '#94A3B8', maxWidth: '300px', textAlign: 'center', lineHeight: '1.6' }}>
                Choose a call record from the list to review the transcript and summary.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Transcripts;
