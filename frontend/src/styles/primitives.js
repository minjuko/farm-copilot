import styled from "styled-components";
import { color, layout, radius, shadow, space } from "./theme";

export const PageContainer = styled.main`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: ${layout("content")};
  margin: 0 auto;
  padding: ${space("md")};
`;

export const Surface = styled.section`
  width: 100%;
  padding: ${space("md")};
  background: ${color("surface")};
  border: 1px solid ${color("border")};
  border-radius: ${radius("md")};
  box-shadow: ${shadow("sm")};
`;

export const Stack = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ $gap, theme }) => theme?.spacing?.[$gap] || $gap || theme?.spacing?.md || "16px"};
`;

export const Inline = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ $gap, theme }) => theme?.spacing?.[$gap] || $gap || theme?.spacing?.sm || "8px"};
`;

export const StatusMessage = styled.p`
  width: 100%;
  padding: ${space("lg")} ${space("md")};
  margin: 0;
  text-align: center;
  color: ${({ $error, theme }) => $error
    ? theme?.colors?.danger || "#e53e3e"
    : theme?.colors?.textMuted || "#666666"};
`;

export const ListPage = styled(PageContainer)`
  background: ${color("background")};
  min-height: 100%;
`;

export const EmptyState = styled(StatusMessage)`
  min-height: 8rem;
  display: flex;
  align-items: center;
  justify-content: center;
`;
