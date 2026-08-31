import { fireEvent, render, screen } from "@testing-library/react";
import BaseModal from "./BaseModal";

test("connects the dialog title and runs configured actions", () => {
  const onConfirm = jest.fn();
  const onClose = jest.fn();
  render(
    <BaseModal
      isOpen
      title="삭제 확인"
      content="이 항목을 삭제할까요?"
      onRequestClose={onClose}
      actions={[
        { label: "삭제", onClick: onConfirm },
        { label: "취소", onClick: onClose },
      ]}
    />
  );

  const dialog = screen.getByRole("dialog", { name: "삭제 확인" });
  expect(dialog).toBeInTheDocument();
  expect(screen.getByText("이 항목을 삭제할까요?")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "삭제" }));
  fireEvent.click(screen.getByRole("button", { name: "취소" }));
  expect(onConfirm).toHaveBeenCalledTimes(1);
  expect(onClose).toHaveBeenCalledTimes(1);
});
