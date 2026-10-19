import { Conversation } from "../components/Conversation";

export function ConversationsPage() {
  return <div className="route-page"><header className="page-header"><p className="overline">Workspace</p><h1>Conversations</h1><p>Review the current session and continue by voice or text.</p></header><Conversation expanded /></div>;
}
