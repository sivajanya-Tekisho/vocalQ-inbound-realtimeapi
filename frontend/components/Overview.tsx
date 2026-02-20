import React from 'react';
import KPICard from './KPICard';
import { api } from '../services/api';
import { COLORS } from '../constants';
import {
  CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis
} from 'recharts';

const Overview: React.FC = () => {
  const [businessStats, setBusinessStats] = React.useState<any[]>([
    { label: 'Total Calls', value: '0', change: 0, trend: 'up' },
    { label: 'Total Contacts', value: '0', change: 0, trend: 'up' },
    { label: 'Avg Duration', value: '0s', change: 0, trend: 'up' },
  ]);
  const [hourWiseCalls, setHourWiseCalls] = React.useState<any[]>([]);
  const [activePeriod, setActivePeriod] = React.useState('Hourly');

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await api.getAnalytics();
        const stats = [
          { label: 'Total Calls', value: data.total_calls.toLocaleString(), change: 0, trend: 'up' as const },
          { label: 'Total Contacts', value: data.completed_calls.toLocaleString(), change: 0, trend: 'up' as const },
          { label: 'Avg Duration', value: `${Math.round(data.avg_duration)}s`, change: 0, trend: 'up' as const },
        ];
        setBusinessStats(stats);
        setHourWiseCalls(data.calls_by_hour);
      } catch (error) {
        console.error("Failed to load analytics", error);
      }
    };
    fetchData();
  }, []);

  return (
    <div>
      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '48px 0 40px',
      }}>
        <h1 style={{
          fontSize: '42px',
          fontWeight: '700',
          color: '#0F172A',
          lineHeight: '1.25',
          marginBottom: '16px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}>
          Smarter calling, faster<br />
          <span style={{
            background: 'linear-gradient(90deg, #FF6B35, #EF4444)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            execution, better results.
          </span>
        </h1>
        <p style={{
          fontSize: '16px',
          color: '#64748B',
          fontWeight: '400',
          lineHeight: '1.6',
        }}>
          Track progress, collaborate seamlessly, and hit every deadline with confidence.
        </p>
      </div>

      {/* KPI Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '24px',
        marginBottom: '40px',
      }}>
        {businessStats.map((stat, idx) => (
          <KPICard key={idx} {...stat} />
        ))}
      </div>

      {/* Call Analytics Chart */}
      <div style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '16px',
        padding: '28px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '28px',
        }}>
          <div>
            <h3 style={{
              fontSize: '20px',
              fontWeight: '700',
              color: '#0F172A',
              marginBottom: '4px',
              fontFamily: 'Inter, system-ui, sans-serif',
            }}>
              Call Analytics
            </h3>
            <p style={{
              fontSize: '14px',
              color: '#94A3B8',
              fontWeight: '400',
            }}>
              Track your call activity over time
            </p>
          </div>

          {/* Time Period Tabs */}
          <div style={{
            display: 'flex',
            gap: '4px',
            backgroundColor: '#F1F5F9',
            padding: '4px',
            borderRadius: '10px',
          }}>
            {['Hourly', 'Daily', 'Weekly', 'Monthly'].map((period) => (
              <button
                key={period}
                onClick={() => setActivePeriod(period)}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  background: activePeriod === period ? '#FFFFFF' : 'transparent',
                  color: activePeriod === period ? '#0F172A' : '#64748B',
                  fontWeight: activePeriod === period ? '600' : '400',
                  fontSize: '13px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  boxShadow: activePeriod === period ? '0 1px 2px 0 rgba(0, 0, 0, 0.06)' : 'none',
                  transition: 'all 0.2s',
                  fontFamily: 'Inter, system-ui, sans-serif',
                }}
              >
                {period}
              </button>
            ))}
          </div>
        </div>

        {/* Area Chart */}
        <div style={{ height: '280px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={hourWiseCalls}>
              <defs>
                <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF6B35" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#FF6B35" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis
                dataKey="name"
                stroke="#94A3B8"
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
              />
              <YAxis
                stroke="#94A3B8"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  fontSize: '13px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  fontFamily: 'Inter, system-ui, sans-serif',
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#FF6B35"
                strokeWidth={2.5}
                fill="url(#colorCalls)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Overview;
