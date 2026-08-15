import { getApiErrorMessage } from './error';

describe('getApiErrorMessage', () => {
  it('uses the backend message contract when available', () => {
    const error = { response: { data: { message: 'Service unavailable' } } };

    expect(getApiErrorMessage(error, 'fallback')).toBe('Service unavailable');
  });

  it('supports the legacy backend error contract', () => {
    const error = { response: { data: { error: 'Invalid request' } } };

    expect(getApiErrorMessage(error, 'fallback')).toBe('Invalid request');
  });

  it('uses a safe fallback for network errors', () => {
    expect(getApiErrorMessage(new Error('Network Error'), 'fallback')).toBe('fallback');
  });
});
