import { useMemo, useState } from "react";
import {
  Table,
  Progress,
  Badge,
  Group,
  Pagination,
  TextInput,
  Select,
  Text,
  Center,
  UnstyledButton,
} from "@mantine/core";

const PAGE_SIZE = 25;

const STATUS_COLORS = {
  available: "teal",
  cooldown: "yellow",
  exhausted: "red",
  inactive: "gray",
};

// Sortable header cell — UnstyledButton (component, not inline button).
function SortHeader({ label, field, sort, onSort }) {
  const active = sort.field === field;
  const arrow = active ? (sort.dir === "asc" ? " ▲" : " ▼") : "";
  return (
    <Table.Th>
      <UnstyledButton onClick={() => onSort(field)} fw={700}>
        <Text span size="sm" fw={700}>
          {label}
          {arrow}
        </Text>
      </UnstyledButton>
    </Table.Th>
  );
}

export default function AccountsTable({ accounts }) {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sort, setSort] = useState({ field: "id", dir: "asc" });

  function onSort(field) {
    setSort((s) =>
      s.field === field ? { field, dir: s.dir === "asc" ? "desc" : "asc" } : { field, dir: "asc" }
    );
    setPage(1);
  }

  const filtered = useMemo(() => {
    let rows = accounts;
    if (statusFilter !== "all") rows = rows.filter((a) => a.status === statusFilter);
    const q = query.trim().toLowerCase();
    if (q) {
      rows = rows.filter(
        (a) =>
          (a.name || "").toLowerCase().includes(q) ||
          a.account_id.toLowerCase().includes(q) ||
          String(a.id).includes(q)
      );
    }
    const { field, dir } = sort;
    const mul = dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = a[field];
      const bv = b[field];
      if (typeof av === "string") return av.localeCompare(bv) * mul;
      return (av - bv) * mul;
    });
  }, [accounts, statusFilter, query, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const slice = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const rows = slice.map((a) => {
    const pct = (a.neurons_today / a.neurons_free_daily) * 100;
    return (
      <Table.Tr key={a.id}>
        <Table.Td>{a.id}</Table.Td>
        <Table.Td>{a.name || "—"}</Table.Td>
        <Table.Td>
          <Text span ff="monospace" size="xs">
            {a.account_id}…
          </Text>
        </Table.Td>
        <Table.Td>
          <Badge color={STATUS_COLORS[a.status] || "gray"} variant="light">
            {a.status}
          </Badge>
        </Table.Td>
        <Table.Td w={180}>
          <Progress.Root size="lg">
            <Progress.Section
              value={Math.min(100, pct)}
              color={pct > 90 ? "red" : pct > 70 ? "yellow" : "teal"}
            >
              <Progress.Label>{Math.round(pct)}%</Progress.Label>
            </Progress.Section>
          </Progress.Root>
          <Text size="xs" c="dimmed">
            {a.neurons_today.toLocaleString()} / {a.neurons_free_daily.toLocaleString()}
          </Text>
        </Table.Td>
        <Table.Td>{a.neurons_remaining.toLocaleString()}</Table.Td>
        <Table.Td>{a.requests_today}</Table.Td>
      </Table.Tr>
    );
  });

  return (
    <>
      <Group justify="space-between" mb="sm" wrap="wrap">
        <TextInput
          placeholder="Search name / account / id"
          value={query}
          onChange={(e) => {
            setQuery(e.currentTarget.value);
            setPage(1);
          }}
          w={280}
        />
        <Select
          data={[
            { value: "all", label: "All statuses" },
            { value: "available", label: "Available" },
            { value: "cooldown", label: "Cooldown" },
            { value: "exhausted", label: "Exhausted" },
            { value: "inactive", label: "Inactive" },
          ]}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v || "all");
            setPage(1);
          }}
          w={180}
        />
      </Group>

      <Table.ScrollContainer minWidth={720}>
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <SortHeader label="#" field="id" sort={sort} onSort={onSort} />
              <SortHeader label="Name" field="name" sort={sort} onSort={onSort} />
              <Table.Th>Account</Table.Th>
              <SortHeader label="Status" field="status" sort={sort} onSort={onSort} />
              <SortHeader label="Neurons today" field="neurons_today" sort={sort} onSort={onSort} />
              <SortHeader label="Remaining" field="neurons_remaining" sort={sort} onSort={onSort} />
              <SortHeader label="Reqs" field="requests_today" sort={sort} onSort={onSort} />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.length > 0 ? (
              rows
            ) : (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Center p="lg">
                    <Text c="dimmed">No accounts. Click “Import from 9router”.</Text>
                  </Center>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      <Group justify="space-between" mt="md">
        <Text size="sm" c="dimmed">
          {filtered.length.toLocaleString()} accounts
        </Text>
        <Pagination total={pageCount} value={safePage} onChange={setPage} />
      </Group>
    </>
  );
}
