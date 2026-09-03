import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  fetchPost,
  createComment,
  editComment,
  deleteComment,
  deletePost,
} from "../../../apis/post";
import PostDetails from "../../molecules/PostDetail";
import Comments from "../../molecules/Comment";
import { useLoading } from "../../../LoadingContext";
import {
  Container,
} from "../../../styles/postStyles";
import { useAuth } from "../../../AuthContext";
import { isCommunityOwner } from "./communityOwnership";
import { getApiErrorMessage } from "../../../apis/error";

const PostDetailTemplate = () => {
  const { id } = useParams();
  const { setIsLoading } = useLoading();
  const { status: authStatus, user } = useAuth();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [replyCommentId, setReplyCommentId] = useState(null);
  const [newReply, setNewReply] = useState("");
  const [editCommentId, setEditCommentId] = useState(null);
  const [editCommentContent, setEditCommentContent] = useState("");
  const [showSettingsMenu, setShowSettingsMenu] = useState({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const settingsMenuRefs = useRef([]);

  const loadPost = useCallback(async () => {
    try {
      setErrorMessage("");
      setIsLoading(true);
      const response = await fetchPost(id);
      setPost(response.data);
      setComments(response.data.comments || []);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "게시글을 불러오지 못했습니다."));
    } finally {
      setIsLoading(false);
    }
  }, [id, setIsLoading]);

  useEffect(() => {
    loadPost();
  }, [loadPost]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      settingsMenuRefs.current.forEach((ref, index) => {
        if (ref && !ref.contains(event.target)) {
          setShowSettingsMenu((prev) => ({
            ...prev,
            [index]: false,
          }));
        }
      });
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleCommentChange = (event) => {
    setNewComment(event.target.value);
  };

  const handleEditCommentChange = (event) => {
    setEditCommentContent(event.target.value);
  };

  const handleReplyChange = (event) => {
    setNewReply(event.target.value);
  };

  const handleSubmitComment = async (event) => {
    event.preventDefault();
    try {
      await createComment(id, { content: newComment });
      await loadPost();
      setNewComment("");
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "댓글 작성에 실패했습니다."));
    }
  };

  const handleSubmitReply = async (event) => {
    event.preventDefault();
    try {
      await createComment(id, { content: newReply, parent_id: replyCommentId });
      await loadPost();
      setNewReply("");
      setReplyCommentId(null);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "답글 작성에 실패했습니다."));
    }
  };

  const handleEditComment = async (commentId) => {
    try {
      await editComment(commentId, { content: editCommentContent });
      const updatedComments = comments.map((comment) =>
        comment.id === commentId
          ? { ...comment, content: editCommentContent }
          : comment
      );
      setComments(updatedComments);
      setEditCommentId(null);
      setEditCommentContent("");
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "댓글 수정에 실패했습니다."));
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await deleteComment(commentId);
      setComments(comments.filter((comment) => comment.id !== commentId));
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "댓글 삭제에 실패했습니다."));
    }
  };

  const handleDeletePost = async () => {
    try {
      await deletePost(id);
      if (post.post_type === "sell") {
        navigate("/sell-board");
      }
      if (post.post_type === "buy") {
        navigate("/buy-board");
      }
      if (post.post_type === "exchange") {
        navigate("/exchange-board");
      }
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "게시글 삭제에 실패했습니다."));
    }
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleSettingsClick = (index) => {
    setShowSettingsMenu((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  if (!post) {
    return <Container>{errorMessage || "게시글을 불러오는 중입니다..."}</Container>;
  }

  return (
    <Container>
      {errorMessage && <p role="alert">{errorMessage}</p>}
      <PostDetails
        post={post}
        canManagePost={isCommunityOwner(authStatus, user, post)}
        showSettingsMenu={showSettingsMenu}
        settingsMenuRefs={settingsMenuRefs}
        openModal={handleOpenModal}
        handleSettingsClick={handleSettingsClick}
        isModalOpen={isModalOpen}
        closeModal={handleCloseModal}
        handleDeletePost={handleDeletePost}
      />
      <Comments
        comments={comments}
        newComment={newComment}
        newReply={newReply}
        replyCommentId={replyCommentId}
        editCommentId={editCommentId}
        editCommentContent={editCommentContent}
        handleCommentChange={handleCommentChange}
        handleEditCommentChange={handleEditCommentChange}
        handleReplyChange={handleReplyChange}
        handleSubmitComment={handleSubmitComment}
        handleSubmitReply={handleSubmitReply}
        handleEditComment={handleEditComment}
        handleDeleteComment={handleDeleteComment}
        setReplyCommentId={setReplyCommentId}
        authStatus={authStatus}
        user={user}
        setEditCommentId={setEditCommentId}
        setEditCommentContent={setEditCommentContent}
        setShowSettingsMenu={setShowSettingsMenu}
      />
    </Container>
  );
};

export default PostDetailTemplate;
