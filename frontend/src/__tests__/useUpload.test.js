import { describe, expect, it, vi } from "vitest";
import { useUpload } from "../composables/useUpload.js";

describe("useUpload", () => {
  it("starts with empty file list", () => {
    const { uploadFiles } = useUpload();
    expect(uploadFiles.value).toEqual([]);
  });

  it("is not loading initially", () => {
    const { uploadLoading } = useUpload();
    expect(uploadLoading.value).toBe(false);
  });

  it("handles file selection", () => {
    const { uploadFiles, onFileChange } = useUpload();
    const fakeFile = new File(["content"], "test.log", { type: "text/plain" });
    onFileChange({ target: { files: [fakeFile] } });
    expect(uploadFiles.value.length).toBe(1);
    expect(uploadFiles.value[0].name).toBe("test.log");
  });

  it("filters unsupported file types on drop", () => {
    const { uploadFiles, onDrop } = useUpload();
    const logFile = new File(["content"], "test.log", { type: "text/plain" });
    const imgFile = new File(["content"], "test.png", { type: "image/png" });

    onDrop({ dataTransfer: { files: [logFile, imgFile] } });
    expect(uploadFiles.value.length).toBe(1);
    expect(uploadFiles.value[0].name).toBe("test.log");
  });

  it("does not submit when no files selected", async () => {
    const requestApi = vi.fn();
    const { submitUpload } = useUpload(requestApi);
    await submitUpload();
    expect(requestApi).not.toHaveBeenCalled();
  });
});
