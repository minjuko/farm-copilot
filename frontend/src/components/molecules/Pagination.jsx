import React from "react";
import ReactPaginate from "react-paginate";
import styled from "styled-components";

const Container = styled.nav`
  display: flex;
  justify-content: center;
  margin-top: 24px;

  .pagination { display: flex; list-style: none; padding: 0; }
  .pagination li { margin: 0 5px; }
  .pagination li a {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
    color: #4aaa87;
    text-decoration: none;
  }
  .pagination li a:hover { background: #f5f5f5; color: #3e8e75; }
  .pagination li.active a { background: #4aaa87; color: white; border-color: #4aaa87; }
  .pagination li.previous a, .pagination li.next a { color: #888; }
  .pagination li.disabled a { color: #ccc; cursor: not-allowed; }
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
