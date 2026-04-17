import { ChatWithTree } from "./chat-with-tree";

/**
 * Unified chat + Hub tree (DASH-01).
 *
 * Server component: delegates interactive content to the client composite
 * (chat-panel + hub-tree share a right-pane viewer state). Access control
 * is handled by middleware (session OR DASHBOARD_TOKEN).
 */
export const dynamic = "force-dynamic";

export default function ChatPage() {
  return (
    <div className="-m-6 flex h-[calc(100vh-3.5rem)]">
      <ChatWithTree />
    </div>
  );
}
