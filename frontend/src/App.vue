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
const analysisStatus = ref("");
const analysisPollTimer = ref(null);
const analysisHistory = ref([]);
const analysisHistoryLoading = ref(false);
const uploadFiles = ref([]);
const isDragActive = ref(false);
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
const statusFilter = ref("");
const startTimeFilter = ref("");
const endTimeFilter = ref("");
const appliedFilters = ref({
  keyword: "",
  status: "",
  startTime: "",
  endTime: "",
});

const isAuthenticated = computed(() => Boolean(token.value));
const apiStatusText = computed(() => (health.value?.status === "ok" ? "后端在线" : "后端未连接"));
const totalErrors = computed(() => logs.value.reduce((total, item) => total + (item.error_count || 0), 0));
const totalWarnings = computed(() => logs.value.reduce((total, item) => total + (item.warn_count || 0), 0));
const hasAppliedFilters = computed(() =>
  Boolean(
    appliedFilters.value.keyword ||
      appliedFilters.value.status ||
      appliedFilters.value.startTime ||
      appliedFilters.value.endTime,
  ),
);
const appliedFilterTags = computed(() => {
  const tags = [];

  if (appliedFilters.value.keyword) {
    tags.push(`关键词：${appliedFilters.value.keyword}`);
  }

  if (appliedFilters.value.status) {
    tags.push(`状态：${appliedFilters.value.status}`);
  }

  if (appliedFilters.value.startTime) {
    tags.push(`开始：${appliedFilters.value.startTime}`);
  }

  if (appliedFilters.value.endTime) {
    tags.push(`结束：${appliedFilters.value.endTime}`);
  }

  return tags;
});
const selectedEntries = computed(() => selectedLog.value?.entries || []);
const keyEntries = computed(() =>
  selectedEntries.value.filter((entry) => {
    const level = (entry.level || "").toUpperCase();
    return entry.is_key_event || ["WARN", "ERROR", "FATAL", "CRITICAL"].includes(level);
  }),
);
const diagnosisMetrics = computed(() => {
  const total = selectedLog.value?.total_parsed_entries || selectedEntries.value.length;
  const errors = selectedLog.value?.total_error_count || 0;
  const warnings = selectedLog.value?.total_warn_count || 0;
  const keyCount = errors + warnings;
  const riskLevel = errors > 0 ? "严重" : warnings > 0 ? "关注" : "平稳";
  const topIssue = highFrequencyExceptions.value[0]?.title || "未发现高频异常";

  return [
    { label: "风险等级", value: riskLevel },
    { label: "关键事件", value: keyCount },
    { label: "异常占比", value: total ? `${Math.round((keyCount / total) * 100)}%` : "0%" },
    { label: "主要问题", value: topIssue },
  ];
});
const highFrequencyExceptions = computed(() => {
  const groups = new Map();

  for (const entry of keyEntries.value) {
    const title = normalizeIssueTitle(entry.message);
    const current = groups.get(title) || {
      title,
      count: 0,
      level: entry.level || "-",
      firstLine: entry.line_number,
      lastLine: entry.line_number,
      sample: entry.message,
    };

    current.count += 1;
    current.lastLine = entry.line_number;
    if (rankLevel(entry.level) > rankLevel(current.level)) {
      current.level = entry.level;
    }
    groups.set(title, current);
  }

  return Array.from(groups.values())
    .sort((a, b) => b.count - a.count || rankLevel(b.level) - rankLevel(a.level))
    .slice(0, 6);
});
const keyInformationGroups = computed(() => [
  {
    title: "涉及服务",
    items: topExtractedValues(selectedEntries.value, extractServiceName),
    empty: "未识别到服务名",
  },
  {
    title: "请求链路",
    items: topExtractedValues(selectedEntries.value, extractRequestId),
    empty: "未识别到请求 ID",
  },
  {
    title: "问题关键词",
    items: topKeywordHits(keyEntries.value),
    empty: "未识别到明显关键词",
  },
]);
const keyEventTimeline = computed(() => keyEntries.value.slice(0, 8));

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
  analysisHistory.value = [];
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

    if (selectedLogId.value) {
      const stillExists = logs.value.some((log) => log.id === selectedLogId.value);
      if (!stillExists) {
        selectedLogId.value = null;
        selectedLog.value = null;
        analysisResult.value = null;
      }
    }
  } catch {
    logs.value = [];
  } finally {
    logsLoading.value = false;
  }
}

async function applyFilters() {
  appliedFilters.value = {
    keyword: keywordFilter.value.trim(),
    status: statusFilter.value,
    startTime: startTimeFilter.value.trim(),
    endTime: endTimeFilter.value.trim(),
  };
  selectedLogId.value = null;
  selectedLog.value = null;
  analysisResult.value = null;
  await loadLogs();
}

async function loadLogDetail(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) {
    return;
  }

  selectedLogLoading.value = true;
  selectedLogId.value = Number(logId);

  try {
    selectedLog.value = await requestApi(`/logs/${selectedLogId.value}`);
  } catch {
    selectedLog.value = null;
  } finally {
    selectedLogLoading.value = false;
  }
}

async function selectLog(logId) {
  analysisResult.value = null;
  await loadLogDetail(logId);
  await loadAnalysisHistory(logId);
  activeView.value = "detail";
}

function backToWorkspace() {
  activeView.value = "workspace";
}

async function loadAnalysisHistory(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) {
    analysisHistory.value = [];
    return;
  }

  analysisHistoryLoading.value = true;

  try {
    const data = await requestApi(`/logs/${logId}/analyses`);
    analysisHistory.value = data.items || [];
  } catch {
    analysisHistory.value = [];
  } finally {
    analysisHistoryLoading.value = false;
  }
}

async function analyzeLog(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) {
    return;
  }

  stopPolling();
  analysisLoading.value = true;
  analysisStatus.value = "pending";
  analysisResult.value = null;
  selectedLogId.value = Number(logId);

  try {
    await requestApi(`/logs/${selectedLogId.value}/analyze`, {
      method: "POST",
    });
    startPolling(selectedLogId.value);
  } catch {
    analysisLoading.value = false;
    analysisStatus.value = "";
  }
}

function startPolling(logId) {
  stopPolling();
  pollAnalysisStatus(logId);
  analysisPollTimer.value = setInterval(() => pollAnalysisStatus(logId), 2000);
}

function stopPolling() {
  if (analysisPollTimer.value) {
    clearInterval(analysisPollTimer.value);
    analysisPollTimer.value = null;
  }
}

async function pollAnalysisStatus(logId) {
  try {
    const data = await requestApi(`/logs/${logId}/analyze/status`);
    analysisStatus.value = data.status;

    if (data.status === "completed") {
      stopPolling();
      analysisLoading.value = false;
      analysisResult.value = {
        summary: data.summary,
        causes: data.causes,
        suggestions: data.suggestions,
      };
      await loadLogs();
      await loadLogDetail(logId);
      await loadAnalysisHistory(logId);
    } else if (data.status === "failed") {
      stopPolling();
      analysisLoading.value = false;
      analysisStatus.value = "failed";
      errorMessage.value = data.error || "分析失败，请重试。";
    } else if (data.status === "none") {
      stopPolling();
      analysisLoading.value = false;
      analysisStatus.value = "";
      errorMessage.value = "没有找到当前日志的分析任务，请重新点击分析。";
    }
  } catch {
    stopPolling();
    analysisLoading.value = false;
    analysisStatus.value = "";
  }
}

async function submitUpload() {
  if (uploadFiles.value.length === 0) {
    errorMessage.value = "请选择日志文件。";
    return;
  }

  uploadLoading.value = true;

  try {
    const formData = new FormData();
    const isBatchUpload = uploadFiles.value.length > 1;

    for (const file of uploadFiles.value) {
      formData.append(isBatchUpload ? "files" : "file", file);
    }

    uploadResult.value = await requestApi(isBatchUpload ? "/logs/upload/batch" : "/logs/upload", {
      method: "POST",
      body: formData,
    });

    const latestUpload = isBatchUpload ? uploadResult.value.items.at(-1) : uploadResult.value;
    selectedLogId.value = latestUpload.id;
    await loadLogs();
    await loadLogDetail(latestUpload.id);
  } catch {
    uploadResult.value = null;
  } finally {
    uploadLoading.value = false;
  }
}

function onFileChange(event) {
  uploadFiles.value = Array.from(event.target.files || []);
}

function onDragEnter() {
  isDragActive.value = true;
}

function onDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragActive.value = false;
  }
}

function onDrop(event) {
  isDragActive.value = false;
  uploadFiles.value = Array.from(event.dataTransfer?.files || []).filter(isSupportedLogFile);

  if (uploadFiles.value.length === 0) {
    errorMessage.value = "请拖入 .log 或 .txt 文件。";
  }
}

function isSupportedLogFile(file) {
  const filename = file.name.toLowerCase();
  return filename.endsWith(".log") || filename.endsWith(".txt") || file.type === "text/plain";
}

function buildLogQuery() {
  const query = new URLSearchParams();
  const filters = appliedFilters.value;

  if (filters.keyword) {
    query.set("keyword", filters.keyword);
  }

  if (filters.status) {
    query.set("status", filters.status);
  }

  if (filters.startTime) {
    query.set("start_time", filters.startTime);
  }

  if (filters.endTime) {
    query.set("end_time", filters.endTime);
  }

  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

async function clearFilters() {
  keywordFilter.value = "";
  statusFilter.value = "";
  startTimeFilter.value = "";
  endTimeFilter.value = "";
  appliedFilters.value = {
    keyword: "",
    status: "",
    startTime: "",
    endTime: "",
  };
  selectedLogId.value = null;
  selectedLog.value = null;
  analysisResult.value = null;
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

function splitItems(text) {
  if (!text) return [];
  return text.split(/\n{2,}/).map((s) => s.trim()).filter(Boolean);
}

function normalizeIssueTitle(message) {
  return message
    .replace(/\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?/g, "")
    .replace(/\b(?:request[_-]?id|trace[_-]?id|rid|txid)[=:]\s*[\w.-]+/gi, "")
    .replace(/\b[0-9a-f]{8,}\b/gi, "<id>")
    .replace(/\b\d{2,}\b/g, "<n>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 120) || "未命名异常";
}

function rankLevel(level) {
  const levelRanks = {
    CRITICAL: 5,
    FATAL: 5,
    ERROR: 4,
    WARN: 3,
    WARNING: 3,
    INFO: 2,
    DEBUG: 1,
    TRACE: 1,
  };

  return levelRanks[(level || "").toUpperCase()] || 0;
}

function topExtractedValues(entries, extractor) {
  const counts = new Map();

  for (const entry of entries) {
    const value = extractor(entry.message);
    if (!value) continue;
    counts.set(value, (counts.get(value) || 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
}

function extractServiceName(message) {
  const serviceMatch = message.match(/\b(?:service|module|component|logger|app)[=:]\s*([\w.-]+)/i);
  if (serviceMatch) return serviceMatch[1];

  const bracketMatch = message.match(/\[([a-z][\w.-]{2,})\]/i);
  return bracketMatch ? bracketMatch[1] : "";
}

function extractRequestId(message) {
  const match = message.match(/\b(?:request[_-]?id|trace[_-]?id|rid|txid)[=:]\s*([\w.-]+)/i);
  return match ? match[1] : "";
}

function topKeywordHits(entries) {
  const keywordMap = [
    ["timeout", "请求超时"],
    ["exception", "异常抛出"],
    ["connection", "连接问题"],
    ["database", "数据库"],
    ["postgres", "PostgreSQL"],
    ["redis", "Redis"],
    ["cache", "缓存"],
    ["memory", "内存"],
    ["disk", "磁盘"],
    ["unauthorized", "鉴权失败"],
    ["5\\d{2}", "HTTP 5xx"],
  ];
  const counts = new Map();

  for (const entry of entries) {
    for (const [pattern, label] of keywordMap) {
      if (new RegExp(pattern, "i").test(entry.message)) {
        counts.set(label, (counts.get(label) || 0) + 1);
      }
    }
  }

  return Array.from(counts.entries())
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
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
        <button
          :class="{ active: activeView === 'detail' }"
          type="button"
          :disabled="!selectedLogId"
          @click="activeView = 'detail'"
        >
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

      <section v-if="activeView === 'workspace'" class="workspace-content">
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

        <section class="workspace-grid">
          <section class="panel upload-panel">
            <div class="section-heading">
              <div>
                <p class="eyebrow">Upload</p>
                <h2>上传日志</h2>
              </div>
              <span class="tag">{{ uploadFiles.length > 0 ? `${uploadFiles.length} 个文件` : "等待" }}</span>
            </div>

            <div
              class="drop-zone"
              :class="{ active: isDragActive }"
              @dragenter.prevent="onDragEnter"
              @dragover.prevent="onDragEnter"
              @dragleave.prevent="onDragLeave"
              @drop.prevent="onDrop"
            >
              <label class="drop-label" for="log-file">
                <strong>{{ uploadFiles.length > 0 ? `已选择 ${uploadFiles.length} 个文件` : "拖入日志文件" }}</strong>
                <span>支持 .log / .txt，可一次选择多个文件</span>
              </label>
              <input id="log-file" class="file-input" type="file" accept=".log,.txt,text/plain" multiple @change="onFileChange" />
            </div>

            <ul v-if="uploadFiles.length > 0" class="selected-files">
              <li v-for="file in uploadFiles" :key="`${file.name}-${file.size}`">
                <span>{{ file.name }}</span>
                <em>{{ formatBytes(file.size) }}</em>
              </li>
            </ul>

            <button class="primary-button full-button" type="button" :disabled="uploadLoading" @click="submitUpload">
              {{ uploadLoading ? "上传中" : uploadFiles.length > 1 ? "批量上传并解析" : "上传并解析" }}
            </button>

            <dl v-if="uploadResult && !uploadResult.items" class="meta-list">
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

            <dl v-if="uploadResult?.items" class="meta-list">
              <div>
                <dt>上传数量</dt>
                <dd>{{ uploadResult.uploaded_count }}</dd>
              </div>
              <div>
                <dt>最后日志 ID</dt>
                <dd>#{{ uploadResult.items.at(-1)?.id }}</dd>
              </div>
              <div>
                <dt>总解析行数</dt>
                <dd>{{ uploadResult.items.reduce((total, item) => total + item.parsed_entries, 0) }}</dd>
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
                <button class="secondary-button" type="button" :disabled="logsLoading" @click="clearFilters">重置</button>
                <button class="primary-button" type="button" :disabled="logsLoading" @click="applyFilters">
                  {{ logsLoading ? "加载中" : "查询" }}
                </button>
              </div>
            </div>

            <div class="filter-grid">
              <label>
                <span>关键词</span>
                <input v-model="keywordFilter" type="search" placeholder="文件名或日志内容" />
              </label>
              <label>
                <span>状态</span>
                <select v-model="statusFilter">
                  <option value="">全部</option>
                  <option value="parsed">parsed</option>
                  <option value="analyzed">analyzed</option>
                </select>
              </label>
              <label>
                <span>开始时间</span>
                <input v-model="startTimeFilter" type="text" placeholder="" />
              </label>
              <label>
                <span>结束时间</span>
                <input v-model="endTimeFilter" type="text" placeholder="" />
              </label>
            </div>

            <div class="applied-filters">
              <span class="applied-label">当前列表：</span>
              <template v-if="hasAppliedFilters">
                <span v-for="tag in appliedFilterTags" :key="tag" class="filter-chip">{{ tag }}</span>
              </template>
              <span v-else class="filter-chip muted">全部日志</span>
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

            <p v-if="logs.length === 0" class="empty-state">
              {{ hasAppliedFilters ? "当前筛选条件没有匹配日志" : "暂无日志" }}
            </p>
          </section>
        </section>
      </section>

      <section v-if="activeView === 'detail'" class="detail-page">
        <div class="detail-header">
          <div>
            <p class="eyebrow">Detail</p>
            <h2>{{ selectedLog?.filename || "未选择日志" }}</h2>
          </div>
          <div class="button-row">
            <span v-if="analysisLoading" class="tag tag-active">{{ analysisStatus === 'running' ? '分析中' : '排队中' }}</span>
            <span v-else class="tag">{{ selectedLog?.status }}</span>
            <button class="primary-button" type="button" :disabled="!selectedLogId || analysisLoading" @click="analyzeLog()">
              {{ analysisLoading ? "请稍候..." : "分析" }}
            </button>
            <button class="secondary-button" type="button" @click="backToWorkspace">返回工作台</button>
          </div>
        </div>

        <div class="detail-body">
          <section class="panel detail-main">
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
                <dt>显示行数</dt>
                <dd>
                  {{ selectedLog.parsed_entries }}
                  <span v-if="selectedLog.total_parsed_entries !== selectedLog.parsed_entries" class="stats-hint">
                    / 共 {{ selectedLog.total_parsed_entries }}
                  </span>
                </dd>
              </div>
            </dl>

            <div v-if="selectedLog" class="troubleshooting-dashboard">
              <div class="section-heading compact-heading">
                <div>
                  <p class="eyebrow">Diagnosis</p>
                  <h2>排障面板</h2>
                </div>
              </div>

              <section class="diagnosis-metrics">
                <div v-for="metric in diagnosisMetrics" :key="metric.label" class="diagnosis-metric">
                  <span>{{ metric.label }}</span>
                  <strong>{{ metric.value }}</strong>
                </div>
              </section>

              <section class="dashboard-grid">
                <div class="analysis-card">
                  <h3>高频异常统计</h3>
                  <div v-if="highFrequencyExceptions.length === 0" class="inline-empty">暂无 ERROR / WARN 事件</div>
                  <ol v-else class="issue-list">
                    <li v-for="issue in highFrequencyExceptions" :key="issue.title">
                      <div>
                        <strong>{{ issue.title }}</strong>
                        <span>行 {{ issue.firstLine }} - {{ issue.lastLine }}</span>
                      </div>
                      <em>{{ issue.level }} · {{ issue.count }} 次</em>
                    </li>
                  </ol>
                </div>

                <div class="analysis-card">
                  <h3>关键信息聚合</h3>
                  <div class="info-groups">
                    <section v-for="group in keyInformationGroups" :key="group.title">
                      <h4>{{ group.title }}</h4>
                      <div v-if="group.items.length === 0" class="inline-empty">{{ group.empty }}</div>
                      <div v-else class="info-chips">
                        <span v-for="item in group.items" :key="`${group.title}-${item.label}`">
                          {{ item.label }} <em>{{ item.count }}</em>
                        </span>
                      </div>
                    </section>
                  </div>
                </div>
              </section>

              <section class="analysis-card">
                <h3>关键事件</h3>
                <div v-if="keyEventTimeline.length === 0" class="inline-empty">暂无关键事件</div>
                <div v-else class="event-timeline">
                  <article v-for="entry in keyEventTimeline" :key="entry.id">
                    <span class="tag">{{ entry.level || "-" }}</span>
                    <div>
                      <strong>第 {{ entry.line_number }} 行 · {{ entry.timestamp || "无时间戳" }}</strong>
                      <p>{{ entry.message }}</p>
                    </div>
                  </article>
                </div>
              </section>

              <section v-if="analysisResult" class="ai-result-grid">
                <div class="analysis-card">
                  <h3>AI 摘要</h3>
                  <p class="analysis-text">{{ analysisResult.summary }}</p>
                </div>
                <div class="analysis-card analysis-card-warn">
                  <h3>异常原因</h3>
                  <ul class="analysis-list">
                    <li v-for="(item, i) in splitItems(analysisResult.causes)" :key="i">{{ item }}</li>
                  </ul>
                </div>
                <div class="analysis-card analysis-card-ok">
                  <h3>排障建议</h3>
                  <ul class="analysis-list">
                    <li v-for="(item, i) in splitItems(analysisResult.suggestions)" :key="i">{{ item }}</li>
                  </ul>
                </div>
              </section>
              <div v-else class="analysis-card analysis-card-muted">
                <h3>AI 分析</h3>
                <p class="analysis-text">点击右上角「分析」后，这里会展示摘要、异常原因和排障建议。</p>
              </div>
            </div>

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

          <aside class="detail-sidebar">
            <section class="panel">
              <div class="section-heading compact-heading">
                <div>
                  <p class="eyebrow">Preview</p>
                  <h2>原始片段</h2>
                </div>
              </div>
              <pre>{{ selectedLog?.content_preview || "暂无内容" }}</pre>
            </section>

            <section class="panel">
              <div class="section-heading compact-heading">
                <div>
                  <p class="eyebrow">History</p>
                  <h2>分析历史</h2>
                </div>
              </div>
              <div v-if="analysisHistoryLoading" class="empty-state">加载中</div>
              <div v-else-if="analysisHistory.length === 0" class="empty-state">暂无分析记录</div>
              <div v-else class="history-list">
                <div
                  v-for="record in analysisHistory"
                  :key="record.id"
                  class="history-item"
                  @click="analysisResult = record"
                >
                  <span class="history-time">{{ formatDate(record.analyzed_at) }}</span>
                  <span class="tag">{{ record.id }}</span>
                </div>
              </div>
            </section>
          </aside>
        </div>
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
