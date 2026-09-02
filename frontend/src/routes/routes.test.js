jest.mock("../components/templates/crop/SessionDetails", () => () => null);

import {
  chatRoutes,
  diagnosisRoutes,
  predictionRoutes,
  protectedAnalysisRoutes,
  soilRoutes,
} from "./analysisRoutes";
import { protectedCommunityRoutes, publicCommunityRoutes } from "./communityRoutes";
import { guestOnlyRoutes, protectedUserRoutes, publicUserRoutes } from "./userRoutes";

const allRoutes = [
  ...publicUserRoutes,
  ...guestOnlyRoutes,
  ...protectedUserRoutes,
  ...publicCommunityRoutes,
  ...protectedCommunityRoutes,
  ...protectedAnalysisRoutes,
];

test("uses unique absolute paths for every application route", () => {
  const paths = allRoutes.map((route) => route.path);
  expect(paths.every((path) => path.startsWith("/"))).toBe(true);
  expect(new Set(paths).size).toBe(paths.length);
});

test("keeps public, guest-only, and protected ownership explicit", () => {
  expect(publicCommunityRoutes.map(({ path }) => path)).toContain("/post/:id");
  expect(guestOnlyRoutes.map(({ path }) => path)).toEqual(expect.arrayContaining(["/login", "/signup"]));
  expect(protectedCommunityRoutes.map(({ path }) => path)).toEqual(expect.arrayContaining([
    "/post/create",
    "/post/edit/:id",
  ]));
});

test("groups analysis routes by backend feature and removes the obsolete detail alias", () => {
  expect(predictionRoutes.map(({ path }) => path)).toContain("/session-details/:sessionId");
  expect(predictionRoutes.map(({ path }) => path)).not.toContain("/session-details");
  expect(diagnosisRoutes.map(({ path }) => path)).toContain("/info/:sessionId");
  expect(soilRoutes.map(({ path }) => path)).toContain("/soil-details/:sessionId");
  expect(chatRoutes.map(({ path }) => path)).toContain("/chat/:sessionId");
});
