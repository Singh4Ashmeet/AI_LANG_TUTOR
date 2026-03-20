import { client } from './client';

export const lessonsApi = {
  start: () => client.post('/lessons/start'),
  complete: (sessionId, xp) => client.post('/lessons/complete', null, { params: { session_id: sessionId, xp } }),
};
