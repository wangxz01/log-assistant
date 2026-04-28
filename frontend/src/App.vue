<script setup>
import { computed, onMounted, ref } from "vue";
import { useApi } from "./composables/useApi.js";
import { useAuth } from "./composables/useAuth.js";
import { useFilters } from "./composables/useFilters.js";
import { useUpload } from "./composables/useUpload.js";
import { formatBytes, formatDate, formatJson, splitItems } from "./composables/useFormat.js";
import AuthPage from "./pages/AuthPage.vue";
import WorkspaceView from "./pages/WorkspaceView.vue";
import DetailView from "./pages/DetailView.vue";
import ResponseView from "./pages/ResponseView.vue";

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
const entriesPage = ref(1);
const entriesPerPage = 50;
const entriesTotalPages = ref(1);
const activeKeyword = ref("");
const logStats = ref(null);

const { token, errorMessage, lastResponse, requestApi } = useApi();
const {
  authMode, authEmail, authPassword, authLoading, authResult, authNotice,
  sessionLoading, currentEmail, isAuthenticated,
  submitAuth, restoreSession, logout: authLogout,
} = useAuth(requestApi);

const {
  keywordFilter, statusFilter, levelFilter, serviceFilter, startTimeFilter, endTimeFilter,
  appliedFilters, hasAppliedFilters, appliedFilterTags,
  buildLogQuery, applyFilters, clearFilters,
} = useFilters(async () => {
  selectedLogId.value = null;
  selectedLog.value = null;
  analysisResult.value = null;
  await loadLogs();
});

const {
  uploadFiles, isDragActive, uploadLoading, uploadResult, uploadProgress,
  submitUpload, onFileChange, onDragEnter, onDragLeave, onDrop,
} = useUpload(() => token.value, async (logId) => {
  selectedLogId.value = logId;
  await loadLogs();
  await loadLogDetail(logId);
});

const apiStatusText = computed(() => (health.value?.status === "ok" ? "后端在线" : "后端未连接"));
const aiConfigured = computed(() => Boolean(health.value?.ai_configured));
const totalErrors = computed(() => logs.value.reduce((total, item) => total + (item.error_count || 0), 0));
const totalWarnings = computed(() => logs.value.reduce((total, item) => total + (item.warn_count || 0), 0));

const selectedEntries = computed(() => selectedLog.value?.entries || []);
const keyEntries = computed(() =>
  selectedEntries.value.filter((entry) => {
    const level = (entry.level || "").toUpperCase();
    return entry.is_key_event || ["WARN", "ERROR", "FATAL", "CRITICAL"].includes(level);
  }),
);

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
  const ranks = { CRITICAL: 5, FATAL: 5, ERROR: 4, WARN: 3, WARNING: 3, INFO: 2, DEBUG: 1, TRACE: 1 };
  return ranks[(level || "").toUpperCase()] || 0;
}

function topExtractedValues(entries, extractor) {
  const counts = new Map();
  for (const entry of entries) {
    const value = extractor(entry);
    if (!value) continue;
    counts.set(value, (counts.get(value) || 0) + 1);
  }
  return Array.from(counts.entries()).map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count).slice(0, 6);
}

function extractServiceName(message) {
  const m = message.match(/\b(?:service|module|component|logger|app)[=:]\s*([\w.-]+)/i);
  if (m) return m[1];
  const b = message.match(/\[([a-z][\w.-]{2,})\]/i);
  return b ? b[1] : "";
}

function extractRequestId(message) {
  const m = message.match(/\b(?:request[_-]?id|trace[_-]?id|rid|txid)[=:]\s*([\w.-]+)/i);
  return m ? m[1] : "";
}

function topKeywordHits(entries) {
  const keywordMap = [
    ["timeout", "请求超时"], ["exception", "异常抛出"], ["connection", "连接问题"],
    ["database", "数据库"], ["postgres", "PostgreSQL"], ["redis", "Redis"],
    ["cache", "缓存"], ["memory", "内存"], ["disk", "磁盘"],
    ["unauthorized", "鉴权失败"], ["5\\d{2}", "HTTP 5xx"],
  ];
  const counts = new Map();
  for (const entry of entries) {
    for (const [pattern, label] of keywordMap) {
      if (new RegExp(pattern, "i").test(entry.message)) counts.set(label, (counts.get(label) || 0) + 1);
    }
  }
  return Array.from(counts.entries()).map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count).slice(0, 6);
}

const diagnosisMetrics = computed(() => {
  const total = selectedLog.value?.total_parsed_entries || selectedEntries.value.length;
  const errors = selectedLog.value?.total_error_count || 0;
  const warnings = selectedLog.value?.total_warn_count || 0;
  const keyCount = errors + warnings;
  const riskLevel = errors > 0 ? "严重" : warnings > 0 ? "关注" : "平稳";
  return [
    { label: "风险等级", value: riskLevel },
    { label: "关键事件", value: keyCount },
    { label: "异常占比", value: total ? `${Math.round((keyCount / total) * 100)}%` : "0%" },
    { label: "主要问题", value: highFrequencyExceptions.value[0]?.title || "未发现高频异常" },
  ];
});

const highFrequencyExceptions = computed(() => {
  const groups = new Map();
  for (const entry of keyEntries.value) {
    const title = normalizeIssueTitle(entry.message);
    const current = groups.get(title) || { title, count: 0, level: entry.level || "-", firstLine: entry.line_number, lastLine: entry.line_number };
    current.count += 1;
    current.lastLine = entry.line_number;
    if (rankLevel(entry.level) > rankLevel(current.level)) current.level = entry.level;
    groups.set(title, current);
  }
  return Array.from(groups.values()).sort((a, b) => b.count - a.count || rankLevel(b.level) - rankLevel(a.level)).slice(0, 6);
});

const keyInformationGroups = computed(() => [
  { title: "涉及服务", items: topExtractedValues(selectedEntries.value, (e) => e.service_name || extractServiceName(e.message)), empty: "未识别到服务名" },
  { title: "请求链路", items: topExtractedValues(selectedEntries.value, (e) => extractRequestId(e.message)), empty: "未识别到请求 ID" },
  { title: "问题关键词", items: topKeywordHits(keyEntries.value), empty: "未识别到明显关键词" },
]);

const keyEventTimeline = computed(() => keyEntries.value.slice(0, 8));

async function checkHealth() {
  try { health.value = await requestApi("/health"); } catch { health.value = null; }
}

async function loadLogs() {
  if (!isAuthenticated.value) { logs.value = []; return; }
  logsLoading.value = true;
  try {
    const data = await requestApi(`/logs${buildLogQuery()}`);
    logs.value = data.items || [];
    if (selectedLogId.value) {
      if (!logs.value.some((log) => log.id === selectedLogId.value)) {
        selectedLogId.value = null;
        selectedLog.value = null;
        analysisResult.value = null;
      }
    }
  } catch { logs.value = []; } finally { logsLoading.value = false; }
}

async function loadLogDetail(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) return;
  selectedLogLoading.value = true;
  selectedLogId.value = Number(logId);
  activeKeyword.value = appliedFilters.value.keyword || "";
  try {
    const params = new URLSearchParams({ page: entriesPage.value, per_page: entriesPerPage });
    if (activeKeyword.value) params.set("keyword", activeKeyword.value);
    if (appliedFilters.value.service) params.set("service", appliedFilters.value.service);
    if (appliedFilters.value.level) params.set("level", appliedFilters.value.level);
    if (appliedFilters.value.startTime) params.set("start_time", appliedFilters.value.startTime);
    if (appliedFilters.value.endTime) params.set("end_time", appliedFilters.value.endTime);
    selectedLog.value = await requestApi(`/logs/${selectedLogId.value}?${params}`);
    entriesTotalPages.value = selectedLog.value?.total_pages || 1;
  } catch { selectedLog.value = null; } finally { selectedLogLoading.value = false; }
}

async function goToEntriesPage(page) {
  entriesPage.value = page;
  await loadLogDetail();
}

async function loadLogStats(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) return;
  try { logStats.value = await requestApi(`/logs/${logId}/stats`, { silent: true }); }
  catch { logStats.value = null; }
}

async function loadAnalysisHistory(logId = selectedLogId.value) {
  if (!isAuthenticated.value || !logId) { analysisHistory.value = []; return; }
  analysisHistoryLoading.value = true;
  try { const data = await requestApi(`/logs/${logId}/analyses`); analysisHistory.value = data.items || []; }
  catch { analysisHistory.value = []; } finally { analysisHistoryLoading.value = false; }
}

async function selectLog(logId) {
  analysisResult.value = null;
  entriesPage.value = 1;
  logStats.value = null;
  await loadLogDetail(logId);
  await loadAnalysisHistory(logId);
  loadLogStats(logId);
  activeView.value = "detail";
}

function backToWorkspace() { activeView.value = "workspace"; }

async function analyzeLog() {
  if (!isAuthenticated.value || !selectedLogId.value) return;
  if (!aiConfigured.value) { errorMessage.value = "AI 分析未配置：请在 .env 中设置 DEEPSEEK_API_KEY 后重启服务。"; return; }
  stopPolling();
  analysisLoading.value = true;
  analysisStatus.value = "pending";
  analysisResult.value = null;
  try { await requestApi(`/logs/${selectedLogId.value}/analyze`, { method: "POST" }); startPolling(selectedLogId.value); }
  catch { analysisLoading.value = false; analysisStatus.value = ""; }
}

function startPolling(logId) {
  stopPolling();
  pollAnalysisStatus(logId);
  analysisPollTimer.value = setInterval(() => pollAnalysisStatus(logId), 2000);
}

function stopPolling() {
  if (analysisPollTimer.value) { clearInterval(analysisPollTimer.value); analysisPollTimer.value = null; }
}

async function pollAnalysisStatus(logId) {
  try {
    const data = await requestApi(`/logs/${logId}/analyze/status`);
    analysisStatus.value = data.status;
    if (data.status === "completed") {
      stopPolling();
      analysisLoading.value = false;
      analysisResult.value = { summary: data.summary, causes: data.causes, suggestions: data.suggestions };
      await loadLogs(); await loadLogDetail(logId); await loadAnalysisHistory(logId);
    } else if (data.status === "failed") {
      stopPolling(); analysisLoading.value = false; analysisStatus.value = "failed";
      errorMessage.value = data.error || "分析失败，请重试。";
    } else if (data.status === "none") {
      stopPolling(); analysisLoading.value = false; analysisStatus.value = "";
      errorMessage.value = "没有找到当前日志的分析任务，请重新点击分析。";
    }
  } catch { stopPolling(); analysisLoading.value = false; analysisStatus.value = ""; }
}

function exportAnalysis() {
  if (!analysisResult.value) return;
  const lines = [];
  lines.push("=== AI 摘要 ===");
  lines.push(analysisResult.value.summary || "");
  lines.push("");
  lines.push("=== 异常原因 ===");
  const causes = Array.isArray(analysisResult.value.causes) ? analysisResult.value.causes : [analysisResult.value.causes];
  causes.forEach((c, i) => lines.push(`${i + 1}. ${c}`));
  lines.push("");
  lines.push("=== 排障建议 ===");
  const suggestions = Array.isArray(analysisResult.value.suggestions) ? analysisResult.value.suggestions : [analysisResult.value.suggestions];
  suggestions.forEach((s, i) => lines.push(`${i + 1}. ${s}`));
  downloadText(`analysis-${selectedLogId.value}.txt`, lines.join("\n"));
}

function exportEntries() {
  if (!selectedLog.value?.entries?.length) return;
  const header = "行号\t时间\t级别\t服务/模块\t内容";
  const rows = selectedLog.value.entries.map((e) =>
    `${e.line_number}\t${e.timestamp || ""}\t${e.level || ""}\t${e.service_name || ""}\t${e.message}`,
  );
  downloadText(`entries-${selectedLogId.value}.tsv`, [header, ...rows].join("\n"));
}

function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function logout() {
  authLogout(() => {
    logs.value = [];
    selectedLogId.value = null;
    selectedLog.value = null;
    analysisResult.value = null;
    analysisHistory.value = [];
    uploadResult.value = null;
    authResult.value = null;
  });
}

onMounted(async () => {
  await checkHealth();
  await restoreSession(async () => {
    token.value = "";
    activeView.value = "workspace";
    await loadLogs();
  });
});

async function onFormSubmitAuth() {
  await submitAuth(async (accessToken) => {
    token.value = accessToken;
    currentEmail.value = authEmail.value;
    activeView.value = "workspace";
    await loadLogs();
  });
}
</script>

<template>
  <AuthPage
    v-if="sessionLoading || !isAuthenticated"
    :health="health"
    :session-loading="sessionLoading"
    :is-authenticated="isAuthenticated"
    :auth-mode="authMode"
    :auth-email="authEmail"
    :auth-password="authPassword"
    :auth-loading="authLoading"
    :error-message="errorMessage"
    :auth-notice="authNotice"
    :api-status-text="apiStatusText"
    @update:auth-mode="authMode = $event"
    @update:auth-email="authEmail = $event"
    @update:auth-password="authPassword = $event"
    @submit="onFormSubmitAuth"
  />

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

      <WorkspaceView
        v-if="activeView === 'workspace'"
        :logs="logs"
        :logs-loading="logsLoading"
        :selected-log-id="selectedLogId"
        :total-errors="totalErrors"
        :total-warnings="totalWarnings"
        :upload-files="uploadFiles"
        :is-drag-active="isDragActive"
        :upload-loading="uploadLoading"
        :upload-result="uploadResult"
        :upload-progress="uploadProgress"
        :has-applied-filters="hasAppliedFilters"
        :applied-filter-tags="appliedFilterTags"
        :keyword-filter="keywordFilter"
        :status-filter="statusFilter"
        :level-filter="levelFilter"
        :service-filter="serviceFilter"
        :start-time-filter="startTimeFilter"
        :end-time-filter="endTimeFilter"
        @select-log="selectLog"
        @submit-upload="submitUpload"
        @file-change="onFileChange"
        @drag-enter="onDragEnter"
        @drag-over="onDragEnter"
        @drag-leave="onDragLeave"
        @drop="onDrop"
        @apply-filters="applyFilters"
        @clear-filters="clearFilters"
        @update:keyword-filter="keywordFilter = $event"
        @update:status-filter="statusFilter = $event"
        @update:level-filter="levelFilter = $event"
        @update:service-filter="serviceFilter = $event"
        @update:start-time-filter="startTimeFilter = $event"
        @update:end-time-filter="endTimeFilter = $event"
      />

      <DetailView
        v-if="activeView === 'detail'"
        :selected-log="selectedLog"
        :selected-log-id="selectedLogId"
        :analysis-result="analysisResult"
        :analysis-loading="analysisLoading"
        :analysis-status="analysisStatus"
        :analysis-history="analysisHistory"
        :analysis-history-loading="analysisHistoryLoading"
        :ai-configured="aiConfigured"
        :active-keyword="activeKeyword"
        :log-stats="logStats"
        :entries-page="entriesPage"
        :entries-total-pages="entriesTotalPages"
        :diagnosis-metrics="diagnosisMetrics"
        :high-frequency-exceptions="highFrequencyExceptions"
        :key-information-groups="keyInformationGroups"
        :key-event-timeline="keyEventTimeline"
        @analyze="analyzeLog"
        @back="backToWorkspace"
        @go-page="goToEntriesPage"
        @export-analysis="exportAnalysis"
        @export-entries="exportEntries"
        @select-history="analysisResult = $event"
      />

      <ResponseView
        v-if="activeView === 'response'"
        :last-response="lastResponse"
        :format-json="formatJson"
      />
    </main>
  </div>
</template>
