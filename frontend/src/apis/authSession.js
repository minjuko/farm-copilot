const unauthorizedListeners = new Set();

export const subscribeToUnauthorized = (listener) => {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
};

export const notifyUnauthorized = () => {
  unauthorizedListeners.forEach((listener) => listener());
};
