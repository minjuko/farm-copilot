import { getApiErrorMessage, getServiceErrorMessage } from './error';

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

describe('getServiceErrorMessage', () => {
  it('does not expose backend infrastructure messages for 5xx responses', () => {
    const error = { response: { status: 503, data: { message: 'Internal service detail' } } };

    expect(getServiceErrorMessage(error, 'safe fallback')).toBe('safe fallback');
  });

  it('keeps actionable validation messages for 4xx responses', () => {
    const error = { response: { status: 400, data: { message: 'Invalid input' } } };

    expect(getServiceErrorMessage(error, 'safe fallback')).toBe('Invalid input');
  });
});
