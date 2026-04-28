import { computed, ref } from "vue";

export function useFilters(onApply) {
  const keywordFilter = ref("");
  const statusFilter = ref("");
  const levelFilter = ref("");
  const serviceFilter = ref("");
  const startTimeFilter = ref("");
  const endTimeFilter = ref("");
  const appliedFilters = ref({ keyword: "", status: "", level: "", service: "", startTime: "", endTime: "" });

  const hasAppliedFilters = computed(() =>
    Boolean(appliedFilters.value.keyword || appliedFilters.value.status || appliedFilters.value.level || appliedFilters.value.service || appliedFilters.value.startTime || appliedFilters.value.endTime),
  );

  const appliedFilterTags = computed(() => {
    const tags = [];
    if (appliedFilters.value.keyword) tags.push(`关键词：${appliedFilters.value.keyword}`);
    if (appliedFilters.value.status) tags.push(`状态：${appliedFilters.value.status}`);
    if (appliedFilters.value.level) tags.push(`级别：${appliedFilters.value.level}`);
    if (appliedFilters.value.service) tags.push(`服务：${appliedFilters.value.service}`);
    if (appliedFilters.value.startTime) tags.push(`开始：${appliedFilters.value.startTime}`);
    if (appliedFilters.value.endTime) tags.push(`结束：${appliedFilters.value.endTime}`);
    return tags;
  });

  function buildLogQuery() {
    const query = new URLSearchParams();
    const f = appliedFilters.value;
    if (f.keyword) query.set("keyword", f.keyword);
    if (f.status) query.set("status", f.status);
    if (f.level) query.set("level", f.level);
    if (f.service) query.set("service", f.service);
    if (f.startTime) query.set("start_time", f.startTime);
    if (f.endTime) query.set("end_time", f.endTime);
    const qs = query.toString();
    return qs ? `?${qs}` : "";
  }

  async function applyFilters() {
    appliedFilters.value = {
      keyword: keywordFilter.value.trim(),
      status: statusFilter.value,
      level: levelFilter.value,
      service: serviceFilter.value.trim(),
      startTime: startTimeFilter.value.trim(),
      endTime: endTimeFilter.value.trim(),
    };
    if (onApply) await onApply();
  }

  async function clearFilters() {
    keywordFilter.value = "";
    statusFilter.value = "";
    levelFilter.value = "";
    serviceFilter.value = "";
    startTimeFilter.value = "";
    endTimeFilter.value = "";
    appliedFilters.value = { keyword: "", status: "", level: "", service: "", startTime: "", endTime: "" };
    if (onApply) await onApply();
  }

  return {
    keywordFilter, statusFilter, levelFilter, serviceFilter, startTimeFilter, endTimeFilter,
    appliedFilters, hasAppliedFilters, appliedFilterTags,
    buildLogQuery, applyFilters, clearFilters,
  };
}
