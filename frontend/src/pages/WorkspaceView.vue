<script setup>
import { formatBytes, formatDate } from "../composables/useFormat.js";

defineProps({
  logs: Array,
  logsLoading: Boolean,
  selectedLogId: [Number, null],
  totalErrors: Number,
  totalWarnings: Number,
  uploadFiles: Array,
  isDragActive: Boolean,
  uploadLoading: Boolean,
  uploadResult: [Object, null],
  uploadProgress: Number,
  hasAppliedFilters: Boolean,
  appliedFilterTags: Array,
  keywordFilter: String,
  statusFilter: String,
  levelFilter: String,
  serviceFilter: String,
  startTimeFilter: String,
  endTimeFilter: String,
  logsPage: Number,
  logsTotalPages: Number,
  logsTotal: Number,
});

defineEmits([
  "select-log",
  "submit-upload",
  "file-change",
  "drag-enter",
  "drag-over",
  "drag-leave",
  "drop",
  "apply-filters",
  "clear-filters",
  "update:keywordFilter",
  "update:statusFilter",
  "update:levelFilter",
  "update:serviceFilter",
  "update:startTimeFilter",
  "update:endTimeFilter",
  "go-logs-page",
]);
</script>

<template>
  <section class="workspace-content">
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
          @dragenter.prevent="$emit('drag-enter')"
          @dragover.prevent="$emit('drag-over')"
          @dragleave.prevent="$emit('drag-leave', $event)"
          @drop.prevent="$emit('drop', $event)"
        >
          <label class="drop-label" for="log-file">
            <strong>{{ uploadFiles.length > 0 ? `已选择 ${uploadFiles.length} 个文件` : "拖入日志文件" }}</strong>
            <span>支持 .log / .txt，可一次选择多个文件</span>
          </label>
          <input id="log-file" class="file-input" type="file" accept=".log,.txt,text/plain" multiple @change="$emit('file-change', $event)" />
        </div>

        <ul v-if="uploadFiles.length > 0" class="selected-files">
          <li v-for="file in uploadFiles" :key="`${file.name}-${file.size}`">
            <span>{{ file.name }}</span>
            <em>{{ formatBytes(file.size) }}</em>
          </li>
        </ul>

        <button class="primary-button full-button" type="button" :disabled="uploadLoading" @click="$emit('submit-upload')">
          {{ uploadLoading ? `上传中 ${uploadProgress}%` : uploadFiles.length > 1 ? "批量上传并解析" : "上传并解析" }}
        </button>

        <div v-if="uploadLoading" class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: `${uploadProgress}%` }"></div>
        </div>

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
            <button class="secondary-button" type="button" :disabled="logsLoading" @click="$emit('clear-filters')">重置</button>
            <button class="primary-button" type="button" :disabled="logsLoading" @click="$emit('apply-filters')">
              {{ logsLoading ? "加载中" : "查询" }}
            </button>
          </div>
        </div>

        <div class="filter-grid">
          <label>
            <span>关键词</span>
            <input :value="keywordFilter" type="search" placeholder="文件名或日志内容" @input="$emit('update:keywordFilter', $event.target.value)" />
          </label>
          <label>
            <span>状态</span>
            <select :value="statusFilter" @change="$emit('update:statusFilter', $event.target.value)">
              <option value="">全部</option>
              <option value="parsed">parsed</option>
              <option value="analyzed">analyzed</option>
            </select>
          </label>
          <label>
            <span>服务/模块</span>
            <input :value="serviceFilter" type="search" placeholder="服务名关键词" @input="$emit('update:serviceFilter', $event.target.value)" />
          </label>
          <label>
            <span>级别</span>
            <select :value="levelFilter" @change="$emit('update:levelFilter', $event.target.value)">
              <option value="">全部</option>
              <option value="ERROR">ERROR</option>
              <option value="WARN">WARN</option>
              <option value="INFO">INFO</option>
              <option value="DEBUG">DEBUG</option>
              <option value="FATAL">FATAL</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </label>
          <label>
            <span>开始时间</span>
            <input :value="startTimeFilter" type="datetime-local" @input="$emit('update:startTimeFilter', $event.target.value)" />
          </label>
          <label>
            <span>结束时间</span>
            <input :value="endTimeFilter" type="datetime-local" @input="$emit('update:endTimeFilter', $event.target.value)" />
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
                @click="$emit('select-log', log.id)"
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

        <div v-if="logsTotalPages > 1" class="pagination">
          <button class="secondary-button" type="button" :disabled="logsPage <= 1" @click="$emit('go-logs-page', logsPage - 1)">上一页</button>
          <span class="pagination-info">{{ logsPage }} / {{ logsTotalPages }}（{{ logsTotal }} 条）</span>
          <button class="secondary-button" type="button" :disabled="logsPage >= logsTotalPages" @click="$emit('go-logs-page', logsPage + 1)">下一页</button>
        </div>
      </section>
    </section>
  </section>
</template>
