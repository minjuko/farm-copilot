export const appTheme = {
  colors: {
    primary: "#4aaa87",
    primaryHover: "#3b8b6d",
    primaryFocus: "#6dc4b0",
    primarySoft: "#e8f5e9",
    danger: "#e53e3e",
    dangerHover: "#c53030",
    text: "#333333",
    textMuted: "#666666",
    border: "#dddddd",
    borderStrong: "#cccccc",
    surface: "#ffffff",
    background: "#f9f9f9",
    surfaceHover: "#f5f5f5",
    disabled: "#9e9e9e",
    overlay: "rgba(255, 255, 255, 0.8)",
  },
  spacing: {
    xs: "4px",
    sm: "8px",
    md: "16px",
    lg: "24px",
    xl: "32px",
  },
  radii: {
    sm: "4px",
    md: "8px",
    lg: "12px",
  },
  shadows: {
    sm: "0 2px 4px rgba(0, 0, 0, 0.1)",
    md: "0 2px 8px rgba(0, 0, 0, 0.3)",
  },
  breakpoints: {
    mobile: "480px",
    tablet: "768px",
  },
  layout: {
    content: "75rem",
    form: "600px",
  },
  zIndices: {
    header: 1000,
    modal: 1100,
    loader: 9999,
  },
};

export const color = (name) => ({ theme }) => theme?.colors?.[name] || appTheme.colors[name];
export const space = (name) => ({ theme }) => theme?.spacing?.[name] || appTheme.spacing[name];
export const radius = (name) => ({ theme }) => theme?.radii?.[name] || appTheme.radii[name];
export const shadow = (name) => ({ theme }) => theme?.shadows?.[name] || appTheme.shadows[name];
export const layout = (name) => ({ theme }) => theme?.layout?.[name] || appTheme.layout[name];
export const zIndex = (name) => ({ theme }) => theme?.zIndices?.[name] || appTheme.zIndices[name];
