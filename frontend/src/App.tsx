import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { VoiceProvider } from "./context/VoiceContext";
import { AboutPage } from "./pages/AboutPage";
import { ConversationsPage } from "./pages/ConversationsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { IntroPage } from "./pages/IntroPage";
import { SettingsPage } from "./pages/SettingsPage";

/** Root index component: directs first-time visitors to /intro; returning users to Dashboard. */
function DashboardIndex() {
  const seen = typeof window !== "undefined" && sessionStorage.getItem("intro_seen");
  if (!seen) {
    return <Navigate to="/intro" replace />;
  }
  return <DashboardPage />;
}

export default function App() {
  return (
    <VoiceProvider>
      <Routes>
        {/* Standalone intro — rendered without the sidebar AppLayout */}
        <Route path="intro" element={<IntroPage />} />

        {/* Main application shell */}
        <Route element={<AppLayout />}>
          <Route index element={<DashboardIndex />} />
          <Route path="conversations" element={<ConversationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </VoiceProvider>
  );
}
