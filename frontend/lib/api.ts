import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the auth token when one is stored (set by the login flow).
// Backend runs with AUTH_ENABLED=false in local dev, so absence of a
// token is fine there.
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('zenith_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auth API - matches backend /api/auth routes
export const authAPI = {
  register: (businessId: string, email: string, password: string, fullName?: string) =>
    api.post('/api/auth/register', {
      business_id: businessId, email, password, full_name: fullName,
    }),
  login: (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }),
  me: () => api.get('/api/auth/me'),
  setToken: (token: string) => localStorage.setItem('zenith_token', token),
  clearToken: () => localStorage.removeItem('zenith_token'),
};

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error('API Error:', error.response.status, error.response.data);
      // Session expired or revoked: clear the stale token and send the
      // user to login. Auth endpoints are excluded — a 401 there is a
      // normal wrong-password (or auth-disabled /me) response, not an
      // expired session.
      if (
        error.response.status === 401 &&
        typeof window !== 'undefined' &&
        !error.config?.url?.includes('/api/auth/') &&
        window.location.pathname !== '/login'
      ) {
        localStorage.removeItem('zenith_token');
        window.location.href = '/login';
      }
    } else if (error.request) {
      console.error('API Error: No response received - is backend running?');
    } else {
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// Dashboard API - matches backend /api/analytics routes
export const dashboardAPI = {
  getHealth: () => api.get('/health'),

  getStats: (businessId: string) =>
    api.get('/api/analytics/summary', { params: { business_id: businessId } }),

  getRecentCalls: (businessId: string, limit = 50) =>
    api.get('/api/calls', { params: { business_id: businessId, limit } }),

  getCallTranscript: (callId: string) =>
    api.get(`/api/calls/${callId}/transcript`),

  getCallAnalytics: (businessId: string, startDate?: string, endDate?: string) =>
    api.get('/api/analytics/summary', { params: { business_id: businessId } }),
};

// Business API - matches backend /api/businesses routes
export const businessAPI = {
  getByPhone: (phone: string) =>
    api.get(`/api/businesses`).then(res => {
      const business = res.data.find((b: any) => b.phone_number === phone);
      if (business) return { data: business };
      throw new Error('Business not found');
    }),
  
  create: (data: any) =>
    api.post('/api/businesses', data),
  
  get: (businessId: string) =>
    api.get(`/api/businesses/${businessId}`),
    
  list: () =>
    api.get('/api/businesses'),
    
  delete: (businessId: string) =>
    api.delete(`/api/businesses/${businessId}`),
};

// Voice API - matches backend /api/voice routes
export const voiceAPI = {
  simulateCall: (businessPhone: string, message: string, callerNumber?: string) => {
    const formData = new FormData();
    formData.append('business_phone', businessPhone);
    formData.append('message', message);
    if (callerNumber) formData.append('caller_number', callerNumber);
    
    return api.post('/api/voice/test/simulate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Also export with alternate names for compatibility
export const businessesApi = businessAPI;
export const callsApi = {
  list: dashboardAPI.getRecentCalls,
  get: (id: string) => api.get(`/api/calls/${id}`),
  getTranscript: dashboardAPI.getCallTranscript,
};
export const analyticsApi = {
  summary: () => api.get('/api/analytics/summary'),
  callsByDay: (days?: number) => api.get('/api/analytics/calls-by-day', { params: { days } }),
};

export default api;
