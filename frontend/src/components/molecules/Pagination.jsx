import React from "react";
import ReactPaginate from "react-paginate";
import styled from "styled-components";
import { color, radius, space } from "../../styles/theme";

const Container = styled.nav`
  display: flex;
  justify-content: center;
  margin-top: ${space("lg")};

  .pagination { display: flex; list-style: none; padding: 0; }
  .pagination li { margin: 0 5px; }
  .pagination li a {
    padding: 8px 12px;
    border: 1px solid ${color("border")};
    border-radius: ${radius("sm")};
    cursor: pointer;
    color: ${color("primary")};
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
