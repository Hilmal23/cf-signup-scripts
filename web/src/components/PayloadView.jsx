import { useMemo, useState } from "react";
import {
  Box,
  Stack,
  Text,
  Badge,
  Code,
  Group,
  Collapse,
  UnstyledButton,
  ScrollArea,
  ThemeIcon,
} from "@mantine/core";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

const ROLE_COLORS = {
  system: "violet",
  user: "blue",
  assistant: "teal",
  tool: "orange",
};

function tryParse(s) {
  if (!s || typeof s !== "string") return null;
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

// Pull reasoning (tag) out of content, return { reasoning, answer }.
function splitReasoning(content) {
  if (typeof content !== "string") return { reasoning: null, answer: content };
  const m = content.match(/^\s*([\s\S]*?)<\/think>\s*([\s\S]*)$/);
  if (m) return { reasoning: m[1].trim(), answer: m[2].trim() };
  return { reasoning: null, answer: content };
}

function fmtToolCall(tc) {
  if (!tc?.function) return JSON.stringify(tc);
  let args = tc.function.arguments;
  try {
    args = JSON.stringify(JSON.parse(args));
  } catch {
    /* keep raw */
  }
  return `${tc.function.name}(${args})`;
}

function Collapsible({ label, count, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Stack gap={4}>
      <UnstyledButton onClick={() => setOpen((o) => !o)}>
        <Text size="xs" fw={700}>
          {open ? "▾" : "▸"} {label}{count != null ? ` (${count})` : ""}
        </Text>
      </UnstyledButton>
      <Collapse in={open}>{children}</Collapse>
    </Stack>
  );
}

function Bubble({ role, children }) {
  return (
    <Group align="flex-start" gap="xs" wrap="nowrap">
      <Badge color={ROLE_COLORS[role] || "gray"} variant="light" size="sm" w={70} justify="center">
        {role}
      </Badge>
      <Box style={{ flex: 1, minWidth: 0 }}>
        {children}
      </Box>
    </Group>
  );
}

// Render message content — markdown for assistant, plain for user/tool.
function Content({ content, role, asMarkdown }) {
  if (content == null || content === "") return <Text size="sm" c="dimmed" fs="italic">(empty)</Text>;
  const str = typeof content === "string" ? content : JSON.stringify(content);
  if (asMarkdown && role === "assistant") {
    return (
      <Box className="payload-markdown" style={{ fontSize: 13, lineHeight: 1.5 }}>
        <Markdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ className, children, ...rest }) {
              const isBlock = /language-/.test(className || "");
              return isBlock ? (
                <Code block {...rest}>{String(children).replace(/\n$/, "")}</Code>
              ) : (
                <Code {...rest}>{children}</Code>
              );
            },
            a({ href, children, ...rest }) {
              return <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>{children}</a>;
            },
          }}
        >
          {str}
        </Markdown>
      </Box>
    );
  }
  return <Text size="sm" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.5 }}>{str}</Text>;
}

// Render the tools array (function definitions from a request).
function ToolsPanel({ tools }) {
  if (!tools?.length) return null;
  return (
    <Collapsible label="Tools" count={tools.length}>
      <Stack gap={4} pl="md">
        {tools.map((t, i) => {
          const fn = t.function || t;
          const params = fn.parameters?.properties || {};
          const required = fn.parameters?.required || [];
          const paramStr = Object.keys(params)
            .map((p) => `${p}${required.includes(p) ? "*" : ""}: ${params[p].type || "any"}`)
            .join(", ");
          return (
            <Group key={i} gap="xs" wrap="nowrap">
              <ThemeIcon size="xs" variant="light" color="orange">⚙</ThemeIcon>
              <Code size="xs" color="orange">{fn.name}</Code>
              <Text size="xs" c="dimmed">({paramStr || "no params"})</Text>
            </Group>
          );
        })}
      </Stack>
    </Collapsible>
  );
}

// Render a chat-shaped object (has .messages or .choices[0].message).
function ChatView({ obj, isResponse }) {
  const messages = isResponse
    ? obj?.choices?.map((c) => c.message).filter(Boolean)
    : obj?.messages;

  if (!messages?.length) {
    return <Text size="sm" c="dimmed" fs="italic">(no messages)</Text>;
  }

  return (
    <Stack gap="sm">
      {/* System prompt(s) as boxes on top */}
      {messages.filter((m) => m.role === "system").map((m, i) => (
        <Box key={`s${i}`} p="sm" bg="var(--mantine-color-violet-1)" style={{ borderRadius: 6, borderLeft: "3px solid var(--mantine-color-violet-6)" }} c="dark">
          <Text size="xs" fw={700} c="violet" mb={4}>SYSTEM</Text>
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{typeof m.content === "string" ? m.content : JSON.stringify(m.content)}</Text>
        </Box>
      ))}

      {/* Non-system messages as bubbles */}
      {messages.filter((m) => m.role !== "system").map((m, i) => {
        const { reasoning, answer } = splitReasoning(m.content);
        const toolCalls = m.tool_calls;
        return (
          <Stack key={`m${i}`} gap={4}>
            <Bubble role={m.role}>
              <Stack gap={4}>
                {/* tool_calls inline */}
                {toolCalls?.length > 0 && (
                  <Box>
                    {toolCalls.map((tc, j) => (
                      <Group key={j} gap={4} wrap="nowrap">
                        <Text size="xs" c="teal" fw={700}>→ calls</Text>
                        <Code size="xs" c="teal">{fmtToolCall(tc)}</Code>
                      </Group>
                    ))}
                  </Box>
                )}
                {/* reasoning split (assistant only) */}
                {reasoning && m.role === "assistant" && (
                  <Collapsible label="Reasoning" defaultOpen={false}>
                    <Box p="sm" bg="var(--mantine-color-gray-1)" style={{ borderRadius: 4 }} c="dimmed">
                      <Text size="xs" style={{ whiteSpace: "pre-wrap", fontFamily: "monospace" }}>{reasoning}</Text>
                    </Box>
                  </Collapsible>
                )}
                {/* answer/content */}
                {answer != null && answer !== "" && (
                  <Content content={answer} role={m.role} asMarkdown={m.role === "assistant"} />
                )}
                {/* tool result without content */}
                {!answer && !toolCalls?.length && (
                  <Content content={m.content} role={m.role} asMarkdown={false} />
                )}
              </Stack>
            </Bubble>
          </Stack>
        );
      })}
    </Stack>
  );
}

export default function PayloadView({ body, kind }) {
  // kind: "client" | "provider" | "response"
  const obj = useMemo(() => tryParse(body), [body]);

  if (!body) {
    return <Text size="xs" c="dimmed" fs="italic">(none)</Text>;
  }
  if (!obj) {
    // Non-JSON (e.g. "[SSE stream]" or truncated/raw) — show as-is.
    return (
      <ScrollArea.Autosize mah={240} type="auto">
        <Box p="sm" bg="var(--mantine-color-dark-8)" style={{ borderRadius: 4 }}>
          <Code block style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 11 }}>{body}</Code>
        </Box>
      </ScrollArea.Autosize>
    );
  }

  const isResponse = kind === "response";
  const isChat = obj?.messages || obj?.choices?.[0]?.message;

  if (!isChat) {
    // Non-chat JSON (embeddings, /ai/run result, etc.) — pretty JSON.
    return (
      <ScrollArea.Autosize mah={240} type="auto">
        <Box p="sm" bg="var(--mantine-color-dark-8)" style={{ borderRadius: 4 }}>
          <Code block style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 11 }}>
            {JSON.stringify(obj, null, 2)}
          </Code>
        </Box>
      </ScrollArea.Autosize>
    );
  }

  return (
    <Stack gap="sm">
      {/* Tools (request only — definitions the client sent) */}
      {!isResponse && obj.tools?.length > 0 && <ToolsPanel tools={obj.tools} />}

      {/* Metadata strip for chat: model, max_tokens, temperature, etc. */}
      <Group gap="md" wrap="wrap">
        {obj.model && <Group gap={4}><Text size="xs" c="dimmed">Model:</Text><Code size="xs">{obj.model}</Code></Group>}
        {obj.max_tokens != null && <Text size="xs" c="dimmed">Max tokens: {obj.max_tokens}</Text>}
        {obj.temperature != null && <Text size="xs" c="dimmed">Temp: {obj.temperature}</Text>}
        {obj.stream && <Badge size="xs" variant="light">stream</Badge>}
        {isResponse && obj.usage && (
          <Group gap={4}>
            <Text size="xs" c="dimmed">Usage:</Text>
            <Text size="xs">{obj.usage.prompt_tokens}↑ / {obj.usage.completion_tokens}↓</Text>
          </Group>
        )}
      </Group>

      <ChatView obj={obj} isResponse={isResponse} />
    </Stack>
  );
}
