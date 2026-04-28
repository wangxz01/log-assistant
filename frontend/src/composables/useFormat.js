export function formatJson(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function formatBytes(value) {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  return `${(value / 1024).toFixed(1)} KB`;
}

export function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export function splitItems(text) {
  if (!text) return [];
  return text.split(/\n{2,}/).map((s) => s.trim()).filter(Boolean);
}
