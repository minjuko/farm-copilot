import styled from 'styled-components';
import { color, radius, shadow, space } from './theme';

export const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: ${space("lg")} 0 96px;
  min-height: 100vh;
  background: ${color("background")};
  position: relative;
  overflow: hidden;
`;

export const ContentContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
`;

export const Button = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1.25rem; 
  margin: 0 0 ${space("lg")};
  font-weight: 600;
  background-color: ${color("primary")};
  color: white;
  border: none;
  border-radius: ${radius("sm")};
  cursor: pointer;
  font-size: 1rem; 
  transition: background-color 0.3s;
  width: 9.375rem; 
  box-shadow: ${shadow("sm")};

  &:hover {
    background-color: ${color("primaryHover")};
  }

  svg {
    margin-right: 0.5rem;
  }
`;

export const SessionListContainer = styled.div`
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow-y: auto;
`;

export const SessionList = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12.5rem, 1fr)); 
  gap: ${space("md")};
  max-width: 60rem;
  width: calc(100% - 2.5rem);
  padding: 0;
  box-sizing: border-box;
  margin: 0 auto 1.25rem;

  @media (max-width: 768px) {
    grid-template-columns: repeat(auto-fill, minmax(11.25rem, 1fr)); 
  }

  @media (max-width: 480px) {
    grid-template-columns: 1fr;
    gap: ${space("sm")};
    width: calc(100% - 2rem);
  }
`;

export const SessionItem = styled.div`
  background-color: ${color("surface")};
  border-radius: ${radius("lg")};
  border: 1px solid ${color("borderStrong")};
  box-shadow: ${shadow("sm")};
  display: flex;
  flex-direction: column;
  align-items: flex-start; 
  justify-content: space-between;
  padding: 14px ${space("md")} 12px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  height: auto; 

  &:hover {
    transform: translateY(-0.125rem);
    box-shadow: ${shadow("md")};
  }

  &:active {
    transform: translateY(-0.125rem);
    box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.1); 
  }
`;

export const SessionName = styled.span`
  font-size: 1.125rem;
  font-weight: 600;
  color: ${color("text")};
  margin-bottom: 0.5rem; 
  word-break: break-word;
  text-align: center;

  @media (max-width: 480px) {
    font-size: 1rem; 
    margin-bottom: 0.375rem;
  }
`;

export const EditInput = styled.input`
  font-size: 1.25rem; 
  padding: 0.625rem; 
  margin-bottom: 0.5rem; 
  width: 80%;
  border: 2px solid #E0E0E0;
  border-radius: 0.625rem; 

  @media (max-width: 480px) {
    font-size: 1rem; 
    padding: 0.5rem;
    margin-bottom: 0.375rem; 
  }
`;

export const SessionDetails = styled.div`
  width: 100%;
  font-size: 0.98rem;
  line-height: 1.55;
  margin: 0;
  text-align: left;
  color: ${color("textMuted")};

  @media (max-width: 480px) {
    font-size: 0.93rem;
    margin-bottom: 0.375rem;
  }
`;

export const ButtonContainer = styled.div`
  display: flex;
  align-items: center;
  gap: ${space("sm")};
  justify-content: flex-end;
  width: 100%;
  margin-top: ${space("sm")};
  padding-top: ${space("sm")};
  border-top: 1px solid ${color("border")};

  @media (max-width: 480px) {
    margin-top: 0.375rem;
  }
`;

export const SaveButton = styled.button`
  background-color: ${color("primary")};
  color: white;
  border: none;
  border-radius: 0.3125rem; 
  padding: 0.5rem 0.875rem; 
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.3s;

  &:hover {
    background-color: ${color("primaryHover")};
  }

  @media (max-width: 480px) {
    padding: 0.375rem 0.625rem; 
    font-size: 0.875rem; 
  }
`;

export const DeleteButton = styled.button`
  background: none;
  border: none;
  color: ${color("danger")};
  cursor: pointer;
  font-size: 1rem; 

  &:hover {
    color: ${color("dangerHover")};
  }

  @media (max-width: 480px) {
    font-size: 0.875rem; 
  }
`;

export const EditButton = styled.button`
  background: none;
  border: none;
  color: ${color("primary")};
  cursor: pointer;
  font-size: 1rem; 

  &:hover {
    color: ${color("primaryHover")};
  }

  @media (max-width: 480px) {
    font-size: 0.875rem;
  }
`;

export const PaginationContainer = styled.div`
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 1.5rem;
  margin-bottom: 1.25rem; 

  .pagination {
    display: flex;
    list-style: none;
    padding: 0;
    margin: 0;

    @media (max-width: 480px) {
      flex-wrap: wrap;
      justify-content: center;
    }
  }

  .pagination li {
    margin: 0 0.3125rem; 

    @media (max-width: 480px) {
      margin: 0.3125rem; 
    }
  }

  .pagination li a {
    padding: 0.625rem 0.75rem; 
    border: 1px solid #ddd;
    border-radius: 0.3125rem; 
    cursor: pointer;
    color: #4aaa87;
    text-decoration: none;
    transition: background-color 0.3s, color 0.3s;

    @media (max-width: 480px) {
      padding: 0.375rem 0.625rem; 
      font-size: 0.875rem; 
    }
  }

  .pagination li a:hover {
    background-color: #f5f5f5;
    color: #3e8e75;
  }

  .pagination li.active a {
    background-color: #4aaa87;
    color: white;
    border: none;
  }

  .pagination li.previous a,
  .pagination li.next a {
    color: #888;
  }

  .pagination li.disabled a {
    color: #ccc;
    cursor: not-allowed;
  }
`;

export const EmptyMessage = styled.div`
  text-align: center;
  color: ${color("textMuted")};
  font-size: 1rem;
  margin: 2rem;
`;

export const SessionHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: ${space("sm")};
  width: 100%;
`;

export const ResultHint = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  color: ${color("primaryHover")};
  font-size: 0.88rem;
  font-weight: 700;
  line-height: 1.4;
`;
