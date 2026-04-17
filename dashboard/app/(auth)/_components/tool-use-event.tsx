"use client";

import {
  Terminal,
  FileText,
  Folder,
  Globe,
  Hammer,
  Pencil,
  Search,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Inline renderer for a single chat stream frame.
 *
 * Frames:
 *   - { type: "text", content: string }               → markdown paragraph
 *   - { type: "tool_use", tool: string, input: any }  → tool invocation card
 *   - { type: "tool_result", tool: string, output: any } → result card
 *   - { type: "end" }                                  → ignored (upstream)
 *   - { type: "error", message: string }               → error card
 *
 * Markdown: react-markdown + remark-gfm. NO `rehype-raw` — raw HTML is
 * rejected to neutralise T-13-40 (XSS in assistant tokens). No
 * `dangerouslySetInnerHTML` anywhere in this component tree.
 */

// Map lucide icons to canonical tool names from claude-code-sdk.
const TOOL_ICON: Record<string, typeof Terminal> = {
  Bash: Terminal,
  Read: FileText,
  Write: FileText,
  Edit: Pencil,
  Glob: Folder,
  Grep: Search,
  WebFetch: Globe,
  WebSearch: Search,
  TodoWrite: Pencil,
};

function iconFor(tool: string) {
  const cmp = TOOL_ICON[tool] ?? Wrench;
  return cmp;
}

export type ToolUseEventProps = {
  type: "text" | "tool_use" | "tool_result" | "error" | "raw";
  content?: string;
  tool?: string;
  input?: unknown;
  output?: unknown;
  data?: string;
  message?: string;
};

export function ToolUseEvent(props: ToolUseEventProps) {
  if (props.type === "text" && typeof props.content === "string") {
    return (
      <div
        className="prose prose-invert max-w-none text-sm leading-relaxed"
        data-testid="chat-text"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {props.content}
        </ReactMarkdown>
      </div>
    );
  }

  if (props.type === "tool_use") {
    const tool = props.tool ?? "unknown";
    const Icon = iconFor(tool);
    return (
      <Card
        data-testid="chat-tool-use"
        className="border-primary/30 bg-muted/30"
      >
        <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-2">
          <Hammer className="size-4 text-muted-foreground" />
          <Icon className="size-4 text-primary" />
          <CardTitle className="font-mono text-xs">{tool}</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded bg-background/50 p-2 text-xs">
            {JSON.stringify(props.input ?? {}, null, 2)}
          </pre>
        </CardContent>
      </Card>
    );
  }

  if (props.type === "tool_result") {
    const tool = props.tool ?? "unknown";
    const Icon = iconFor(tool);
    const out =
      typeof props.output === "string"
        ? props.output
        : JSON.stringify(props.output ?? null, null, 2);
    return (
      <Card
        data-testid="chat-tool-result"
        className="border-muted-foreground/20"
      >
        <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-2">
          <Icon className="size-4 text-muted-foreground" />
          <CardTitle className="font-mono text-xs text-muted-foreground">
            {tool} result
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-48 overflow-auto rounded bg-background/50 p-2 text-xs">
            {out}
          </pre>
        </CardContent>
      </Card>
    );
  }

  if (props.type === "error") {
    return (
      <Card className="border-destructive/40 bg-destructive/5">
        <CardContent className="py-3 text-sm text-destructive">
          {props.message ?? "Stream error"}
        </CardContent>
      </Card>
    );
  }

  return null;
}
