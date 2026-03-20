import { client } from './client';

export const usersApi = {
  me: () => client.get('/users/me'),
};
