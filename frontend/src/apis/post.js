import { instance } from "./client";

export const fetchPosts = (postType) => {
  return instance.get("/community/", {
    params: { post_type: postType },
  });
};

export const fetchPost = (postId) => {
  return instance.get(`/community/post/${postId}/`);
};

export const editPost = (postId, formData) => {
  return instance.post(`/community/post/${postId}/edit/`, formData);
};

export const createPost = (formData) => {
  return instance.post("/community/post/create/", formData);
};

export const fetchMyCommentedPosts = () => {
  return instance.get("/community/mycommentedposts/");
};

export const fetchMyPosts = () => {
  return instance.get("/community/myposts/");
};

export const deletePost = (postId) => {
  return instance.post(`/community/post/${postId}/delete/`);
};

export const createComment = (postId, commentData) => {
  return instance.post(`/community/post/${postId}/comment/create/`, commentData);
};

export const editComment = (commentId, commentData) => {
  return instance.post(`/community/comment/${commentId}/edit/`, commentData);
};

export const deleteComment = (commentId) => {
  return instance.post(`/community/comment/${commentId}/delete/`);
};
