import { useState } from "react";
import { Button } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { runImport } from "../api.js";

// Manual 9router import. No inline <button> — Mantine Button component only.
export default function ImportButton({ onDone }) {
  const [loading, setLoading] = useState(false);

  async function handleImport() {
    setLoading(true);
    try {
      const r = await runImport();
      notifications.show({
        title: "Import complete",
        message: `${r.imported} imported, ${r.skipped} skipped — ${r.total} total`,
        color: "teal",
      });
      onDone?.();
    } catch (e) {
      notifications.show({ title: "Import failed", message: e.message, color: "red" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button onClick={handleImport} loading={loading} variant="filled">
      Import from 9router
    </Button>
  );
}
