import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  signup: (email, password) => api.post('/api/auth/signup', { email, password }),
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  getMe: () => api.get('/api/auth/me'),
};

// Strategy API
export const strategyAPI = {
  generate: (data) => api.post('/api/strategy', data),
  getHistory: () => api.get('/api/history'),
  getById: (id) => api.get(`/api/strategy/${id}`),
  delete: (id) => api.delete(`/api/strategy/${id}`),
  submitFeedback: (strategyId, rating) => api.post('/feedback', { strategy_id: strategyId, rating }),
};

export default api;
