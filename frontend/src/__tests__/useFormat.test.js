import { describe, expect, it } from "vitest";
import { formatBytes, formatDate, formatJson, splitItems } from "../composables/useFormat.js";

describe("formatBytes", () => {
  it("returns 0 B for falsy values", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(null)).toBe("0 B");
    expect(formatBytes(undefined)).toBe("0 B");
  });

  it("formats bytes correctly", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(20480)).toBe("20.0 KB");
  });
});

describe("formatDate", () => {
  it("returns - for falsy values", () => {
    expect(formatDate(null)).toBe("-");
    expect(formatDate("")).toBe("-");
  });

  it("formats ISO date strings", () => {
    const result = formatDate("2026-04-28T10:00:00Z");
    expect(result).toBeTruthy();
    expect(typeof result).toBe("string");
  });
});

describe("formatJson", () => {
  it("returns empty string for falsy values", () => {
    expect(formatJson(null)).toBe("");
    expect(formatJson(undefined)).toBe("");
    expect(formatJson("")).toBe("");
  });

  it("returns strings as-is", () => {
    expect(formatJson("hello")).toBe("hello");
  });

  it("stringifies objects", () => {
    const result = formatJson({ key: "value" });
    expect(result).toBe('{\n  "key": "value"\n}');
  });
});

describe("splitItems", () => {
  it("returns empty array for falsy values", () => {
    expect(splitItems(null)).toEqual([]);
    expect(splitItems("")).toEqual([]);
  });

  it("splits on double newlines", () => {
    expect(splitItems("item1\n\nitem2\n\nitem3")).toEqual(["item1", "item2", "item3"]);
  });

  it("handles single items", () => {
    expect(splitItems("single item")).toEqual(["single item"]);
  });

  it("trims whitespace from items", () => {
    expect(splitItems("  item1  \n\n  item2  ")).toEqual(["item1", "item2"]);
  });
});
