import React, { useId } from "react";
import Modal from "react-modal";
import styled from "styled-components";

const Dialog = styled(Modal)`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  position: absolute;
  top: ${({ $top }) => $top || "50%"};
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 400px;
  width: 80%;
  max-height: ${({ $maxHeight }) => $maxHeight || "400px"};
`;

const Title = styled.h2`font-size: 24px; margin-bottom: 16px; color: #333;`;
const Content = styled.div`font-size: 16px; color: #666; margin-bottom: 24px; text-align: center;`;
const Actions = styled.div`display: flex; gap: 10px;`;
const Button = styled.button`
  padding: 12px 16px;
  font-size: 16px;
  font-weight: bold;
  color: white;
  background: ${({ $color }) => $color};
  border: 0;
  border-radius: 4px;
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
