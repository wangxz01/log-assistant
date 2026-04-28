<script setup>
defineProps({
  lastResponse: [Object, String, null],
  formatJson: Function,
});
</script>

<template>
  <section class="panel response-panel">
    <div class="section-heading">
      <div>
        <p class="eyebrow">Response</p>
        <h2>最近响应</h2>
      </div>
    </div>
    <pre>{{ formatJson(lastResponse) || "暂无响应" }}</pre>
  </section>
</template>
