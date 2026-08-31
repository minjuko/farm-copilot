import React from "react";
import styled from "styled-components";
import { formatSoilSampleLabel } from "./soilFlow";

const Field = styled.div`width: 100%; margin-bottom: 16px; display: flex; flex-direction: column;`;
const Label = styled.label`font-size: 16px; margin-bottom: 8px; color: #333;`;
const Select = styled.select`
  padding: 8px; margin-bottom: 16px; border: 1px solid #ccc; border-radius: 4px;
  width: 100%; max-width: 400px; box-sizing: border-box; font-size: 16px;
`;

const SoilSampleSelect = ({ disabled, onSelect, samples }) => {
  if (!samples.length) return null;
  return (
    <Field>
      <Label htmlFor="soil-sample">상세 주소 선택</Label>
      <Select id="soil-sample" onChange={(event) => onSelect(event.target.value)} defaultValue="" disabled={disabled}>
        <option value="" disabled>선택하세요</option>
        {samples.map((sample, index) => (
          <option key={`${sample.No ?? sample.PNU_Nm}-${index}`} value={index}>
            {formatSoilSampleLabel(sample)}
          </option>
        ))}
      </Select>
    </Field>
  );
};

export default SoilSampleSelect;
