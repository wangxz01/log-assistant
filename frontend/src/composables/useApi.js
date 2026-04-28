import { ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

const errorMessage = ref("");
const lastResponse = ref(null);

function getErrorMessage(status, body) {
  if (body && typeof body === "object" && body.detail) {
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg || JSON.stringify(item)).join("；");
    }
    return body.detail;
  }
  if (typeof body === "string" && body) return body;
  return `请求失败：${status}`;
}

export function useApi() {
  const token = ref("");

  async function requestApi(path, options = {}) {
    errorMessage.value = "";
    const { silent = false, ...fetchOptions } = options;

    try {
      const headers = new Headers(fetchOptions.headers || {});
      if (token.value && path.startsWith("/logs")) {
        headers.set("Authorization", `Bearer ${token.value}`);
      }

      const response = await fetch(`${apiBaseUrl}${path}`, { ...fetchOptions, headers, credentials: "include" });
      const contentType = response.headers.get("content-type") || "";
      const body = contentType.includes("application/json") ? await response.json() : await response.text();

      lastResponse.value = { path, status: response.status, ok: response.ok, body };

      if (!response.ok) throw new Error(getErrorMessage(response.status, body));
      return body;
    } catch (error) {
      if (!silent) errorMessage.value = error instanceof Error ? error.message : "请求失败";
      throw error;
    }
  }

  return { token, errorMessage, lastResponse, requestApi };
}
