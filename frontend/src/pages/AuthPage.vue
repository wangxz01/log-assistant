<script setup>
defineProps({
  health: Object,
  sessionLoading: Boolean,
  isAuthenticated: Boolean,
  authMode: String,
  authEmail: String,
  authPassword: String,
  authLoading: Boolean,
  errorMessage: String,
  authNotice: String,
  apiStatusText: String,
});

defineEmits([
  "update:authMode",
  "update:authEmail",
  "update:authPassword",
  "submit",
]);
</script>

<template>
  <main v-if="sessionLoading" class="auth-page">
    <section class="auth-panel">
      <div class="auth-brand">
        <div class="brand-mark">LA</div>
        <div>
          <p class="eyebrow">Log Assistant</p>
          <h1>正在恢复登录状态</h1>
        </div>
      </div>
      <div class="auth-footer">
        <span class="status-dot" :class="{ online: health?.status === 'ok' }"></span>
        <span>{{ apiStatusText }}</span>
      </div>
    </section>
  </main>

  <main v-else-if="!isAuthenticated" class="auth-page">
    <section class="auth-panel">
      <div class="auth-brand">
        <div class="brand-mark">LA</div>
        <div>
          <p class="eyebrow">Log Assistant</p>
          <h1>登录日志分析平台</h1>
        </div>
      </div>

      <div class="auth-tabs" role="tablist" aria-label="认证方式">
        <button :class="{ active: authMode === 'login' }" type="button" @click="$emit('update:authMode', 'login')">登录</button>
        <button :class="{ active: authMode === 'register' }" type="button" @click="$emit('update:authMode', 'register')">注册</button>
      </div>

      <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>
      <p v-if="authNotice" class="notice-banner">{{ authNotice }}</p>

      <form class="auth-form" @submit.prevent="$emit('submit')">
        <label class="field-label" for="email">邮箱</label>
        <input id="email" :value="authEmail" type="email" autocomplete="email" @input="$emit('update:authEmail', $event.target.value)" />

        <label class="field-label" for="password">密码</label>
        <input
          id="password"
          :value="authPassword"
          type="password"
          :autocomplete="authMode === 'register' ? 'new-password' : 'current-password'"
          minlength="8"
          @input="$emit('update:authPassword', $event.target.value)"
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
</template>
