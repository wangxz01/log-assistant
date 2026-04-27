<script setup>
import { computed, onMounted, ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

const activeView = ref("workspace");
const health = ref(null);
const logs = ref([]);
const logsLoading = ref(false);
const selectedLogId = ref(null);
const selectedLog = ref(null);
const selectedLogLoading = ref(false);
const analysisResult = ref(null);
const analysisLoading = ref(false);
const uploadFile = ref(null);
const uploadLoading = ref(false);
const uploadResult = ref(null);
const authMode = ref("login");
const authEmail = ref("");
const authPassword = ref("");
const authLoading = ref(false);
const authResult = ref(null);
const authNotice = ref("");
const token = ref("");
const currentEmail = ref("");
const lastResponse = ref(null);
const errorMessage = ref("");
const keywordFilter = ref("");
const levelFilter = ref("");
const startTimeFilter = ref("");
const endTimeFilter = ref("");

const isAuthenticated = computed(() => Boolean(token.value));
const apiStatusText = computed(() => (health.value?.status === "ok" ? "后端在线" : "后端未连接"));
const selectedLogStatus = computed(() => selectedLog.value?.status || "未选择");
const totalErrors = computed(() => logs.value.reduce((total, item) => total + (item.error_count || 0), 0));
const totalWarnings = computed(() => logs.value.reduce((total, item) => total + (item.warn_count || 0), 0));

async function requestApi(path, options = {}) {
  errorMessage.value = "";

  try {
    const headers = new Headers(options.headers || {});

    if (token.value && path.startsWith("/logs")) {
      headers.set("Authorization", `Bearer ${token.value}`);
    }

    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      headers,
    });
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : await response.text();

    lastResponse.value = {
      path,
      status: response.status,
      ok: response.ok,
      body,
    };

    if (!response.ok) {
      throw new Error(getErrorMessage(response.status, body));
    }

    return body;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "请求失败";
    throw error;
  }
}

function getErrorMessage(status, body) {
  if (body && typeof body === "object" && body.detail) {
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg || JSON.stringify(item)).join("；");
    }

    return body.detail;
  }

  if (typeof body === "string" && body) {
    return body;
  }

  return `请求失败：${status}`;
}

async function checkHealth() {
  try {
    health.value = await requestApi("/health");
  } catch {
    health.value = null;
  }
}

async function submitAuth() {
  authLoading.value = true;
  authNotice.value = "";

  try {
    authResult.value = await requestApi(`/auth/${authMode.value}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: authEmail.value,
        password: authPassword.value,
      }),
    });

    if (authResult.value.access_token) {
      token.value = authResult.value.access_token;
      currentEmail.value = authEmail.value;
      activeView.value = "workspace";
      await loadLogs();
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

function logout() {
  token.value = "";
  currentEmail.value = "";
  logs.value = [];
  selectedLogId.value = null;
  selectedLog.value = null;
  analysisResult.value = null;
  uploadResult.value = null;
  authResult.value = null;
  authMode.value = "login";
}

async function loadLogs() {
  if (!isAuthenticated.value) {
    logs.value = [];
    return;
  }

  logsLoading.value = true;

  try {
    const data = await requestApi(`/logs${buildLogQuery()}`);
    logs.value = data.items || [];

    if (logs.value.length > 0 && !selectedLog.value) {
      await loadLogDetail(logs.value[0].id);
    }
  } catch {
    logs.value = [];
  } finally {
    logsLoading.value = false;
  }
}

async function loadLogDetail(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) {
    return;
  }

  selectedLogLoading.value = true;
  selectedLogId.value = Number(logId);

  try {
    selectedLog.value = await requestApi(`/logs/${selectedLogId.value}${buildLogQuery()}`);
  } catch {
    selectedLog.value = null;
  } finally {
    selectedLogLoading.value = false;
  }
}

async function selectLog(logId) {
  await loadLogDetail(logId);
  activeView.value = "detail";
}

async function analyzeLog(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) {
    return;
  }

  analysisLoading.value = true;
  selectedLogId.value = Number(logId);

  try {
    analysisResult.value = await requestApi(`/logs/${selectedLogId.value}/analyze`, {
      method: "POST",
    });
    await loadLogs();
    await loadLogDetail(selectedLogId.value);
  } catch {
    analysisResult.value = null;
  } finally {
    analysisLoading.value = false;
  }
}

async function submitUpload() {
  if (!uploadFile.value) {
    errorMessage.value = "请选择日志文件。";
    return;
  }

  uploadLoading.value = true;

  try {
    const formData = new FormData();
    formData.append("file", uploadFile.value);
    uploadResult.value = await requestApi("/logs/upload", {
      method: "POST",
      body: formData,
    });
    selectedLogId.value = uploadResult.value.id;
    await loadLogs();
    await loadLogDetail(uploadResult.value.id);
  } catch {
    uploadResult.value = null;
  } finally {
    uploadLoading.value = false;
  }
}

function onFileChange(event) {
  uploadFile.value = event.target.files?.[0] || null;
}

function buildLogQuery() {
  const query = new URLSearchParams();

  if (keywordFilter.value) {
    query.set("keyword", keywordFilter.value);
  }

  if (levelFilter.value) {
    query.set("level", levelFilter.value);
  }

  if (startTimeFilter.value) {
    query.set("start_time", startTimeFilter.value);
  }

  if (endTimeFilter.value) {
    query.set("end_time", endTimeFilter.value);
  }

  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

async function clearFilters() {
  keywordFilter.value = "";
  levelFilter.value = "";
  startTimeFilter.value = "";
  endTimeFilter.value = "";
  await loadLogs();
}

function formatJson(value) {
  if (!value) {
    return "";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function formatBytes(value) {
  if (!value) {
    return "0 B";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  return `${(value / 1024).toFixed(1)} KB`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString();
}

onMounted(async () => {
  await checkHealth();
});
</script>

<template>
  <main v-if="!isAuthenticated" class="auth-page">
    <section class="auth-panel">
      <div class="auth-brand">
        <div class="brand-mark">LA</div>
        <div>
          <p class="eyebrow">Log Assistant</p>
          <h1>登录日志分析平台</h1>
        </div>
      </div>

      <div class="auth-tabs" role="tablist" aria-label="认证方式">
        <button :class="{ active: authMode === 'login' }" type="button" @click="authMode = 'login'">登录</button>
        <button :class="{ active: authMode === 'register' }" type="button" @click="authMode = 'register'">注册</button>
      </div>

      <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>
      <p v-if="authNotice" class="notice-banner">{{ authNotice }}</p>

      <form class="auth-form" @submit.prevent="submitAuth">
        <label class="field-label" for="email">邮箱</label>
        <input id="email" v-model="authEmail" type="email" autocomplete="email" />

        <label class="field-label" for="password">密码</label>
        <input
          id="password"
          v-model="authPassword"
          type="password"
          :autocomplete="authMode === 'register' ? 'new-password' : 'current-password'"
          minlength="8"
        />

        <button class="primary-button full-button" type="submit" :disabled="authLoading">
          {{ authLoading ? "处理中" : authMode === "login" ? "登录" : "创建账号" }}
        </button>
      </form>

      <div class="auth-footer">
        <span class="status-dot" :class="{ online: health?.status === 'ok' }"></span>
        <span>{{ apiStatusText }}</span>
      </div>
    </section>
  </main>

  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand-block">
        <div class="brand-mark">LA</div>
        <div>
          <p class="eyebrow">Log Assistant</p>
          <h1>日志工作台</h1>
        </div>
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button :class="{ active: activeView === 'workspace' }" type="button" @click="activeView = 'workspace'">
          工作台
        </button>
        <button :class="{ active: activeView === 'detail' }" type="button" @click="activeView = 'detail'">
          日志详情
        </button>
        <button :class="{ active: activeView === 'response' }" type="button" @click="activeView = 'response'">
          最近响应
        </button>
      </nav>

      <div class="connection-panel">
        <span class="status-dot" :class="{ online: health?.status === 'ok' }"></span>
        <span>{{ apiStatusText }}</span>
      </div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">Console</p>
          <h2>{{ activeView === "detail" ? "日志详情" : activeView === "response" ? "最近响应" : "日志工作台" }}</h2>
        </div>
        <div class="user-menu">
          <span>{{ currentEmail }}</span>
          <button class="secondary-button" type="button" @click="logout">退出</button>
        </div>
      </header>

      <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

      <section class="metric-grid">
        <div class="metric-card">
          <span>日志</span>
          <strong>{{ logs.length }}</strong>
        </div>
        <div class="metric-card">
          <span>ERROR</span>
          <strong>{{ totalErrors }}</strong>
        </div>
        <div class="metric-card">
          <span>WARN</span>
          <strong>{{ totalWarnings }}</strong>
        </div>
        <div class="metric-card">
          <span>当前日志</span>
          <strong>{{ selectedLogId ? `#${selectedLogId}` : "-" }}</strong>
        </div>
      </section>

      <section v-if="activeView === 'workspace'" class="workspace-grid">
        <section class="panel upload-panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Upload</p>
              <h2>上传日志</h2>
            </div>
            <span class="tag">{{ uploadResult?.status || "等待" }}</span>
          </div>

          <label class="field-label" for="log-file">日志文件</label>
          <input id="log-file" class="file-input" type="file" accept=".log,.txt,text/plain" @change="onFileChange" />

          <button class="primary-button full-button" type="button" :disabled="uploadLoading" @click="submitUpload">
            {{ uploadLoading ? "上传中" : "上传并解析" }}
          </button>

          <dl v-if="uploadResult" class="meta-list">
            <div>
              <dt>ID</dt>
              <dd>#{{ uploadResult.id }}</dd>
            </div>
            <div>
              <dt>文件名</dt>
              <dd>{{ uploadResult.filename }}</dd>
            </div>
            <div>
              <dt>解析行数</dt>
              <dd>{{ uploadResult.parsed_entries }}</dd>
            </div>
          </dl>
        </section>

        <section class="panel list-panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Logs</p>
              <h2>日志列表</h2>
            </div>
            <div class="button-row">
              <button class="secondary-button" type="button" :disabled="logsLoading" @click="clearFilters">清空</button>
              <button class="primary-button" type="button" :disabled="logsLoading" @click="loadLogs">
                {{ logsLoading ? "加载中" : "查询" }}
              </button>
            </div>
          </div>

          <div class="filter-grid">
            <label>
              <span>关键词</span>
              <input v-model="keywordFilter" type="search" placeholder="timeout" />
            </label>
            <label>
              <span>级别</span>
              <select v-model="levelFilter">
                <option value="">全部</option>
                <option value="ERROR">ERROR</option>
                <option value="WARN">WARN</option>
                <option value="INFO">INFO</option>
                <option value="DEBUG">DEBUG</option>
              </select>
            </label>
            <label>
              <span>开始时间</span>
              <input v-model="startTimeFilter" type="text" placeholder="2026-04-28T10:00:00" />
            </label>
            <label>
              <span>结束时间</span>
              <input v-model="endTimeFilter" type="text" placeholder="2026-04-28T11:00:00" />
            </label>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>文件名</th>
                  <th>状态</th>
                  <th>上传时间</th>
                  <th>ERROR</th>
                  <th>WARN</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="log in logs"
                  :key="log.id"
                  :class="{ selected: log.id === selectedLogId }"
                  @click="selectLog(log.id)"
                >
                  <td>#{{ log.id }}</td>
                  <td>{{ log.filename }}</td>
                  <td><span class="tag">{{ log.status }}</span></td>
                  <td>{{ formatDate(log.uploaded_at) }}</td>
                  <td>{{ log.error_count }}</td>
                  <td>{{ log.warn_count }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-if="logs.length === 0" class="empty-state">暂无日志</p>
        </section>
      </section>

      <section v-if="activeView === 'detail'" class="detail-grid">
        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Detail</p>
              <h2>{{ selectedLog?.filename || "未选择日志" }}</h2>
            </div>
            <div class="button-row">
              <span class="tag">{{ selectedLogStatus }}</span>
              <button class="primary-button" type="button" :disabled="!selectedLogId || analysisLoading" @click="analyzeLog()">
                {{ analysisLoading ? "分析中" : "分析" }}
              </button>
            </div>
          </div>

          <dl v-if="selectedLog" class="meta-list detail-meta">
            <div>
              <dt>所有者</dt>
              <dd>{{ selectedLog.owner_email }}</dd>
            </div>
            <div>
              <dt>上传时间</dt>
              <dd>{{ formatDate(selectedLog.uploaded_at) }}</dd>
            </div>
            <div>
              <dt>大小</dt>
              <dd>{{ formatBytes(selectedLog.size_bytes) }}</dd>
            </div>
            <div>
              <dt>解析行数</dt>
              <dd>{{ selectedLog.parsed_entries }}</dd>
            </div>
          </dl>

          <div class="table-wrap entries-table">
            <table>
              <thead>
                <tr>
                  <th>行</th>
                  <th>时间</th>
                  <th>级别</th>
                  <th>内容</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in selectedLog?.entries || []" :key="entry.id" :class="{ key: entry.is_key_event }">
                  <td>{{ entry.line_number }}</td>
                  <td>{{ entry.timestamp || "-" }}</td>
                  <td><span class="tag">{{ entry.level || "-" }}</span></td>
                  <td>{{ entry.message }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-if="!selectedLog" class="empty-state">未选择日志</p>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Preview</p>
              <h2>原始片段</h2>
            </div>
          </div>
          <pre>{{ selectedLog?.content_preview || "暂无内容" }}</pre>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Analyze</p>
              <h2>分析结果</h2>
            </div>
          </div>
          <pre>{{ formatJson(analysisResult) || "暂无结果" }}</pre>
        </section>
      </section>

      <section v-if="activeView === 'response'" class="panel response-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Response</p>
            <h2>最近响应</h2>
          </div>
        </div>
        <pre>{{ formatJson(lastResponse) || "暂无响应" }}</pre>
      </section>
    </main>
  </div>
</template>
