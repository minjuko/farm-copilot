import { appTheme, color, layout, radius, space, zIndex } from "./theme";

test("provides stable design tokens and safe fallbacks outside ThemeProvider", () => {
  expect(color("primary")({ theme: {} })).toBe("#4aaa87");
  expect(space("md")({ theme: appTheme })).toBe("16px");
  expect(radius("md")({ theme: appTheme })).toBe("8px");
  expect(layout("content")({ theme: appTheme })).toBe("75rem");
  expect(zIndex("modal")({ theme: appTheme })).toBe(1100);
});
