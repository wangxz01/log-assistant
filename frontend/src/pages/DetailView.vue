<script setup>
import { ref } from "vue";
import { formatDate } from "../composables/useFormat.js";

const newRuleName = ref("");
const newRuleLevel = ref("");
const newRuleKeyword = ref("");
const newRuleThreshold = ref(1);

defineProps({
  selectedLog: Object,
  selectedLogId: [Number, null],
  analysisResult: Object,
  analysisLoading: Boolean,
  analysisStatus: String,
  analysisHistory: Array,
  analysisHistoryLoading: Boolean,
  aiConfigured: Boolean,
  activeKeyword: String,
  logStats: Object,
  entriesPage: Number,
  entriesTotalPages: Number,
  diagnosisMetrics: Array,
  highFrequencyExceptions: Array,
  keyInformationGroups: Array,
  keyEventTimeline: Array,
  alertRules: Array,
  alertResults: Object,
});

defineEmits([
  "analyze",
  "back",
  "go-page",
  "export-analysis",
  "export-entries",
  "select-history",
  "create-alert",
  "delete-alert",
  "eval-alerts",
]);

function highlightText(text, keyword) {
  if (!keyword || !text) return (text || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const safe = (text || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return safe.replace(new RegExp(`(${escaped})`, "gi"), "<mark>$1</mark>");
}

function barWidth(count, maxCount) {
  const max = maxCount || 1;
  return `${Math.max(8, Math.round((count / max) * 100))}%`;
}
</script>

<template>
  <section class="detail-page">
    <div class="detail-header">
      <div>
        <p class="eyebrow">Detail</p>
        <h2>{{ selectedLog?.filename || "未选择日志" }}</h2>
      </div>
      <div class="button-row">
        <span v-if="analysisLoading" class="tag tag-active">{{ analysisStatus === 'running' ? '分析中' : '排队中' }}</span>
        <span v-else class="tag">{{ selectedLog?.status }}</span>
        <span v-if="!aiConfigured" class="tag tag-warning">AI 未配置</span>
        <button class="primary-button" type="button" :disabled="!selectedLogId || analysisLoading || !aiConfigured" @click="$emit('analyze')">
          {{ analysisLoading ? "请稍候..." : "分析" }}
        </button>
        <button class="secondary-button" type="button" :disabled="!analysisResult" @click="$emit('export-analysis')">导出分析</button>
        <button class="secondary-button" type="button" :disabled="!selectedLog?.entries?.length" @click="$emit('export-entries')">导出条目</button>
        <button class="secondary-button" type="button" @click="$emit('back')">返回工作台</button>
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
            <dd>{{ selectedLog.size_bytes >= 0 ? `${(selectedLog.size_bytes / 1024).toFixed(1)} KB` : "-" }}</dd>
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

          <section v-if="logStats" class="stats-section">
            <div class="analysis-card">
              <h3>级别分布</h3>
              <div class="chart-bars">
                <div v-for="item in logStats.level_distribution" :key="item.level" class="chart-row">
                  <span class="chart-label">{{ item.level }}</span>
                  <div class="chart-bar-track">
                    <div
                      class="chart-bar-fill"
                      :class="`bar-${(item.level || '').toLowerCase()}`"
                      :style="{ width: barWidth(item.count, logStats.level_distribution[0]?.count) }"
                    >{{ item.count }}</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="analysis-card">
              <h3>服务/模块分布</h3>
              <div v-if="logStats.service_distribution.length === 0" class="inline-empty">未识别到服务名</div>
              <div v-else class="chart-bars">
                <div v-for="item in logStats.service_distribution" :key="item.service" class="chart-row">
                  <span class="chart-label">{{ item.service }}</span>
                  <div class="chart-bar-track">
                    <div class="chart-bar-fill" :style="{ width: barWidth(item.count, logStats.service_distribution[0]?.count) }">{{ item.count }}</div>
                  </div>
                </div>
              </div>
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

          <section class="analysis-card">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
              <h3 style="margin:0">告警规则</h3>
              <button class="secondary-button" type="button" @click="$emit('eval-alerts')" :disabled="!selectedLogId">评估规则</button>
            </div>

            <div v-if="alertResults?.alerts?.length" style="margin-top:10px;display:grid;gap:6px;">
              <div v-for="a in alertResults.alerts" :key="a.rule_id" class="alert-eval" :class="{ triggered: a.triggered }">
                {{ a.message }}
              </div>
            </div>

            <div style="margin-top:10px;display:grid;gap:6px;">
              <div v-for="rule in alertRules" :key="rule.id" class="alert-rule-row">
                <div>
                  <strong>{{ rule.name }}</strong>
                  <span v-if="rule.condition_level"> 级别={{ rule.condition_level }}</span>
                  <span v-if="rule.condition_keyword"> 关键词={{ rule.condition_keyword }}</span>
                  <span v-if="rule.condition_service"> 服务={{ rule.condition_service }}</span>
                  <span> 阈值={{ rule.threshold }}</span>
                </div>
                <button class="secondary-button" type="button" @click="$emit('delete-alert', rule.id)">删除</button>
              </div>
              <p v-if="!alertRules?.length" class="inline-empty">暂无告警规则</p>
            </div>

            <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:6px;">
              <input v-model="newRuleName" type="text" placeholder="规则名称" />
              <input v-model="newRuleLevel" type="text" placeholder="级别 (如 ERROR)" />
              <input v-model="newRuleKeyword" type="text" placeholder="关键词 (可选)" />
              <input v-model.number="newRuleThreshold" type="number" placeholder="阈值" min="1" />
            </div>
            <button class="primary-button" type="button" style="margin-top:8px;width:100%" @click="$emit('create-alert', { name: newRuleName, condition_level: newRuleLevel || null, condition_keyword: newRuleKeyword || null, threshold: newRuleThreshold || 1, enabled: true }); newRuleName=''; newRuleLevel=''; newRuleKeyword=''; newRuleThreshold=1;">
              添加规则
            </button>
          </section>

          <section v-if="analysisResult" class="ai-result-grid">
            <div class="analysis-card">
              <h3>AI 摘要</h3>
              <p class="analysis-text">{{ analysisResult.summary }}</p>
            </div>
            <div class="analysis-card analysis-card-warn">
              <h3>异常原因</h3>
              <ul class="analysis-list">
                <li v-for="(item, i) in (Array.isArray(analysisResult.causes) ? analysisResult.causes : [analysisResult.causes])" :key="`c-${i}`">{{ item }}</li>
              </ul>
            </div>
            <div class="analysis-card analysis-card-ok">
              <h3>排障建议</h3>
              <ul class="analysis-list">
                <li v-for="(item, i) in (Array.isArray(analysisResult.suggestions) ? analysisResult.suggestions : [analysisResult.suggestions])" :key="`s-${i}`">{{ item }}</li>
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
                <th>服务/模块</th>
                <th>内容</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in selectedLog?.entries || []" :key="entry.id" :class="{ key: entry.is_key_event }">
                <td>{{ entry.line_number }}</td>
                <td>{{ entry.timestamp || "-" }}</td>
                <td><span class="tag">{{ entry.level || "-" }}</span></td>
                <td>{{ entry.service_name || "-" }}</td>
                <td v-html="highlightText(entry.message, activeKeyword)"></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="entriesTotalPages > 1" class="pagination">
          <button class="secondary-button" type="button" :disabled="entriesPage <= 1" @click="$emit('go-page', entriesPage - 1)">上一页</button>
          <span class="pagination-info">{{ entriesPage }} / {{ entriesTotalPages }}</span>
          <button class="secondary-button" type="button" :disabled="entriesPage >= entriesTotalPages" @click="$emit('go-page', entriesPage + 1)">下一页</button>
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
              @click="$emit('select-history', record)"
            >
              <span class="history-time">{{ formatDate(record.analyzed_at) }}</span>
              <span class="tag">{{ record.id }}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>
