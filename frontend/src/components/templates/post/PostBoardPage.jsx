import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FaCheck, FaHandsHelping, FaListUl, FaPen, FaShoppingCart, FaStore } from "react-icons/fa";
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
const BOARD_OPTIONS = [
  { type: "sell", label: "판매 게시판", description: "농산물과 농기구를 판매해보세요", to: "/sell-board", icon: FaStore },
  { type: "buy", label: "구매 게시판", description: "필요한 농산물과 농기구를 찾아보세요", to: "/buy-board", icon: FaShoppingCart },
  { type: "exchange", label: "품앗이 게시판", description: "이웃 농부와 일손과 경험을 나눠보세요", to: "/exchange-board", icon: FaHandsHelping },
];

const HeadingRow = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${space("md")};
  width: 100%;
  padding: ${space("md")} ${space("lg")};
  box-sizing: border-box;
  background: linear-gradient(135deg, #e8f5ef 0%, #f8fbf9 100%);
  border: 1px solid ${color("borderStrong")};
  border-radius: ${radius("lg")};
  box-shadow: ${shadow("sm")};
`;
const BoardIdentity = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
`;
const BoardIcon = styled.span`
  display: grid;
  place-items: center;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  color: ${color("surface")};
  background: ${color("primary")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("sm")};
`;
const BoardTitleText = styled.div`min-width: 0;`;
const Heading = styled.h1`
  margin: 0;
  color: ${color("text")};
  font-size: 1.25rem;
`;
const BoardDescription = styled.p`
  margin: 3px 0 0;
  color: ${color("textMuted")};
  font-size: 0.88rem;
  line-height: 1.35;

  @media (max-width: 480px) { display: none; }
`;
const BoardSwitcher = styled.div`position: relative;`;
const SwitcherButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: ${space("sm")};
  padding: 9px 12px;
  color: ${color("primaryHover")};
  background: ${color("surface")};
  border: 1px solid ${color("borderStrong")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("sm")};
  font-size: 0.94rem;
  font-weight: 700;
  cursor: pointer;
`;
const BoardMenu = styled.nav`
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 20;
  width: 190px;
  padding: ${space("sm")};
  background: ${color("surface")};
  border: 1px solid ${color("borderStrong")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("md")};
`;
const BoardMenuItem = styled(Link)`
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  padding: 0 12px;
  color: ${({ $active, theme }) => $active
    ? theme?.colors?.primaryHover || "#3b8b6d"
    : theme?.colors?.text || "#263a32"};
  background: ${({ $active, theme }) => $active
    ? theme?.colors?.primarySoft || "#e8f5e9"
    : "transparent"};
  border-radius: ${radius("sm")};
  font-size: 0.95rem;
  font-weight: ${({ $active }) => ($active ? 700 : 500)};
  text-decoration: none;

  &:hover { background: ${color("surfaceHover")}; }
`;
const Toolbar = styled(Inline)`
  width: 100%; margin: ${space("md")} 0; padding: 0;
`;
const SearchInput = styled.input`
  min-width: 0; height: 42px; box-sizing: border-box;
  font-size: 15px; border: 1px solid ${color("borderStrong")}; padding: ${space("sm")} 12px;
  border-radius: ${radius("lg")}; flex: 1; box-shadow: ${shadow("sm")};
  &:focus { outline: none; border-color: ${color("primary")}; box-shadow: 0 0 0 3px rgba(74, 170, 135, 0.14); }
`;
const CreateButton = styled(Link)`
  display: flex; align-items: center; justify-content: center; height: 42px; box-sizing: border-box;
  padding: ${space("sm")} ${space("md")}; font-size: 15px; font-weight: 700;
  color: ${color("surface")}; background: ${color("primary")}; border-radius: ${radius("md")};
  box-shadow: ${shadow("sm")};
  text-decoration: none;
  &:hover { background: ${color("primaryFocus")}; }
`;
const Table = styled.table`
  width: 100%; border-collapse: separate; border-spacing: 0; background: ${color("surface")};
  border: 1px solid ${color("borderStrong")};
  box-shadow: ${shadow("sm")}; border-radius: ${radius("md")}; overflow: hidden;
`;
const Header = styled.thead`background: ${color("primary")}; color: ${color("surface")};`;
const Row = styled.tr`
  &:nth-child(even) { background: ${color("background")}; }
  &:hover { background: ${color("surfaceHover")}; }
  &:last-child td { border-bottom: 0; }
`;
const HeaderCell = styled.th`padding: 9px ${space("sm")}; border-bottom: 1px solid ${color("borderStrong")}; font-size: 15px; text-align: left;`;
const Cell = styled.td`padding: 10px ${space("sm")}; border-bottom: 1px solid ${color("border")}; font-size: 15px; text-align: left; vertical-align: middle;`;
const PostLink = styled(Link)`
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  color: inherit;
  line-height: 1.4;
  text-decoration: none;
`;
const PostTitle = styled.span`
  display: block; font-size: 15px; font-weight: 700; line-height: inherit; color: #202522;
  max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
`;
const CommentCount = styled.span`
  flex-shrink: 0;
  margin-left: ${space("sm")};
  color: ${color("textMuted")};
  font-size: 15px;
  line-height: inherit;
`;
const getPostLoadError = (error) => getApiErrorMessage(
  error,
  "게시글을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
);

const PostBoardPage = ({ boardLabel, postType }) => {
  const { status: authStatus } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [isBoardMenuOpen, setIsBoardMenuOpen] = useState(false);
  const boardSwitcherRef = useRef(null);
  const activeBoard = BOARD_OPTIONS.find((board) => board.type === postType) || BOARD_OPTIONS[0];
  const ActiveBoardIcon = activeBoard.icon;

  useEffect(() => {
    if (!isBoardMenuOpen) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!boardSwitcherRef.current?.contains(event.target)) setIsBoardMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setIsBoardMenuOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [isBoardMenuOpen]);
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
      <HeadingRow>
        <BoardIdentity>
          <BoardIcon><ActiveBoardIcon aria-hidden="true" /></BoardIcon>
          <BoardTitleText>
            <Heading>{boardLabel}</Heading>
            <BoardDescription>{activeBoard.description}</BoardDescription>
          </BoardTitleText>
        </BoardIdentity>
        <BoardSwitcher ref={boardSwitcherRef}>
          <SwitcherButton
            type="button"
            aria-haspopup="menu"
            aria-expanded={isBoardMenuOpen}
            onClick={() => setIsBoardMenuOpen((open) => !open)}
          >
            <FaListUl aria-hidden="true" /> 게시판 선택
          </SwitcherButton>
          {isBoardMenuOpen && (
            <BoardMenu aria-label="게시판 선택">
              {BOARD_OPTIONS.map((board) => (
                <BoardMenuItem
                  key={board.type}
                  to={board.to}
                  $active={postType === board.type}
                  aria-current={postType === board.type ? "page" : undefined}
                  onClick={() => setIsBoardMenuOpen(false)}
                >
                  {board.label}
                  {postType === board.type && <FaCheck aria-hidden="true" />}
                </BoardMenuItem>
              ))}
            </BoardMenu>
          )}
        </BoardSwitcher>
      </HeadingRow>
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
