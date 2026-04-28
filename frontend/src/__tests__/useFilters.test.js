import { describe, expect, it } from "vitest";
import { useFilters } from "../composables/useFilters.js";

describe("useFilters", () => {
  it("starts with no applied filters", () => {
    const { hasAppliedFilters } = useFilters();
    expect(hasAppliedFilters.value).toBe(false);
  });

  it("builds empty query string when no filters applied", () => {
    const { buildLogQuery } = useFilters();
    expect(buildLogQuery()).toBe("");
  });

  it("builds query string with keyword", () => {
    const { keywordFilter, applyFilters, buildLogQuery } = useFilters();
    keywordFilter.value = "timeout";
    // applyFilters sets appliedFilters synchronously
    applyFilters();
    expect(buildLogQuery()).toContain("keyword=timeout");
  });

  it("builds query string with status", () => {
    const { statusFilter, applyFilters, buildLogQuery } = useFilters();
    statusFilter.value = "analyzed";
    applyFilters();
    expect(buildLogQuery()).toContain("status=analyzed");
  });

  it("generates correct filter tags", () => {
    const { keywordFilter, statusFilter, applyFilters, appliedFilterTags } = useFilters();
    keywordFilter.value = "error";
    statusFilter.value = "parsed";
    applyFilters();
    expect(appliedFilterTags.value).toEqual(["关键词：error", "状态：parsed"]);
  });

  it("clears all filters", async () => {
    const { keywordFilter, statusFilter, applyFilters, clearFilters, hasAppliedFilters } = useFilters();
    keywordFilter.value = "test";
    statusFilter.value = "parsed";
    await applyFilters();
    expect(hasAppliedFilters.value).toBe(true);

    await clearFilters();
    expect(hasAppliedFilters.value).toBe(false);
    expect(keywordFilter.value).toBe("");
    expect(statusFilter.value).toBe("");
  });
});
