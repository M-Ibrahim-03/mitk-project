import { Link, Route, Routes, useParams } from "react-router-dom";

import { ChatPage } from "./pages/ChatPage";
import { WorkflowPage } from "./pages/WorkflowPage";

function NotFoundPage() {
  return (
    <main className="page-shell">
      <section className="surface-card empty-state">
        <span className="eyebrow">VEIL · LOCAL DEMO</span>
        <h1>Page not found</h1>
        <p>This page does not match a Veil demo screen.</p>
        <Link className="text-link" to="/">
          Back to chat
        </Link>
      </section>
    </main>
  );
}

function WorkflowRoute() {
  const { runId } = useParams();
  return <WorkflowPage runId={runId ?? ""} />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="/runs/:runId" element={<WorkflowRoute />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
