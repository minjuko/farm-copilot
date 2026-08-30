import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PostDetail from "../../molecules/PostDetail";
import Comment from "../../molecules/Comment";
import { isCommunityOwner } from "./communityOwnership";

const post = {
  id: 7,
  title: "내 게시글",
  content: "내용",
  post_type: "buy",
  user_id: 3,
  username: "farmer",
  creation_date: "2026-08-20T00:00:00Z",
};

const postDetailProps = {
  post,
  showSettingsMenu: { 0: true },
  settingsMenuRefs: { current: [] },
  openModal: jest.fn(),
  handleSettingsClick: jest.fn(),
  isModalOpen: false,
  closeModal: jest.fn(),
  handleDeletePost: jest.fn(),
};

const commentProps = {
  comments: [{
    id: 11,
    content: "내 댓글",
    user_id: 3,
    user__username: "farmer",
    created_at: "2026-08-20T00:00:00Z",
    parent_id: null,
  }],
  newComment: "",
  newReply: "",
  replyCommentId: null,
  editCommentId: null,
  editCommentContent: "",
  handleCommentChange: jest.fn(),
  handleEditCommentChange: jest.fn(),
  handleReplyChange: jest.fn(),
  handleSubmitComment: jest.fn(),
  handleSubmitReply: jest.fn(),
  handleEditComment: jest.fn(),
  handleDeleteComment: jest.fn(),
  setReplyCommentId: jest.fn(),
  setEditCommentId: jest.fn(),
  setEditCommentContent: jest.fn(),
};

test("matches an owner by id and falls back to the authenticated username", () => {
  expect(isCommunityOwner("authenticated", { user_id: "3" }, post)).toBe(true);
  expect(isCommunityOwner("authenticated", { username: "farmer" }, post)).toBe(true);
  expect(isCommunityOwner("authenticated", { username: "other" }, post)).toBe(false);
  expect(isCommunityOwner("unauthenticated", { username: "farmer" }, post)).toBe(false);
  expect(isCommunityOwner("checking", { username: "farmer" }, post)).toBe(false);
});

test("shows post edit and delete UI only to the owner", () => {
  const { rerender } = render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PostDetail {...postDetailProps} canManagePost />
    </MemoryRouter>
  );

  expect(screen.getByLabelText("게시글 관리")).toBeInTheDocument();
  expect(screen.getByText("수정")).toBeInTheDocument();
  expect(screen.getByText("삭제")).toBeInTheDocument();

  rerender(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PostDetail {...postDetailProps} canManagePost={false} />
    </MemoryRouter>
  );
  expect(screen.queryByLabelText("게시글 관리")).not.toBeInTheDocument();
  expect(screen.queryByText("수정")).not.toBeInTheDocument();
});

test("shows comment create and owner controls to an authenticated owner", () => {
  render(<Comment {...commentProps} authStatus="authenticated" user={{ username: "farmer" }} />);

  expect(screen.getByPlaceholderText("댓글을 작성하세요")).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("댓글 관리"));
  expect(screen.getByText("수정")).toBeInTheDocument();
  expect(screen.getByText("삭제")).toBeInTheDocument();
});

test.each([
  ["authenticated", { username: "other" }],
  ["unauthenticated", null],
  ["checking", null],
])("hides comment owner controls for %s non-owner state", (authStatus, user) => {
  render(<Comment {...commentProps} authStatus={authStatus} user={user} />);
  expect(screen.queryByLabelText("댓글 관리")).not.toBeInTheDocument();
  if (authStatus !== "authenticated") {
    expect(screen.queryByPlaceholderText("댓글을 작성하세요")).not.toBeInTheDocument();
  }
});
