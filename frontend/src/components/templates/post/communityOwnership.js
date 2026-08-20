export const isCommunityOwner = (authStatus, user, resource) => {
  if (authStatus !== "authenticated" || !user || !resource) {
    return false;
  }

  const currentUserId = user.user_id ?? user.id;
  if (currentUserId != null && resource.user_id != null) {
    return String(currentUserId) === String(resource.user_id);
  }

  const resourceUsername = resource.username ?? resource.user__username;
  return Boolean(user.username && resourceUsername)
    && user.username === resourceUsername;
};
