import React from "react";
import styled from "styled-components";
import { color, radius, space } from "../../../styles/theme";
import { formatSoilSampleLabel } from "./soilFlow";

const Field = styled.div`width: 100%; display: flex; flex-direction: column;`;
const Label = styled.label`
  margin-bottom: ${space("sm")}; color: ${color("text")}; font-size: 16px; font-weight: 600;
`;
const Select = styled.select`
  width: 100%; height: 44px; padding: ${space("sm")}; box-sizing: border-box;
  border: 1px solid ${color("borderStrong")}; border-radius: ${radius("sm")};
  background: ${color("surface")}; color: ${color("text")}; font-size: 16px;
  &:focus { outline: 2px solid ${color("primary")}; outline-offset: 1px; }
  &:disabled, &[aria-disabled="true"] {
    background: ${color("surfaceHover")}; color: ${color("textMuted")};
  }
`;
const Guidance = styled.p`
  margin: ${space("xs")} 0 0;
  color: ${color("textMuted")};
  font-size: 0.88rem;
  line-height: 1.4;
`;

const SoilSampleSelect = ({ disabled, guidance, onSelect, samples, selectedSample }) => {
  const selectedIndex = selectedSample ? samples.indexOf(selectedSample) : -1;
  return (
    <Field>
      <Label htmlFor="soil-sample">상세 주소 선택</Label>
      <Select
        id="soil-sample"
        onChange={(event) => onSelect(event.target.value)}
        value={selectedIndex >= 0 ? String(selectedIndex) : ""}
        disabled={disabled || !samples.length}
      >
        {!samples.length && <option value="" disabled>주소를 검색하면 상세 주소가 표시됩니다</option>}
        <option value="" disabled>선택하세요</option>
        {samples.map((sample, index) => (
          <option key={`${sample.No ?? sample.PNU_Nm}-${index}`} value={index}>
            {formatSoilSampleLabel(sample)}
          </option>
        ))}
      </Select>
      {!samples.length && guidance && <Guidance role="status">{guidance}</Guidance>}
    </Field>
  );
};

export default SoilSampleSelect;
