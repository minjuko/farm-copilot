import React, { useEffect, useMemo, useRef, useState } from "react";
import styled from "styled-components";
import { color, radius, shadow, space } from "../../../styles/theme";

const Field = styled.div`
  position: relative;
  width: 100%;
  margin-bottom: ${space("lg")};
  display: flex;
  flex-direction: column;
`;

const Label = styled.label`
  font-size: 16px;
  margin-bottom: ${space("sm")};
  color: ${color("text")};
  font-weight: 600;
  align-self: flex-start;
`;

const Input = styled.input`
  padding: ${space("sm")};
  border: 1px solid ${color("borderStrong")};
  border-radius: ${radius("sm")};
  width: 100%;
  height: 44px;
  box-sizing: border-box;
  font-size: 16px;
  &:focus { outline: 2px solid ${color("primary")}; outline-offset: 1px; }
`;

const List = styled.div`
  width: 100%;
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  max-height: 200px;
  overflow-y: auto;
  background: ${color("surface")};
  border: 1px solid ${color("borderStrong")};
  border-radius: ${radius("sm")};
  box-shadow: ${shadow("sm")};
  z-index: 10;
`;

const Item = styled.button`
  display: block;
  padding: ${space("sm")};
  width: 100%;
  border: 0;
  border-bottom: 1px solid ${color("borderStrong")};
  background: ${color("surface")};
  text-align: left;
  cursor: pointer;
  &:hover, &:focus { background-color: ${color("surfaceHover")}; }
  &:last-child { border-bottom: 0; }
`;

const CropAutocomplete = ({ cropName, cropNames, onChange, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showAllCrops, setShowAllCrops] = useState(false);
  const containerRef = useRef(null);
  const filteredCrops = useMemo(
    () => showAllCrops
      ? cropNames
      : cropNames.filter((crop) => crop.toLowerCase().includes(cropName.toLowerCase())),
    [cropName, cropNames, showAllCrops]
  );

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setShowAllCrops(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  return (
    <Field ref={containerRef}>
      <Label htmlFor="soil-crop-name">작물 이름</Label>
      <Input
        id="soil-crop-name"
        type="text"
        value={cropName}
        onChange={(event) => {
          onChange(event.target.value);
          setShowAllCrops(false);
          setIsOpen(true);
        }}
        onFocus={() => { setShowAllCrops(true); setIsOpen(true); }}
        onClick={() => { setShowAllCrops(true); setIsOpen(true); }}
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
              onClick={() => { onSelect(crop); setShowAllCrops(false); setIsOpen(false); }}
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
