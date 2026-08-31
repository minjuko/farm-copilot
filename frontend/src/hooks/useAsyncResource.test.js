import { act, renderHook, waitFor } from "@testing-library/react";
import { LoadingProvider } from "../LoadingContext";
import useAsyncResource from "./useAsyncResource";

const wrapper = ({ children }) => <LoadingProvider>{children}</LoadingProvider>;

test("exposes the shared data, loading, error, and refetch contract", async () => {
  const loader = jest.fn().mockResolvedValueOnce(["first"]).mockResolvedValueOnce(["second"]);
  const { result } = renderHook(() => useAsyncResource(loader, { initialData: [] }), { wrapper });

  await waitFor(() => expect(result.current.data).toEqual(["first"]));
  expect(result.current.error).toBeNull();

  await act(async () => { await result.current.refetch(); });
  expect(result.current.data).toEqual(["second"]);
  expect(loader).toHaveBeenCalledTimes(2);
});

test("maps failures into a user-facing error and ends loading", async () => {
  const loader = jest.fn().mockRejectedValue(new Error("network"));
  const getError = (error) => `controlled: ${error.message}`;
  const { result } = renderHook(
    () => useAsyncResource(loader, { getError, initialData: [] }),
    { wrapper }
  );

  await waitFor(() => expect(result.current.error).toBe("controlled: network"));
  expect(result.current.isLoading).toBe(false);
  expect(result.current.data).toEqual([]);
});

test("ignores a stale response after a newer refetch", async () => {
  let resolveFirst;
  let resolveSecond;
  const loader = jest.fn()
    .mockReturnValueOnce(new Promise((resolve) => { resolveFirst = resolve; }))
    .mockReturnValueOnce(new Promise((resolve) => { resolveSecond = resolve; }));
  const { result } = renderHook(() => useAsyncResource(loader), { wrapper });

  await waitFor(() => expect(loader).toHaveBeenCalledTimes(1));
  act(() => { result.current.refetch(); });
  await waitFor(() => expect(loader).toHaveBeenCalledTimes(2));
  await act(async () => { resolveSecond("new"); });
  await waitFor(() => expect(result.current.data).toBe("new"));
  await act(async () => { resolveFirst("stale"); });
  expect(result.current.data).toBe("new");
});

test("does not update component state after unmount", async () => {
  let resolveRequest;
  const loader = () => new Promise((resolve) => { resolveRequest = resolve; });
  const consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
  const { unmount } = renderHook(() => useAsyncResource(loader), { wrapper });

  await waitFor(() => expect(resolveRequest).toBeDefined());
  unmount();
  await act(async () => { resolveRequest("late"); });

  expect(consoleError).not.toHaveBeenCalled();
  consoleError.mockRestore();
});
