import React from "react";
import BoardTemplate from "../components/templates/post/BoardTemplate";
import BuyBoardTemplate from "../components/templates/post/BuyBoardTemplate";
import EditPostTemplate from "../components/templates/post/EditPostTemplate";
import ExchangeBoardTemplate from "../components/templates/post/ExchangeBoardTemplate";
import MyCommentedPostsTemplate from "../components/templates/post/MyCommentedPostsTemplate";
import MyPostTemplate from "../components/templates/post/MyPostTemplate";
import PostDetailTemplate from "../components/templates/post/PostDetailTemplate";
import SellBoardTemplate from "../components/templates/post/SellBoardTemplate";
import WritePostTemplate from "../components/templates/post/WritePostTemplate";

export const publicCommunityRoutes = [
  { path: "/board", element: <BoardTemplate /> },
  { path: "/buy-board", element: <BuyBoardTemplate /> },
  { path: "/sell-board", element: <SellBoardTemplate /> },
  { path: "/exchange-board", element: <ExchangeBoardTemplate /> },
  { path: "/post/:id", element: <PostDetailTemplate /> },
];

export const protectedCommunityRoutes = [
  { path: "/my-posts", element: <MyPostTemplate /> },
  { path: "/my-commented-posts", element: <MyCommentedPostsTemplate /> },
  { path: "/post/create", element: <WritePostTemplate /> },
  { path: "/post/edit/:id", element: <EditPostTemplate /> },
];
