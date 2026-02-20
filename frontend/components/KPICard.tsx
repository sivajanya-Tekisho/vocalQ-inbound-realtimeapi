import React from 'react';
import { BusinessMetric } from '../types';
import { COLORS } from '../constants';

const KPICard: React.FC<BusinessMetric> = ({ label, value, change, trend }) => {
  const getAccent = () => {
    if (label.includes('Total Calls')) return { colors: ['#EF4444', '#F59E0B'], sub: 'All time' };
    if (label.includes('Contacts') || label.includes('Answered')) return { colors: ['#8B5CF6', '#6366F1'], sub: 'Active users' };
    if (label.includes('Duration') || label.includes('Avg')) return { colors: ['#06B6D4', '#3B82F6'], sub: 'Per call' };
    if (label.includes('Missed')) return { colors: ['#EF4444', '#F87171'], sub: 'All time' };
    return { colors: ['#FF6B35', '#FF8C61'], sub: 'All time' };
  };

  const { colors, sub } = getAccent();

  return (
    <div style={{
      backgroundColor: '#F1F5F9',
      borderRadius: '16px',
      padding: '24px 28px',
      position: 'relative',
      overflow: 'hidden',
      transition: 'transform 0.2s',
      cursor: 'default',
    }}
      onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; }}
    >
      <p style={{
        fontSize: '13px',
        fontWeight: '500',
        color: '#64748B',
        marginBottom: '12px',
        letterSpacing: '0.01em',
      }}>
        {label}
      </p>

      <h3 style={{
        fontSize: '36px',
        fontWeight: '700',
        color: '#0F172A',
        lineHeight: '1',
        marginBottom: '8px',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        {value}
      </h3>

      <p style={{
        fontSize: '12px',
        color: '#94A3B8',
        fontWeight: '400',
      }}>
        {sub}
      </p>

      {/* Gradient bottom border */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: '4px',
        background: `linear-gradient(90deg, ${colors[0]}, ${colors[1]})`,
      }} />
    </div>
  );
};

export default KPICard;
