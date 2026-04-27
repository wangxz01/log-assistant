<script setup>
import { computed, onMounted, ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

const activeView = ref("overview");
const health = ref(null);
const healthLoading = ref(false);
const logs = ref([]);
const logsLoading = ref(false);
const selectedLogId = ref(1);
const selectedLog = ref(null);
const selectedLogLoading = ref(false);
const analysisResult = ref(null);
const analysisLoading = ref(false);
const uploadFile = ref(null);
const uploadLoading = ref(false);
const uploadResult = ref(null);
const authEmail = ref("student@example.com");
const authPassword = ref("password123");
const authLoading = ref(false);
const authResult = ref(null);
const token = ref("");
const lastResponse = ref(null);
const errorMessage = ref("");

const apiStatusText = computed(() => {
  if (!health.value) {
    return "未检查";
  }

  return health.value.status === "ok" ? "在线" : "异常";
});

const selectedLogStatus = computed(() => selectedLog.value?.status || "未选择");

async function requestApi(path, options = {}) {
  errorMessage.value = "";

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, options);
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : await response.text();
    lastResponse.value = {
      path,
      status: response.status,
      ok: response.ok,
      body,
    };

    if (!response.ok) {
      throw new Error(`请求失败：${response.status}`);
    }

    return body;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "请求失败";
    throw error;
  }
}

async function checkHealth() {
  healthLoading.value = true;

  try {
    health.value = await requestApi("/health");
  } catch {
    health.value = null;
  } finally {
    healthLoading.value = false;
  }
}

async function loadLogs() {
  logsLoading.value = true;

  try {
    const data = await requestApi("/logs");
    logs.value = data.items || [];

    if (logs.value.length > 0 && !selectedLog.value) {
      selectedLogId.value = logs.value[0].id;
    }
  } catch {
    logs.value = [];
  } finally {
    logsLoading.value = false;
  }
}

async function loadLogDetail(logId = selectedLogId.value) {
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

async function analyzeLog(logId = selectedLogId.value) {
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
    errorMessage.value = "请选择日志文件";
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

async function submitAuth(mode) {
  authLoading.value = true;

  try {
    authResult.value = await requestApi(`/auth/${mode}`, {
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
    }
  } catch {
    authResult.value = null;
  } finally {
    authLoading.value = false;
  }
}

function onFileChange(event) {
  uploadFile.value = event.target.files?.[0] || null;
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

function showDetail(logId) {
  activeView.value = "logs";
  loadLogDetail(logId);
}

onMounted(async () => {
  await checkHealth();
  await loadLogs();

  if (logs.value.length > 0) {
    await loadLogDetail(logs.value[0].id);
  }
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-block">
        <div class="brand-mark">LA</div>
        <div>
          <p class="eyebrow">Log Assistant</p>
          <h1>日志分析控制台</h1>
        </div>
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button :class="{ active: activeView === 'overview' }" type="button" @click="activeView = 'overview'">
          概览
        </button>
        <button :class="{ active: activeView === 'logs' }" type="button" @click="activeView = 'logs'">
          日志工作台
        </button>
        <button :class="{ active: activeView === 'auth' }" type="button" @click="activeView = 'auth'">
          认证测试
        </button>
        <button :class="{ active: activeView === 'response' }" type="button" @click="activeView = 'response'">
          接口响应
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
          <p class="eyebrow">API Base</p>
          <strong>{{ apiBaseUrl }}</strong>
        </div>
        <button class="secondary-button" type="button" :disabled="healthLoading" @click="checkHealth">
          {{ healthLoading ? "检查中" : "检查 API" }}
        </button>
      </header>

      <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

      <section v-if="activeView === 'overview'" class="view-grid">
        <div class="metric-card">
          <span>API 状态</span>
          <strong>{{ apiStatusText }}</strong>
        </div>
        <div class="metric-card">
          <span>日志数量</span>
          <strong>{{ logs.length }}</strong>
        </div>
        <div class="metric-card">
          <span>当前日志</span>
          <strong>#{{ selectedLogId }}</strong>
        </div>
        <div class="metric-card">
          <span>登录令牌</span>
          <strong>{{ token ? "已获取" : "未获取" }}</strong>
        </div>

        <section class="panel wide-panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Logs</p>
              <h2>最近日志</h2>
            </div>
            <button class="secondary-button" type="button" :disabled="logsLoading" @click="loadLogs">
              {{ logsLoading ? "加载中" : "刷新" }}
            </button>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>文件名</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in logs" :key="log.id">
                  <td>#{{ log.id }}</td>
                  <td>{{ log.filename }}</td>
                  <td><span class="tag">{{ log.status }}</span></td>
                  <td>
                    <button class="text-button" type="button" @click="showDetail(log.id)">查看</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Analyze</p>
              <h2>分析状态</h2>
            </div>
          </div>
          <pre>{{ formatJson(analysisResult || selectedLog) || "暂无数据" }}</pre>
        </section>
      </section>

      <section v-if="activeView === 'logs'" class="split-layout">
        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Upload</p>
              <h2>上传日志</h2>
            </div>
          </div>

          <label class="field-label" for="log-file">日志文件</label>
          <input id="log-file" class="file-input" type="file" @change="onFileChange" />
          <button class="primary-button" type="button" :disabled="uploadLoading" @click="submitUpload">
            {{ uploadLoading ? "上传中" : "上传日志" }}
          </button>

          <pre>{{ formatJson(uploadResult) || "等待上传" }}</pre>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Detail</p>
              <h2>日志详情</h2>
            </div>
            <span class="tag">{{ selectedLogStatus }}</span>
          </div>

          <label class="field-label" for="log-id">日志 ID</label>
          <div class="inline-form">
            <input id="log-id" v-model.number="selectedLogId" type="number" min="1" />
            <button class="secondary-button" type="button" :disabled="selectedLogLoading" @click="loadLogDetail()">
              {{ selectedLogLoading ? "加载中" : "查看" }}
            </button>
            <button class="primary-button" type="button" :disabled="analysisLoading" @click="analyzeLog()">
              {{ analysisLoading ? "分析中" : "分析" }}
            </button>
          </div>

          <pre>{{ formatJson(selectedLog) || "暂无详情" }}</pre>
        </section>

        <section class="panel wide-panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Inventory</p>
              <h2>日志列表</h2>
            </div>
            <button class="secondary-button" type="button" :disabled="logsLoading" @click="loadLogs">
              {{ logsLoading ? "加载中" : "刷新" }}
            </button>
          </div>

          <div class="log-list">
            <button
              v-for="log in logs"
              :key="log.id"
              class="log-row"
              :class="{ selected: log.id === selectedLogId }"
              type="button"
              @click="loadLogDetail(log.id)"
            >
              <span>#{{ log.id }}</span>
              <strong>{{ log.filename }}</strong>
              <em>{{ log.status }}</em>
            </button>
          </div>
        </section>
      </section>

      <section v-if="activeView === 'auth'" class="split-layout">
        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Auth</p>
              <h2>账号接口</h2>
            </div>
          </div>

          <label class="field-label" for="email">邮箱</label>
          <input id="email" v-model="authEmail" type="email" />

          <label class="field-label" for="password">密码</label>
          <input id="password" v-model="authPassword" type="password" />

          <div class="button-row">
            <button class="secondary-button" type="button" :disabled="authLoading" @click="submitAuth('register')">
              注册
            </button>
            <button class="primary-button" type="button" :disabled="authLoading" @click="submitAuth('login')">
              登录
            </button>
          </div>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Token</p>
              <h2>认证结果</h2>
            </div>
          </div>
          <pre>{{ formatJson(authResult) || "暂无认证响应" }}</pre>
        </section>
      </section>

      <section v-if="activeView === 'response'" class="panel response-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Response</p>
            <h2>最近接口响应</h2>
          </div>
        </div>
        <pre>{{ formatJson(lastResponse) || "暂无接口响应" }}</pre>
      </section>
    </main>
  </div>
</template>
