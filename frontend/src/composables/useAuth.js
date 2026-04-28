import { computed, ref } from "vue";

export function useAuth(requestApi) {
  const authMode = ref("login");
  const authEmail = ref("");
  const authPassword = ref("");
  const authLoading = ref(false);
  const authResult = ref(null);
  const authNotice = ref("");
  const sessionLoading = ref(true);
  const currentEmail = ref("");

  const isAuthenticated = computed(() => Boolean(currentEmail.value));

  async function submitAuth(onSuccess) {
    authLoading.value = true;
    authNotice.value = "";

    try {
      authResult.value = await requestApi(`/auth/${authMode.value}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail.value, password: authPassword.value }),
      });

      if (authResult.value.access_token) {
        if (onSuccess) await onSuccess(authResult.value.access_token);
        return;
      }

      authNotice.value = authResult.value.message || "注册成功，请登录。";
      authMode.value = "login";
    } catch {
      authResult.value = null;
    } finally {
      authLoading.value = false;
    }
  }

  async function restoreSession(onSuccess) {
    sessionLoading.value = true;
    try {
      let user;
      try {
        user = await requestApi("/auth/me", { silent: true });
      } catch {
        await requestApi("/auth/refresh", { method: "POST", silent: true });
        user = await requestApi("/auth/me", { silent: true });
      }
      currentEmail.value = user.email;
      if (onSuccess) await onSuccess();
    } catch {
      currentEmail.value = "";
    } finally {
      sessionLoading.value = false;
    }
  }

  async function logout(clearState) {
    try {
      await requestApi("/auth/logout", { method: "POST", silent: true });
    } catch {
      // clear local state even if server is unreachable
    }
    currentEmail.value = "";
    if (clearState) clearState();
  }

  return {
    authMode, authEmail, authPassword, authLoading, authResult, authNotice,
    sessionLoading, currentEmail, isAuthenticated,
    submitAuth, restoreSession, logout,
  };
}
