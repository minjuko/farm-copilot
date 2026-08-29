import { instance } from './instance';

export const fetchCapabilities = () => instance.get('/api/capabilities/');

export const normalizeCapability = (payload, serviceName) => {
  const capability = payload?.[serviceName];
  if (!capability || typeof capability.available !== 'boolean') {
    return { status: 'limited', available: false, reason: 'unavailable' };
  }
  return capability;
};
