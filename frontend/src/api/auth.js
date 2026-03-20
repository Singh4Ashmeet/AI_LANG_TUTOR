import { client } from './client';

export const authApi = {
  login: (email, password) => client.post('/auth/login', { email, password }),
  register: (data) => client.post('/auth/register', data),
  refresh: (token) => client.post('/auth/refresh', { refresh_token: token }),
  logout: () => client.post('/auth/logout'),
};
