import { notifyUnauthorized } from "./authSession";
import { handleResponseError } from "./client";

jest.mock("./authSession", () => ({ notifyUnauthorized: jest.fn() }));

beforeEach(() => jest.clearAllMocks());

test("notifies auth state and preserves a 401 rejection", async () => {
  const error = { response: { status: 401 } };

  await expect(handleResponseError(error)).rejects.toBe(error);
  expect(notifyUnauthorized).toHaveBeenCalledTimes(1);
});

test("preserves non-auth failures without clearing auth state", async () => {
  const error = { response: { status: 503 } };

  await expect(handleResponseError(error)).rejects.toBe(error);
  expect(notifyUnauthorized).not.toHaveBeenCalled();
});
