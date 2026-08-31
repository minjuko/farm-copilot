import React from "react";
import BaseModal from "./BaseModal";

const CustomModal = ({
  content,
  customHeight,
  customTop,
  isError,
  isOpen,
  onConfirm,
  onRequestClose,
  overlayStyles,
  showConfirmButton,
  title,
}) => {
  const actions = showConfirmButton
    ? [
        { label: "삭제", onClick: onConfirm, color: "#e53e3e", hoverColor: "#c53030" },
        { label: "취소", onClick: onRequestClose },
      ]
    : [{
        label: "확인",
        onClick: onRequestClose,
        color: isError ? "#e53e3e" : "#4aaa87",
        hoverColor: isError ? "#c53030" : "#3b8b6d",
      }];

  return (
    <BaseModal
      actions={actions}
      content={content}
      isOpen={isOpen}
      maxHeight={customHeight}
      onRequestClose={onRequestClose}
      overlayZIndex={overlayStyles?.zIndex}
      title={title}
      top={customTop}
    />
  );
};

export default CustomModal;
