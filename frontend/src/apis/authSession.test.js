import { notifyUnauthorized, subscribeToUnauthorized } from "./authSession";

test("notifies current unauthorized subscribers and supports cleanup", () => {
  const listener = jest.fn();
  const unsubscribe = subscribeToUnauthorized(listener);

  notifyUnauthorized();
  expect(listener).toHaveBeenCalledTimes(1);

  unsubscribe();
  notifyUnauthorized();
  expect(listener).toHaveBeenCalledTimes(1);
});
