import { ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

export function useUpload(getToken, onUploaded) {
  const uploadFiles = ref([]);
  const isDragActive = ref(false);
  const uploadLoading = ref(false);
  const uploadResult = ref(null);
  const uploadProgress = ref(0);

  function isSupportedLogFile(file) {
    const filename = file.name.toLowerCase();
    return filename.endsWith(".log") || filename.endsWith(".txt") || file.type === "text/plain";
  }

  function uploadViaXhr(url, formData) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${apiBaseUrl}${url}`);
      xhr.withCredentials = true;

      const token = getToken();
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) uploadProgress.value = Math.round((e.loaded / e.total) * 100);
      });

      xhr.addEventListener("load", () => {
        let body;
        try { body = JSON.parse(xhr.responseText); } catch { body = xhr.responseText; }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body);
        } else {
          const detail = body?.detail || `上传失败：${xhr.status}`;
          reject(new Error(detail));
        }
      });

      xhr.addEventListener("error", () => reject(new Error("无法连接到服务器")));
      xhr.addEventListener("abort", () => reject(new Error("上传已取消")));
      xhr.send(formData);
    });
  }

  async function submitUpload() {
    if (uploadFiles.value.length === 0) return;
    uploadLoading.value = true;
    uploadProgress.value = 0;

    try {
      const formData = new FormData();
      const isBatch = uploadFiles.value.length > 1;
      for (const file of uploadFiles.value) {
        formData.append(isBatch ? "files" : "file", file);
      }
      uploadResult.value = await uploadViaXhr(isBatch ? "/logs/upload/batch" : "/logs/upload", formData);
      const latest = isBatch ? uploadResult.value.items.at(-1) : uploadResult.value;
      if (onUploaded) await onUploaded(latest.id);
    } catch {
      uploadResult.value = null;
    } finally {
      uploadLoading.value = false;
      uploadProgress.value = 0;
    }
  }

  function onFileChange(event) {
    uploadFiles.value = Array.from(event.target.files || []);
  }

  function onDragEnter() { isDragActive.value = true; }

  function onDragLeave(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) isDragActive.value = false;
  }

  function onDrop(event) {
    isDragActive.value = false;
    uploadFiles.value = Array.from(event.dataTransfer?.files || []).filter(isSupportedLogFile);
  }

  return {
    uploadFiles, isDragActive, uploadLoading, uploadResult, uploadProgress,
    submitUpload, onFileChange, onDragEnter, onDragLeave, onDrop,
  };
}
