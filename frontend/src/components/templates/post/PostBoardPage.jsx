import React, { useEffect, useMemo, useState } from "react";
import { FaPen } from "react-icons/fa";
import { Link } from "react-router-dom";
import styled from "styled-components";
import { useAuth } from "../../../AuthContext";
import { fetchPosts } from "../../../apis/post";
import { getApiErrorMessage } from "../../../apis/error";
import { useLoading } from "../../../LoadingContext";
import Pagination from "../../molecules/Pagination";

const POSTS_PER_PAGE = 5;

const Container = styled.div`
  display: flex; flex-direction: column; align-items: center;
  padding: 16px; max-width: 75rem; width: 100%; margin: 0 auto;
`;
const Heading = styled.h1`font-size: 1.25rem; color: #333; align-self: flex-start; margin: 1rem;`;
const Toolbar = styled.div`
  display: flex; align-items: center; width: 100%; margin: 20px 0; padding: 16px;
`;
const SearchInput = styled.input`
  font-size: 14px; border: 2px solid #4aaa87; padding: 8px;
  border-radius: 12px; flex: 1; box-shadow: 0 2px 4px rgba(0,0,0,.1);
  &:focus { outline: none; border-color: #6dc4b0; }
`;
const CreateButton = styled(Link)`
  display: flex; align-items: center; justify-content: center; padding: 8px 16px;
  font-size: 14px; color: white; background: #4aaa87; border-radius: 8px;
  text-decoration: none; margin-left: 8px;
  &:hover { background: #6dc4b0; }
`;
const Table = styled.table`
  width: 100%; border-collapse: collapse; background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,.05); border-radius: 8px; overflow: hidden;
`;
const Header = styled.thead`background: #4aaa87; color: white;`;
const Row = styled.tr`&:nth-child(even) { background: #f9f9f9; }`;
const HeaderCell = styled.th`padding: 8px; border-bottom: 1px solid #ccc; font-size: 14px; text-align: left;`;
const Cell = styled.td`padding: 8px; border-bottom: 1px solid #ccc; font-size: 14px; text-align: left;`;
const PostLink = styled(Link)`text-decoration: none; color: inherit;`;
const PostTitle = styled.span`
  font-size: 14px; font-weight: bold; color: #4aaa87; display: inline-block;
  max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
`;
const CommentCount = styled.span`font-size: 14px; color: gray; margin-left: 8px;`;
const Status = styled.p`width: 100%; padding: 2rem 1rem; text-align: center; color: #666;`;

const PostBoardPage = ({ boardLabel, postType }) => {
  const { status: authStatus } = useAuth();
  const { setIsLoading } = useLoading();
  const [posts, setPosts] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const loadPosts = async () => {
      setIsLoading(true);
      try {
        const response = await fetchPosts(postType);
        if (!Array.isArray(response?.data)) throw new Error("MALFORMED_POST_LIST");
        const sortedPosts = [...response.data].sort(
          (a, b) => new Date(b.creation_date) - new Date(a.creation_date)
        );
        if (active) { setPosts(sortedPosts); setError(""); }
      } catch (requestError) {
        if (active) {
          setPosts([]);
          setError(getApiErrorMessage(requestError, "게시글을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."));
        }
      } finally {
        setIsLoading(false);
      }
    };
    loadPosts();
    return () => { active = false; };
  }, [postType, setIsLoading]);

  const filteredPosts = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    if (!normalizedSearch) return posts;
    return posts.filter((post) => String(post.title || "").toLowerCase().includes(normalizedSearch));
  }, [posts, searchTerm]);
  const pageCount = Math.ceil(filteredPosts.length / POSTS_PER_PAGE);
  const visiblePosts = filteredPosts.slice(currentPage * POSTS_PER_PAGE, (currentPage + 1) * POSTS_PER_PAGE);

  const changeSearch = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(0);
  };

  return (
    <Container>
      <Heading>{boardLabel}</Heading>
      <Toolbar>
        <SearchInput
          aria-label={`${boardLabel} 제목 검색`}
          type="search"
          placeholder="제목을 검색하세요"
          value={searchTerm}
          onChange={changeSearch}
        />
        {authStatus === "authenticated" && (
          <CreateButton to={`/post/create?post_type=${postType}`}>
            <FaPen aria-hidden="true" style={{ marginRight: 8 }} />글 작성
          </CreateButton>
        )}
      </Toolbar>
      {error ? <Status role="alert">{error}</Status> : visiblePosts.length === 0 ? (
        <Status>{searchTerm ? "검색 결과가 없습니다." : "등록된 게시글이 없습니다."}</Status>
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
    </Container>
  );
};

export default PostBoardPage;
