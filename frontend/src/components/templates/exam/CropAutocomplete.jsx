import React, { useEffect, useMemo, useRef, useState } from "react";
import styled from "styled-components";

const Field = styled.div`
  position: relative;
  width: 100%;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  font-size: 16px;
  margin-bottom: 8px;
  color: #333;
  align-self: flex-start;
`;

const Input = styled.input`
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: 100%;
  height: 40px;
  box-sizing: border-box;
  font-size: 16px;
`;

const List = styled.div`
  width: 100%;
  max-width: 400px;
  max-height: 200px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  z-index: 1;
`;

const Item = styled.button`
  display: block;
  padding: 8px;
  width: 100%;
  border: 0;
  border-bottom: 1px solid #ccc;
  background: #fff;
  text-align: center;
  cursor: pointer;
  &:hover, &:focus { background-color: #f1f1f1; }
  &:last-child { border-bottom: 0; }
`;

const CropAutocomplete = ({ cropName, cropNames, onChange, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const filteredCrops = useMemo(
    () => cropNames.filter((crop) => crop.toLowerCase().includes(cropName.toLowerCase())),
    [cropName, cropNames]
  );

  useEffect(() => {
    const closeOnOutsideClick = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, []);

  return (
    <Field ref={containerRef}>
      <Label htmlFor="soil-crop-name">작물 이름</Label>
      <Input
        id="soil-crop-name"
        type="text"
        value={cropName}
        onChange={(event) => { onChange(event.target.value); setIsOpen(true); }}
        onClick={() => setIsOpen(true)}
        placeholder="작물 이름을 검색하세요"
        autoComplete="off"
      />
      {isOpen && filteredCrops.length > 0 && (
        <List role="listbox" aria-label="작물 검색 결과">
          {filteredCrops.map((crop) => (
            <Item
              type="button"
              role="option"
              aria-selected={crop === cropName}
              key={crop}
              onClick={() => { onSelect(crop); setIsOpen(false); }}
            >
              {crop}
            </Item>
          ))}
        </List>
      )}
    </Field>
  );
};

export default CropAutocomplete;
