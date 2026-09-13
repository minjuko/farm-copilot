import React from "react";
import { IoSearch } from "react-icons/io5";
import styled from "styled-components";
import { color, radius, space } from "../../../styles/theme";

const Field = styled.div`
  width: 100%;
  margin-bottom: ${space("lg")};
  display: flex;
  flex-direction: column;
`;
const Label = styled.label`
  margin-bottom: ${space("sm")}; color: ${color("text")}; font-size: 16px; font-weight: 600;
`;
const Row = styled.div`display: flex; gap: ${space("sm")}; width: 100%; align-items: center;`;
const Input = styled.input`
  padding: ${space("sm")}; border: 1px solid ${color("borderStrong")}; border-radius: ${radius("sm")};
  flex: 1; min-width: 0; height: 44px; box-sizing: border-box; font-size: 16px;
  &:focus { outline: 2px solid ${color("primary")}; outline-offset: 1px; }
`;
const Button = styled.button`
  min-width: 104px; height: 44px; padding: 0 ${space("md")}; display: flex; gap: 0.35rem;
  align-items: center; justify-content: center; font-weight: 600;
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
const Meta = styled.span`display: block; margin-top: 0.2rem; color: ${color("textMuted")}; font-size: 0.86rem;`;

const AddressSearch = ({
  address, disabled, isSearching, onChange, onSearch, onSelect, results,
}) => (
  <Field>
    <Label htmlFor="soil-address">주소</Label>
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
  </Field>
);

export default AddressSearch;
