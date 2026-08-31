import { act, renderHook } from "@testing-library/react";
import { LoadingProvider, useLoading } from "./LoadingContext";

const wrapper = ({ children }) => <LoadingProvider>{children}</LoadingProvider>;

test("keeps loading visible until every overlapping request finishes", () => {
  const { result } = renderHook(() => useLoading(), { wrapper });
  let finishFirst;
  let finishSecond;

  act(() => {
    finishFirst = result.current.beginLoading();
    finishSecond = result.current.beginLoading();
  });
  expect(result.current.loadingCount).toBe(2);
  expect(result.current.isLoading).toBe(true);

  act(() => finishFirst());
  expect(result.current.loadingCount).toBe(1);
  expect(result.current.isLoading).toBe(true);

  act(() => finishSecond());
  expect(result.current.loadingCount).toBe(0);
  expect(result.current.isLoading).toBe(false);
});

test("makes the finish callback idempotent and never underflows", () => {
  const { result } = renderHook(() => useLoading(), { wrapper });
  let finish;

  act(() => { finish = result.current.beginLoading(); });
  act(() => { finish(); finish(); result.current.endLoading(); });

  expect(result.current.loadingCount).toBe(0);
  expect(result.current.isLoading).toBe(false);
});

test("supports existing balanced setIsLoading callers without overlap races", () => {
  const { result } = renderHook(() => useLoading(), { wrapper });

  act(() => {
    result.current.setIsLoading(true);
    result.current.setIsLoading(true);
    result.current.setIsLoading(false);
  });
  expect(result.current.isLoading).toBe(true);
  expect(result.current.loadingCount).toBe(1);

  act(() => result.current.setIsLoading(false));
  expect(result.current.isLoading).toBe(false);
});

test("withLoading releases the counter after success and failure", async () => {
  const { result } = renderHook(() => useLoading(), { wrapper });

  await act(async () => {
    await expect(result.current.withLoading(async () => "done")).resolves.toBe("done");
  });
  expect(result.current.loadingCount).toBe(0);

  await act(async () => {
    await expect(result.current.withLoading(async () => { throw new Error("failed"); }))
      .rejects.toThrow("failed");
  });
  expect(result.current.loadingCount).toBe(0);
});
