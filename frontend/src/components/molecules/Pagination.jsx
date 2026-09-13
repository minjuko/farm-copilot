import React from "react";
import ReactPaginate from "react-paginate";
import styled from "styled-components";
import { color, radius } from "../../styles/theme";

const Container = styled.nav`
  display: flex;
  justify-content: center;
  margin-top: 18px;

  .pagination { display: flex; align-items: center; list-style: none; padding: 0; margin: 0; }
  .pagination li { margin: 0 3px; }
  .pagination li a {
    display: grid;
    place-items: center;
    min-width: 34px;
    height: 34px;
    padding: 0 8px;
    box-sizing: border-box;
    border: 1px solid ${color("border")};
    border-radius: ${radius("sm")};
    cursor: pointer;
    color: ${color("primary")};
    font-size: 0.88rem;
    line-height: 1;
    text-decoration: none;
  }
  .pagination li a:hover { background: ${color("surfaceHover")}; color: ${color("primaryHover")}; }
  .pagination li.active a { background: ${color("primary")}; color: ${color("surface")}; border-color: ${color("primary")}; }
  .pagination li.previous a, .pagination li.next a { color: ${color("textMuted")}; }
  .pagination li.disabled a { color: ${color("disabled")}; cursor: not-allowed; }
`;

const Pagination = ({ currentPage, onPageChange, pageCount, ariaLabel = "페이지 탐색" }) => {
  if (pageCount <= 1) return null;

  return (
    <Container aria-label={ariaLabel}>
      <ReactPaginate
        previousLabel="이전"
        nextLabel="다음"
        breakLabel="..."
        pageCount={pageCount}
        forcePage={Math.min(currentPage, pageCount - 1)}
        marginPagesDisplayed={2}
        pageRangeDisplayed={5}
        onPageChange={onPageChange}
        containerClassName="pagination"
        activeClassName="active"
        previousClassName="previous"
        nextClassName="next"
        disabledClassName="disabled"
      />
    </Container>
  );
};

export default Pagination;
