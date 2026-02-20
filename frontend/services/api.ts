import { CallMetric, BusinessDataMetrics, ChartData } from '../types';

// Dynamic API URL - works for both local and production
const API_BASE_URL = typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
    : 'http://localhost:8000/api/v1';

export const api = {
    async getAnalytics(): Promise<{
        total_calls: number;
        completed_calls: number;
        missed_calls: number;
        avg_duration: number;
        intent_distribution: Record<string, number>;
        calls_by_hour: { name: string; value: number }[];
        peak_window: string;
    }> {
        const response = await fetch(`${API_BASE_URL}/calls/analytics`);
        if (!response.ok) throw new Error('Failed to fetch analytics');
        return response.json();
    },

    async getCalls(skip = 0, limit = 100): Promise<CallMetric[]> {
        const response = await fetch(`${API_BASE_URL}/calls/?skip=${skip}&limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch calls');
        return response.json();
    },

    async getActiveCalls(): Promise<CallMetric[]> {
        const response = await fetch(`${API_BASE_URL}/calls/active`);
        if (!response.ok) throw new Error('Failed to fetch active calls');
        return response.json();
    },

    async getCallDetails(callId: string): Promise<CallMetric> {
        const response = await fetch(`${API_BASE_URL}/calls/${callId}`);
        if (!response.ok) throw new Error('Failed to fetch call details');
        return response.json();
    },

    async getInboundStatus(): Promise<{ enabled: boolean }> {
        const response = await fetch(`${API_BASE_URL}/admin/settings/inbound`);
        if (!response.ok) throw new Error('Failed to fetch inbound status');
        return response.json();
    },

    async setInboundStatus(enabled: boolean): Promise<{ status: string; enabled: boolean }> {
        const response = await fetch(`${API_BASE_URL}/admin/settings/inbound`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ enabled }),
        });
        if (!response.ok) throw new Error('Failed to update inbound status');
        return response.json();
    },

    async getQueue(): Promise<{ success: boolean; count: number; queue: any[] }> {
        const response = await fetch(`${API_BASE_URL}/queue/queue`);
        if (!response.ok) throw new Error('Failed to fetch queue');
        return response.json();
    },

    async getQueueStats(): Promise<{ total: number; waiting: number; assigned: number; high_priority: number }> {
        const response = await fetch(`${API_BASE_URL}/queue/queue/stats`);
        if (!response.ok) throw new Error('Failed to fetch queue stats');
        return response.json();
    }
};
