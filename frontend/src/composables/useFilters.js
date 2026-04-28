import { computed, ref } from "vue";

export function useFilters(onApply) {
  const keywordFilter = ref("");
  const statusFilter = ref("");
  const startTimeFilter = ref("");
  const endTimeFilter = ref("");
  const appliedFilters = ref({ keyword: "", status: "", startTime: "", endTime: "" });

  const hasAppliedFilters = computed(() =>
    Boolean(appliedFilters.value.keyword || appliedFilters.value.status || appliedFilters.value.startTime || appliedFilters.value.endTime),
  );

  const appliedFilterTags = computed(() => {
    const tags = [];
    if (appliedFilters.value.keyword) tags.push(`关键词：${appliedFilters.value.keyword}`);
    if (appliedFilters.value.status) tags.push(`状态：${appliedFilters.value.status}`);
    if (appliedFilters.value.startTime) tags.push(`开始：${appliedFilters.value.startTime}`);
    if (appliedFilters.value.endTime) tags.push(`结束：${appliedFilters.value.endTime}`);
    return tags;
  });

  function buildLogQuery() {
    const query = new URLSearchParams();
    const f = appliedFilters.value;
    if (f.keyword) query.set("keyword", f.keyword);
    if (f.status) query.set("status", f.status);
    if (f.startTime) query.set("start_time", f.startTime);
    if (f.endTime) query.set("end_time", f.endTime);
    const qs = query.toString();
    return qs ? `?${qs}` : "";
  }

  async function applyFilters() {
    appliedFilters.value = {
      keyword: keywordFilter.value.trim(),
      status: statusFilter.value,
      startTime: startTimeFilter.value.trim(),
      endTime: endTimeFilter.value.trim(),
    };
    if (onApply) await onApply();
  }

  async function clearFilters() {
    keywordFilter.value = "";
    statusFilter.value = "";
    startTimeFilter.value = "";
    endTimeFilter.value = "";
    appliedFilters.value = { keyword: "", status: "", startTime: "", endTime: "" };
    if (onApply) await onApply();
  }

  return {
    keywordFilter, statusFilter, startTimeFilter, endTimeFilter,
    appliedFilters, hasAppliedFilters, appliedFilterTags,
    buildLogQuery, applyFilters, clearFilters,
  };
}
