import { ref } from "vue";

export function useUpload(requestApi, onUploaded) {
  const uploadFiles = ref([]);
  const isDragActive = ref(false);
  const uploadLoading = ref(false);
  const uploadResult = ref(null);

  function isSupportedLogFile(file) {
    const filename = file.name.toLowerCase();
    return filename.endsWith(".log") || filename.endsWith(".txt") || file.type === "text/plain";
  }

  async function submitUpload() {
    if (uploadFiles.value.length === 0) return;
    uploadLoading.value = true;

    try {
      const formData = new FormData();
      const isBatch = uploadFiles.value.length > 1;
      for (const file of uploadFiles.value) {
        formData.append(isBatch ? "files" : "file", file);
      }
      uploadResult.value = await requestApi(isBatch ? "/logs/upload/batch" : "/logs/upload", {
        method: "POST",
        body: formData,
      });
      const latest = isBatch ? uploadResult.value.items.at(-1) : uploadResult.value;
      if (onUploaded) await onUploaded(latest.id);
    } catch {
      uploadResult.value = null;
    } finally {
      uploadLoading.value = false;
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
    uploadFiles, isDragActive, uploadLoading, uploadResult,
    submitUpload, onFileChange, onDragEnter, onDragLeave, onDrop,
  };
}
