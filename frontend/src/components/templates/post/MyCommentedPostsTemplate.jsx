import React, { useCallback, useState } from "react";
import styled from "styled-components";
import { Link } from "react-router-dom";
import Pagination from "../../molecules/Pagination";
import { fetchMyCommentedPosts } from "../../../apis/post";
import { useLoading } from "../../../LoadingContext";
import GlobalLoader from "../../atoms/GlobalLoader";
import useAsyncResource from "../../../hooks/useAsyncResource";
import { EmptyState, ListPage } from "../../../styles/primitives";
import { color, radius, shadow } from "../../../styles/theme";

const getMyCommentedPostsError = () => (
  "댓글을 작성한 게시글을 불러오지 못했습니다."
);

const PostList = styled.div`
  display: grid;
  gap: 1rem;
  margin-top: 32px;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  background-color: ${color("surface")};
  box-shadow: ${shadow("sm")};
  border-radius: ${radius("md")};
  overflow: hidden;
`;

const TableHeader = styled.thead`
  background-color: ${color("primary")};
  color: ${color("surface")};
`;

const TableRow = styled.tr`
  &:nth-child(even) {
    background-color: ${color("background")};
  }
`;

const TableCell = styled.td`
  padding: 12px;
  border-bottom: 1px solid ${color("borderStrong")};
  font-size: 14px;
  color: ${(props) => (props.$header ? "aliceblue" : "black")};
  text-align: left;
`;

const StyledLink = styled(Link)`
  text-decoration: none;
  color: inherit;
`;

const PostTitle = styled.span`
  font-size: 14px;
  font-weight: bold;
  color: ${color("primary")};
  display: inline-block;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const MyCommentedPostsTemplate = () => {
  const { isLoading } = useLoading();
  const [currentPage, setCurrentPage] = useState(0);
  const loadPosts = useCallback(async () => {
    const response = await fetchMyCommentedPosts();
    if (!Array.isArray(response?.data)) throw new Error("MALFORMED_MY_COMMENTED_POSTS");
    return [...response.data].sort((a, b) => new Date(b.creation_date) - new Date(a.creation_date));
  }, []);
  const { data: posts, error: loadError } = useAsyncResource(loadPosts, {
    getError: getMyCommentedPostsError,
    initialData: [],
  });
  const postsPerPage = 5;
  const pageCount = Math.ceil(posts.length / postsPerPage);
  const offset = currentPage * postsPerPage;

  const handlePageClick = ({ selected }) => {
    setCurrentPage(selected);
  };

  return (
    <ListPage>
      <GlobalLoader isLoading={isLoading} />
      {loadError && <p role="alert">{loadError}</p>}
      <PostList>
        {posts.length === 0 && !loadError ? <EmptyState>댓글을 작성한 게시글이 없습니다.</EmptyState> : <Table>
          <TableHeader>
            <TableRow>
              <TableCell $header>제목</TableCell>
              <TableCell $header>작성자</TableCell>
              <TableCell $header>작성일</TableCell>
            </TableRow>
          </TableHeader>
          <tbody>
            {posts.slice(offset, offset + postsPerPage).map((post) => (
              <TableRow key={post.id}>
                <TableCell>
                  <StyledLink to={`/post/${post.id}`}>
                    <PostTitle>{post.title}</PostTitle>
                  </StyledLink>
                </TableCell>
                <TableCell>{post.user__username}</TableCell>
                <TableCell>{new Date(post.creation_date).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
          </tbody>
        </Table>}
      </PostList>
      <Pagination currentPage={currentPage} pageCount={pageCount} onPageChange={handlePageClick} />
    </ListPage>
  );
};

export default MyCommentedPostsTemplate;
