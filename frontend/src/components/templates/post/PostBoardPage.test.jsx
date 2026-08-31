import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { fetchPosts } from "../../../apis/post";
import PostBoardPage from "./PostBoardPage";

const mockSetIsLoading = jest.fn();
let mockAuthStatus = "unauthenticated";

jest.mock("../../../apis/post", () => ({ fetchPosts: jest.fn() }));
jest.mock("../../../AuthContext", () => ({
  useAuth: () => ({ status: mockAuthStatus }),
}));
jest.mock("../../../LoadingContext", () => ({
  useLoading: () => ({ setIsLoading: mockSetIsLoading }),
}));

const post = (id, title) => ({
  id,
  title,
  user__username: `farmer-${id}`,
  creation_date: `2026-08-${String(id).padStart(2, "0")}T10:00:00Z`,
  comment_count: id,
});

const renderBoard = (props = {}) => render(
  <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <PostBoardPage postType="buy" boardLabel="구매 게시판" {...props} />
  </MemoryRouter>
);

beforeEach(() => {
  jest.clearAllMocks();
  mockAuthStatus = "unauthenticated";
  fetchPosts.mockResolvedValue({ data: [post(1, "apple"), post(2, "pepper")] });
});

test.each([
  ["buy", "구매 게시판"],
  ["sell", "판매 게시판"],
  ["exchange", "나눔 게시판"],
])("loads only the %s post contract", async (postType, boardLabel) => {
  renderBoard({ postType, boardLabel });

  expect(await screen.findByText("pepper")).toBeInTheDocument();
  expect(fetchPosts).toHaveBeenCalledWith(postType);
  expect(mockSetIsLoading.mock.calls).toEqual([[true], [false]]);
});

test("filters titles and shows an explicit empty result", async () => {
  renderBoard();
  await screen.findByText("pepper");

  fireEvent.change(screen.getByRole("searchbox", { name: "구매 게시판 제목 검색" }), {
    target: { value: "missing" },
  });

  expect(screen.getByText("검색 결과가 없습니다.")).toBeInTheDocument();
});

test("shows the correctly typed create link only to authenticated users", async () => {
  mockAuthStatus = "authenticated";
  renderBoard({ postType: "exchange", boardLabel: "나눔 게시판" });
  await screen.findByText("pepper");

  expect(screen.getByRole("link", { name: /글 작성/ })).toHaveAttribute(
    "href", "/post/create?post_type=exchange"
  );
});

test("renders a controlled API error instead of a browser alert", async () => {
  fetchPosts.mockRejectedValue({ response: { status: 503 } });
  renderBoard();

  expect(await screen.findByRole("alert")).toHaveTextContent("게시글을 불러오지 못했습니다");
  await waitFor(() => expect(mockSetIsLoading).toHaveBeenLastCalledWith(false));
});

test("paginates the filtered post collection", async () => {
  fetchPosts.mockResolvedValue({ data: Array.from({ length: 6 }, (_, index) => post(index + 1, `post-${index + 1}`)) });
  renderBoard();

  expect(await screen.findByRole("navigation", { name: "구매 게시판 페이지 탐색" })).toBeInTheDocument();
  fireEvent.click(screen.getByText("다음"));
  expect(screen.getByText("post-1")).toBeInTheDocument();
  expect(screen.queryByText("post-6")).not.toBeInTheDocument();
});
