import axios from 'axios';
import toast from 'react-hot-toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const client = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refresh });
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          client.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
          return client(originalRequest);
        } catch (e) {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    const msg = error.response?.data?.detail || 'Error';
    toast.error(msg);
    return Promise.reject(error);
  }
);
