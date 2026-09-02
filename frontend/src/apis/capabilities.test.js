import { instance } from './client';
import { fetchCapabilities, normalizeCapability } from './capabilities';

jest.mock('./client', () => ({ instance: { get: jest.fn() } }));

beforeEach(() => jest.clearAllMocks());

test('fetches public capability state', () => {
  fetchCapabilities();
  expect(instance.get).toHaveBeenCalledWith('/api/capabilities/');
});

test('normalizes missing or malformed service state to limited', () => {
  expect(normalizeCapability({}, 'soil')).toEqual({
    status: 'limited', available: false, reason: 'unavailable',
  });
});

test('preserves a valid capability response', () => {
  const capability = { status: 'available', available: true, reason: null };
  expect(normalizeCapability({ prediction: capability }, 'prediction')).toBe(capability);
});
