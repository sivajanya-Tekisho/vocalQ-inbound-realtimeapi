import React from 'react';
import { ViewState } from '../types';
import { COLORS } from '../constants';
import { api } from '../services/api';

interface HeaderProps {
    activeView: ViewState;
    onViewChange: (view: ViewState) => void;
}

const Header: React.FC<HeaderProps> = ({ activeView, onViewChange }) => {
    const [inboundEnabled, setInboundEnabled] = React.useState(false);
    const [isLoading, setIsLoading] = React.useState(false);

    const menuItems: Array<{ id: ViewState; label: string }> = [
        { id: 'overview', label: 'Home' },
        { id: 'realtime', label: 'Queue' },
        { id: 'transcripts', label: 'CallLogs' },
        { id: 'knowledge', label: 'Knowledge' },
        { id: 'settings', label: 'Settings' },
    ];

    // Load initial inbound status from backend
    React.useEffect(() => {
        const loadInboundStatus = async () => {
            try {
                const data = await api.getInboundStatus();
                setInboundEnabled(data.enabled);
            } catch (error) {
                console.error('Failed to load inbound status:', error);
            }
        };
        loadInboundStatus();
    }, []);

    const handleToggleInbound = async () => {
        if (isLoading) return; // Prevent multiple clicks

        const newStatus = !inboundEnabled;
        setIsLoading(true);

        try {
            await api.setInboundStatus(newStatus);
            setInboundEnabled(newStatus);
            console.log('Inbound calls', newStatus ? 'enabled' : 'disabled');
        } catch (error) {
            console.error('Failed to update inbound status:', error);
            // Revert on error
            alert('Failed to update inbound status. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <header style={{
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E2E8F0',
            padding: '0 40px',
            height: '64px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 100,
        }}>
            {/* Logo */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, #FF6B35, #FF8C61)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: '700',
                    fontSize: '18px',
                    fontFamily: 'Inter, system-ui, sans-serif',
                }}>
                    V
                </div>
                <span style={{
                    fontSize: '18px',
                    fontWeight: '700',
                    color: '#0F172A',
                    letterSpacing: '-0.02em',
                    fontFamily: 'Inter, system-ui, sans-serif',
                }}>
                    VocalQ
                </span>
            </div>

            {/* Navigation */}
            <nav style={{ display: 'flex', gap: '32px', alignItems: 'center' }}>
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => onViewChange(item.id)}
                        style={{
                            padding: 0,
                            border: 'none',
                            background: 'none',
                            color: activeView === item.id ? '#0F172A' : '#64748B',
                            fontWeight: activeView === item.id ? '600' : '400',
                            fontSize: '15px',
                            cursor: 'pointer',
                            transition: 'color 0.2s',
                            fontFamily: 'Inter, system-ui, sans-serif',
                            lineHeight: '64px',
                            height: '64px',
                            borderBottom: activeView === item.id ? '2px solid #FF6B35' : '2px solid transparent',
                            marginBottom: '-1px',
                        }}
                        onMouseEnter={(e) => {
                            if (activeView !== item.id) {
                                e.currentTarget.style.color = '#0F172A';
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (activeView !== item.id) {
                                e.currentTarget.style.color = '#64748B';
                            }
                        }}
                    >
                        {item.label}
                    </button>
                ))}
            </nav>

            {/* Inbound Toggle Switch */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
            }}>
                <span style={{
                    fontSize: '14px',
                    fontWeight: '500',
                    color: '#64748B',
                    fontFamily: 'Inter, system-ui, sans-serif',
                }}>
                    Inbound
                </span>
                <button
                    onClick={handleToggleInbound}
                    disabled={isLoading}
                    style={{
                        width: '48px',
                        height: '26px',
                        borderRadius: '13px',
                        border: 'none',
                        cursor: isLoading ? 'wait' : 'pointer',
                        position: 'relative',
                        backgroundColor: inboundEnabled ? '#10B981' : '#CBD5E1',
                        transition: 'background-color 0.3s',
                        padding: 0,
                        opacity: isLoading ? 0.6 : 1,
                    }}
                >
                    <div style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '10px',
                        backgroundColor: '#FFFFFF',
                        position: 'absolute',
                        top: '3px',
                        left: inboundEnabled ? '25px' : '3px',
                        transition: 'left 0.3s',
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                    }} />
                </button>
                <span style={{
                    fontSize: '12px',
                    fontWeight: '600',
                    color: inboundEnabled ? '#10B981' : '#94A3B8',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    minWidth: '30px',
                }}>
                    {inboundEnabled ? 'ON' : 'OFF'}
                </span>
            </div>
        </header>
    );
};

export default Header;
