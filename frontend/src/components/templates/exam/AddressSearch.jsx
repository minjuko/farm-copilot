import React from "react";
import { IoSearch } from "react-icons/io5";
import styled from "styled-components";
import { color, radius, space } from "../../../styles/theme";

const Field = styled.div`
  width: 100%;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
`;
const Label = styled.label`font-size: 16px; margin-bottom: ${space("sm")}; color: ${color("text")};`;
const Row = styled.div`display: flex; width: 100%; align-items: center;`;
const Input = styled.input`
  padding: ${space("sm")}; border: 1px solid ${color("borderStrong")}; border-radius: ${radius("sm")};
  width: calc(100% - 110px); height: 40px; box-sizing: border-box; font-size: 16px;
`;
const Button = styled.button`
  margin-left: 10px; height: 40px; display: flex; align-items: center; justify-content: center;
  background: ${color("primary")}; color: ${color("surface")}; border: 0; border-radius: ${radius("sm")}; cursor: pointer;
  &:hover { background: ${color("primaryHover")}; }
  &:disabled { cursor: not-allowed; opacity: 0.6; }
`;
const Results = styled.div`
  width: 100%; margin-top: 0.5rem; border: 1px solid #d8e2dc;
  border-radius: ${radius("md")}; background: ${color("surface")}; overflow: hidden;
`;
const Result = styled.button`
  display: block; width: 100%; padding: 0.75rem; border: 0;
  border-bottom: 1px solid ${color("border")}; background: ${color("surface")}; text-align: left; cursor: pointer;
  &:hover, &:focus { background: #eef8f3; }
  &:last-child { border-bottom: 0; }
`;
const Meta = styled.span`display: block; margin-top: 0.2rem; color: ${color("textMuted")}; font-size: 0.8rem;`;
const Help = styled.p`color: ${color("textMuted")}; font-size: 0.875rem; margin-top: ${space("sm")};`;

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
        {results.map((addressResult, index) => (
          <Result type="button" key={`${addressResult.address_name}-${index}`} onClick={() => onSelect(addressResult)}>
            {addressResult.display_name}
            {addressResult.road_address_name && addressResult.address_name !== addressResult.road_address_name && (
              <Meta>지번: {addressResult.address_name}</Meta>
            )}
          </Result>
        ))}
      </Results>
    )}
    <Help>이전 행정구역 명칭은 자동으로 최신 명칭으로 검색합니다.</Help>
  </Field>
);

export default AddressSearch;
