import React from "react";
import { IoSearch } from "react-icons/io5";
import styled from "styled-components";

const Field = styled.div`
  width: 100%;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
`;
const Label = styled.label`font-size: 16px; margin-bottom: 8px; color: #333;`;
const Row = styled.div`display: flex; width: 100%; align-items: center;`;
const Input = styled.input`
  padding: 8px; border: 1px solid #ccc; border-radius: 4px;
  width: calc(100% - 110px); height: 40px; box-sizing: border-box; font-size: 16px;
`;
const Button = styled.button`
  margin-left: 10px; height: 40px; display: flex; align-items: center; justify-content: center;
  background: #4aaa87; color: white; border: 0; border-radius: 5px; cursor: pointer;
  &:hover { background: #3b8b6d; }
  &:disabled { cursor: not-allowed; opacity: 0.6; }
`;
const Results = styled.div`
  width: 100%; margin-top: 0.5rem; border: 1px solid #d8e2dc;
  border-radius: 6px; background: #fff; overflow: hidden;
`;
const Result = styled.button`
  display: block; width: 100%; padding: 0.75rem; border: 0;
  border-bottom: 1px solid #edf1ee; background: #fff; text-align: left; cursor: pointer;
  &:hover, &:focus { background: #eef8f3; }
  &:last-child { border-bottom: 0; }
`;
const Meta = styled.span`display: block; margin-top: 0.2rem; color: #6b7d75; font-size: 0.8rem;`;
const Help = styled.p`color: #7f8c8d; font-size: 0.875rem; margin-top: 0.5rem;`;

const AddressSearch = ({
  address, disabled, isSearching, onChange, onSearch, onSelect, results,
}) => (
  <Field>
    <Label htmlFor="soil-address">주소</Label>
    <Help>주소를 입력한 후 검색 버튼을 눌러주세요.</Help>
    <Row>
      <Input
        id="soil-address"
        value={address}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") { event.preventDefault(); onSearch(); }
        }}
        placeholder="도로명 또는 지번 주소를 입력하세요"
      />
      <Button type="button" onClick={onSearch} disabled={disabled}>
        {isSearching ? "검색 중" : "주소 검색"} <IoSearch aria-hidden="true" />
      </Button>
    </Row>
    {results.length > 0 && (
      <Results aria-label="주소 검색 결과">
        {results.map((result, index) => (
          <Result type="button" key={`${result.address_name}-${index}`} onClick={() => onSelect(result)}>
            {result.display_name}
            {result.road_address_name && result.address_name !== result.road_address_name && (
              <Meta>지번: {result.address_name}</Meta>
            )}
          </Result>
        ))}
      </Results>
    )}
    <Help>이전 행정구역 명칭은 자동으로 최신 명칭으로 검색합니다.</Help>
  </Field>
);

export default AddressSearch;
