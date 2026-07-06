import { SimpleGrid, Card, Text, Progress, Group, Stack } from "@mantine/core";

function StatCard({ label, value, sub }) {
  return (
    <Card withBorder padding="md" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="xl" fw={700}>
        {value}
      </Text>
      {sub}
    </Card>
  );
}

const fmt = (n) => (n ?? 0).toLocaleString("en-US");

export default function StatsCards({ stats }) {
  const s = stats || {};
  const used = s.neurons_used_today ?? 0;
  const capacity = s.neurons_capacity_today ?? 0;
  const pct = capacity > 0 ? (used / capacity) * 100 : 0;

  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
      <StatCard label="Total accounts" value={fmt(s.total)} />
      <StatCard
        label="Available"
        value={fmt(s.available)}
        sub={
          <Text size="xs" c="dimmed">
            {fmt(s.cooldown)} in cooldown / exhausted
          </Text>
        }
      />
      <StatCard label="Requests today" value={fmt(s.requests_today)} />
      <Card withBorder padding="md" radius="md">
        <Stack gap={4}>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            Neurons today (est.)
          </Text>
          <Group justify="space-between" align="baseline">
            <Text size="xl" fw={700}>
              {fmt(used)}
            </Text>
            <Text size="xs" c="dimmed">
              / {fmt(capacity)}
            </Text>
          </Group>
          <Progress value={pct} color={pct > 90 ? "red" : pct > 70 ? "yellow" : "teal"} />
          <Text size="xs" c="dimmed">
            {fmt(s.neurons_remaining_today)} remaining
          </Text>
        </Stack>
      </Card>
    </SimpleGrid>
  );
}
