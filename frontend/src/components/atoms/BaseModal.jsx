import React, { useId } from "react";
import Modal from "react-modal";
import styled from "styled-components";
import { color, radius, shadow, space, zIndex } from "../../styles/theme";

const Dialog = styled(Modal)`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: ${space("lg")};
  background: ${color("surface")};
  border: 1px solid ${color("border")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("md")};
  position: absolute;
  top: ${({ $top }) => $top || "50%"};
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 400px;
  width: 80%;
  max-height: ${({ $maxHeight }) => $maxHeight || "400px"};
  z-index: ${zIndex("modal")};
`;

const Title = styled.h2`font-size: 24px; margin-bottom: ${space("md")}; color: ${color("text")};`;
const Content = styled.div`font-size: 16px; color: ${color("textMuted")}; margin-bottom: ${space("lg")}; text-align: center;`;
const Actions = styled.div`display: flex; gap: ${space("sm")};`;
const Button = styled.button`
  padding: 12px 16px;
  font-size: 16px;
  font-weight: bold;
  color: white;
  background: ${({ $color }) => $color};
  border: 0;
  border-radius: ${radius("sm")};
  cursor: pointer;
  &:hover { background: ${({ $hoverColor }) => $hoverColor}; }
`;

const BaseModal = ({
  actions = [],
  children,
  content,
  isOpen,
  maxHeight,
  onRequestClose,
  overlayZIndex,
  title,
  top,
}) => {
  const generatedId = useId();
  const titleId = `modal-title-${generatedId.replace(/:/g, "")}`;

  return (
    <Dialog
      isOpen={isOpen}
      onRequestClose={onRequestClose}
      contentLabel={title}
      aria={{ labelledby: titleId }}
      ariaHideApp={false}
      shouldReturnFocusAfterClose
      $top={top}
      $maxHeight={maxHeight}
      style={overlayZIndex ? { overlay: { zIndex: overlayZIndex } } : undefined}
    >
      <Title id={titleId}>{title}</Title>
      <Content>{children || content}</Content>
      {actions.length > 0 && (
        <Actions>
          {actions.map((action) => (
            <Button
              key={action.label}
              type="button"
              onClick={action.onClick}
              $color={action.color || "#4aaa87"}
              $hoverColor={action.hoverColor || "#3b8b6d"}
            >
              {action.label}
            </Button>
          ))}
        </Actions>
      )}
    </Dialog>
  );
};

export default BaseModal;
