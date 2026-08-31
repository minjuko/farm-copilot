import React from "react";
import BaseModal from "./BaseModal";

const ConfirmModal = ({
  cancelColor = "#e53e3e",
  cancelHoverColor = "#c53030",
  cancelText = "닫기",
  closeModal,
  confirmColor = "#4aaa87",
  confirmHoverColor = "#3b8b6d",
  confirmText = "확인",
  content,
  isOpen,
  onConfirm,
  onRequestClose,
  title,
}) => (
  <BaseModal
    isOpen={isOpen}
    onRequestClose={onRequestClose}
    title={title}
    content={content}
    top="40%"
    actions={[
      { label: confirmText, onClick: onConfirm, color: confirmColor, hoverColor: confirmHoverColor },
      { label: cancelText, onClick: closeModal || onRequestClose, color: cancelColor, hoverColor: cancelHoverColor },
    ]}
  />
);

export default ConfirmModal;
