import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// API endpoints matching backend
export const dashboardAPI = {
  getHealth: () => api.get('/health'),
  
  getStats: (businessId: string) => 
    api.get(`/api/dashboard/stats?business_id=${businessId}`),
  
  getRecentCalls: (businessId: string, limit = 50) =>
    api.get(`/api/dashboard/calls/recent?business_id=${businessId}&limit=${limit}`),
  
  getCallTranscript: (callId: string) =>
    api.get(`/api/dashboard/calls/${callId}/transcript`),
  
  getCallAnalytics: (businessId: string, startDate?: string, endDate?: string) =>
    api.get(`/api/dashboard/analytics/calls`, {
      params: { business_id: businessId, start_date: startDate, end_date: endDate }
    }),
};

export const businessAPI = {
  getByPhone: (phone: string) =>
    api.get(`/api/business/phone/${encodeURIComponent(phone)}`),
  
  create: (data: any) =>
    api.post('/api/business/create', data),
  
  get: (businessId: string) =>
    api.get(`/api/business/${businessId}`),
};

export const voiceAPI = {
  simulateCall: (businessPhone: string, message: string) =>
    api.post('/api/voice/test/simulate', 
      `business_phone=${encodeURIComponent(businessPhone)}&message=${encodeURIComponent(message)}`,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' }}
    ),
};
