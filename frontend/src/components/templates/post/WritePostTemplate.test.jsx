import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { createPost } from "../../../apis/post";
import { LoadingProvider } from "../../../LoadingContext";
import WritePostTemplate, { getInitialPostType } from "./WritePostTemplate";

jest.mock("../../../apis/post", () => ({ createPost: jest.fn() }));

const renderWritePost = (search = "") => render(
  <MemoryRouter initialEntries={[`/post/create${search}`]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <LoadingProvider><WritePostTemplate /></LoadingProvider>
  </MemoryRouter>
);

test.each([
  ["sell", "sell"],
  ["buy", "buy"],
  ["exchange", "exchange"],
  [undefined, "buy"],
  ["unsupported", "buy"],
])("uses %s query as the safe initial post type %s", (query, expected) => {
  expect(getInitialPostType(query)).toBe(expected);
  renderWritePost(query ? `?post_type=${query}` : "");
  expect(screen.getByRole("combobox")).toHaveValue(expected);
});

test("keeps manual selection and the submit payload contract", async () => {
  createPost.mockResolvedValue({ data: { id: 7 } });
  renderWritePost("?post_type=sell");

  fireEvent.change(screen.getByRole("combobox"), { target: { value: "exchange" } });
  const textboxes = screen.getAllByRole("textbox");
  fireEvent.change(textboxes[0], { target: { value: "title" } });
  fireEvent.change(textboxes[1], { target: { value: "content" } });
  fireEvent.click(document.querySelector('button[type="submit"]'));

  await waitFor(() => expect(createPost).toHaveBeenCalledTimes(1));
  expect(createPost.mock.calls[0][0].get("post_type")).toBe("exchange");
});
