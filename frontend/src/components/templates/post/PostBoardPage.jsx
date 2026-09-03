import React, { useCallback, useMemo, useState } from "react";
import { FaPen } from "react-icons/fa";
import { Link } from "react-router-dom";
import styled from "styled-components";
import { useAuth } from "../../../AuthContext";
import { fetchPosts } from "../../../apis/post";
import { getApiErrorMessage } from "../../../apis/error";
import useAsyncResource from "../../../hooks/useAsyncResource";
import { Inline, PageContainer, StatusMessage } from "../../../styles/primitives";
import { color, radius, shadow, space } from "../../../styles/theme";
import Pagination from "../../molecules/Pagination";

const POSTS_PER_PAGE = 5;

const Heading = styled.h1`font-size: 1.25rem; color: ${color("text")}; align-self: flex-start; margin: ${space("md")};`;
const Toolbar = styled(Inline)`
  width: 100%; margin: 20px 0; padding: ${space("md")};
`;
const SearchInput = styled.input`
  font-size: 14px; border: 2px solid ${color("primary")}; padding: ${space("sm")};
  border-radius: ${radius("lg")}; flex: 1; box-shadow: ${shadow("sm")};
  &:focus { outline: none; border-color: ${color("primaryFocus")}; }
`;
const CreateButton = styled(Link)`
  display: flex; align-items: center; justify-content: center; padding: ${space("sm")} ${space("md")};
  font-size: 14px; color: ${color("surface")}; background: ${color("primary")}; border-radius: ${radius("md")};
  text-decoration: none;
  &:hover { background: ${color("primaryFocus")}; }
`;
const Table = styled.table`
  width: 100%; border-collapse: collapse; background: ${color("surface")};
  box-shadow: ${shadow("sm")}; border-radius: ${radius("md")}; overflow: hidden;
`;
const Header = styled.thead`background: ${color("primary")}; color: ${color("surface")};`;
const Row = styled.tr`&:nth-child(even) { background: ${color("background")}; }`;
const HeaderCell = styled.th`padding: ${space("sm")}; border-bottom: 1px solid ${color("borderStrong")}; font-size: 14px; text-align: left;`;
const Cell = styled.td`padding: ${space("sm")}; border-bottom: 1px solid ${color("borderStrong")}; font-size: 14px; text-align: left;`;
const PostLink = styled(Link)`text-decoration: none; color: inherit;`;
const PostTitle = styled.span`
  font-size: 14px; font-weight: bold; color: ${color("primary")}; display: inline-block;
  max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
`;
const CommentCount = styled.span`font-size: 14px; color: ${color("textMuted")}; margin-left: ${space("sm")};`;
const getPostLoadError = (error) => getApiErrorMessage(
  error,
  "게시글을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
);

const PostBoardPage = ({ boardLabel, postType }) => {
  const { status: authStatus } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const loadPosts = useCallback(async () => {
    const response = await fetchPosts(postType);
    if (!Array.isArray(response?.data)) throw new Error("MALFORMED_POST_LIST");
    return [...response.data].sort(
      (a, b) => new Date(b.creation_date) - new Date(a.creation_date)
    );
  }, [postType]);
  const { data: posts, error } = useAsyncResource(loadPosts, {
    getError: getPostLoadError,
    initialData: [],
  });

  const filteredPosts = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    if (!normalizedSearch) return posts;
    return posts.filter((post) => String(post.title || "").toLowerCase().includes(normalizedSearch));
  }, [posts, searchTerm]);
  const pageCount = Math.ceil(filteredPosts.length / POSTS_PER_PAGE);
  const visiblePosts = filteredPosts.slice(currentPage * POSTS_PER_PAGE, (currentPage + 1) * POSTS_PER_PAGE);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(0);
  };

  return (
    <PageContainer>
      <Heading>{boardLabel}</Heading>
      <Toolbar>
        <SearchInput
          aria-label={`${boardLabel} 제목 검색`}
          type="search"
          placeholder="제목을 검색하세요"
          value={searchTerm}
          onChange={handleSearchChange}
        />
        {authStatus === "authenticated" && (
          <CreateButton to={`/post/create?post_type=${postType}`}>
            <FaPen aria-hidden="true" style={{ marginRight: 8 }} />글 작성
          </CreateButton>
        )}
      </Toolbar>
      {error ? <StatusMessage $error role="alert">{error}</StatusMessage> : visiblePosts.length === 0 ? (
        <StatusMessage>{searchTerm ? "검색 결과가 없습니다." : "등록된 게시글이 없습니다."}</StatusMessage>
      ) : (
        <Table>
          <Header><Row><HeaderCell>제목</HeaderCell><HeaderCell>작성자</HeaderCell><HeaderCell>작성일</HeaderCell></Row></Header>
          <tbody>
            {visiblePosts.map((post) => (
              <Row key={post.id}>
                <Cell><PostLink to={`/post/${post.id}`}><PostTitle>{post.title}</PostTitle><CommentCount>({post.comment_count || 0})</CommentCount></PostLink></Cell>
                <Cell>{post.user__username}</Cell>
                <Cell>{new Date(post.creation_date).toLocaleDateString()}</Cell>
              </Row>
            ))}
          </tbody>
        </Table>
      )}
      <Pagination
        ariaLabel={`${boardLabel} 페이지 탐색`}
        currentPage={currentPage}
        onPageChange={({ selected }) => setCurrentPage(selected)}
        pageCount={pageCount}
      />
    </PageContainer>
  );
};

export default PostBoardPage;
