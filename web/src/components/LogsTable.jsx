import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Table,
  Select,
  Group,
  Text,
  Badge,
  Code,
  Tooltip,
  Center,
  Loader,
  ScrollArea,
  Stack,
  Button,
  Collapse,
  UnstyledButton,
  Box,
} from "@mantine/core";
import { useInterval } from "@mantine/hooks";
import { fetchLogs, clearLogs } from "../api.js";
import { notifications } from "@mantine/notifications";
import PayloadView from "./PayloadView.jsx";

const STATUS_COLORS = {
  200: "teal",
  429: "yellow",
  4006: "red",
  503: "orange",
  502: "red",
  error: "red",
};

const fmtTime = (ts) => {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-GB", { hour12: false }) + "." + String(d.getMilliseconds()).padStart(3, "0");
};

// Recent request log (ring buffer of the last N calls). Not persisted — clears
// on server restart. Auto-refreshes while the tab is visible.
export default function LogsTable() {
  const [logs, setLogs] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [endpointFilter, setEndpointFilter] = useState("all");
  const [expanded, setExpanded] = useState(null); // seq of the expanded row

  const load = useCallback(() => {
    fetchLogs()
      .then((r) => setLogs(r.logs))
      .catch(() => setLogs([]));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Faster refresh for logs (5s) — they're operational, time-sensitive.
  const interval = useInterval(load, 5000);
  useEffect(() => { interval.start(); return interval.stop; }, [interval]);

  const filtered = useMemo(() => {
    if (!logs) return [];
    let rows = logs;
    if (statusFilter !== "all") {
      if (statusFilter === "ok") rows = rows.filter((l) => l.status === 200);
      else if (statusFilter === "error") rows = rows.filter((l) => l.status !== 200);
      else rows = rows.filter((l) => String(l.status) === statusFilter);
    }
    if (endpointFilter !== "all") rows = rows.filter((l) => l.endpoint === endpointFilter);
    return rows;
  }, [logs, statusFilter, endpointFilter]);

  if (logs === null) {
    return (
      <Center h={200}>
        <Loader />
      </Center>
    );
  }

  const rows = filtered.map((l) => {
    const isOpen = expanded === l.seq;
    return [
      <Table.Tr key={l.seq}>
        <Table.Td>
          <UnstyledButton onClick={() => setExpanded(isOpen ? null : l.seq)}>
            <Text size="xs" ff="monospace" c={isOpen ? "blue" : "dimmed"}>
              {isOpen ? "▼" : "▶"} {fmtTime(l.ts)}
            </Text>
          </UnstyledButton>
        </Table.Td>
        <Table.Td>
          <Badge color={STATUS_COLORS[l.status] || "gray"} variant="light" size="sm">
            {String(l.status)}
          </Badge>
        </Table.Td>
        <Table.Td>
          <Text size="xs">{l.endpoint}{l.stream ? " · stream" : ""}</Text>
        </Table.Td>
        <Table.Td>
          <Code size="xs">{l.model || "—"}</Code>
        </Table.Td>
        <Table.Td>
          <Text size="xs">{l.account_name ? `#${l.account_id} ${l.account_name}` : "—"}</Text>
        </Table.Td>
        <Table.Td>
          {l.usage ? (
            <Text size="xs" c="dimmed">
              {l.usage.prompt_tokens ?? "?"}↑ / {l.usage.completion_tokens ?? "?"}↓
            </Text>
          ) : (
            <Text size="xs" c="dimmed">—</Text>
          )}
        </Table.Td>
        <Table.Td>
          <Text size="xs" c="dimmed">{l.latency_ms}ms</Text>
        </Table.Td>
        <Table.Td>
          <Tooltip label={l.error || ""} disabled={!l.error} withArrow>
            <Text size="xs" c="red" lineClamp={1}>{l.error_code ? `[${l.error_code}] ` : ""}{l.error || ""}</Text>
          </Tooltip>
        </Table.Td>
      </Table.Tr>,
      <Table.Tr key={`${l.seq}-detail`}>
        <Table.Td colSpan={8} p={0}>
          <Collapse in={isOpen}>
            <Box p="md" bg="var(--mantine-color-dark-7)">
              <Stack gap="md">
                <PayloadSection label="Client Request (Input)" color="blue">
                  <PayloadView body={l.client_request} kind="client" />
                </PayloadSection>
                <PayloadSection label="Provider Request (Translate)" color="violet">
                  <PayloadView body={l.provider_request} kind="provider" />
                </PayloadSection>
                <PayloadSection label="Provider Response (Final)" color="teal">
                  <PayloadView body={l.provider_response} kind="response" />
                </PayloadSection>
              </Stack>
            </Box>
          </Collapse>
        </Table.Td>
      </Table.Tr>,
    ];
  });

  return (
    <Stack gap="sm">
      <Group justify="space-between" wrap="wrap">
        <Group gap="sm">
          <Select
            data={[
              { value: "all", label: "All statuses" },
              { value: "ok", label: "200 OK" },
              { value: "429", label: "429" },
              { value: "error", label: "Errors" },
            ]}
            value={statusFilter}
            onChange={(v) => setStatusFilter(v || "all")}
            w={140}
          />
          <Select
            data={[
              { value: "all", label: "All endpoints" },
              { value: "chat", label: "chat" },
              { value: "embeddings", label: "embeddings" },
              { value: "run", label: "run" },
            ]}
            value={endpointFilter}
            onChange={(v) => setEndpointFilter(v || "all")}
            w={160}
          />
          <Text size="sm" c="dimmed">
            {filtered.length} / {logs.length} (last {logs.length})
          </Text>
        </Group>
        <Button
          variant="default"
          size="xs"
          onClick={async () => {
            try { await clearLogs(); load(); } catch {}
          }}
        >
          Clear
        </Button>
      </Group>

      <ScrollArea h={560}>
        <Table striped highlightOnHover withTableBorder minWidth={900}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Time</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Endpoint</Table.Th>
              <Table.Th>Model</Table.Th>
              <Table.Th>Account</Table.Th>
              <Table.Th>Tokens ↑/↓</Table.Th>
              <Table.Th>Latency</Table.Th>
              <Table.Th>Error</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {filtered.length > 0 ? (
              rows.flat()
            ) : (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Center p="lg">
                    <Text c="dimmed">No requests yet. Send a chat/embeddings/run request to populate.</Text>
                  </Center>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </ScrollArea>
    </Stack>
  );
}

// Labeled section wrapping a PayloadView (humanized) — colored left border.
function PayloadSection({ label, color, children }) {
  return (
    <Stack gap={4}>
      <Text size="xs" fw={700} c={color}>{label}</Text>
      <Box p="sm" bg="var(--mantine-color-dark-8)" bd="1px solid var(--mantine-color-dark-5)" style={{ borderRadius: 4, borderLeft: `3px solid var(--mantine-color-${color}-6)` }}>
        {children}
      </Box>
    </Stack>
  );
}
