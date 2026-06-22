import { Navigate, Outlet, useRoutes, type RouteObject } from "react-router-dom";

import { AdminRoute } from "./guards/AdminRoute";
import { ProtectedRoute } from "./guards/ProtectedRoute";
import { AdminShell } from "./shell/AdminShell";
import { AuthenticatedShell } from "./shell/AuthenticatedShell";
import { PublicShell } from "./shell/PublicShell";
import { AdminHomePage } from "../features/admin/pages/AdminHomePage";
import { AccountPage } from "../features/account/pages/AccountPage";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { RegisterPage } from "../features/auth/pages/RegisterPage";
import { DashboardPage } from "../features/dashboard/pages/DashboardPage";
import { ChangesPage } from "../features/changes/pages/ChangesPage";
import { ChatPage } from "../features/chat/pages/ChatPage";
import { DocumentDetailPage } from "../features/documents/pages/DocumentDetailPage";
import { DocumentsPage } from "../features/documents/pages/DocumentsPage";
import { EntitiesPage } from "../features/entities/pages/EntitiesPage";
import { EntityDetailPage } from "../features/entities/pages/EntityDetailPage";
import { HomePage } from "../features/marketing/pages/HomePage";
import { SearchPage } from "../features/search/pages/SearchPage";
import { SpacesPage } from "../features/spaces/pages/SpacesPage";
import { TrackedStatePage } from "../features/tracked-state/pages/TrackedStatePage";

export const appRoutes: RouteObject[] = [
  {
    element: <PublicShell />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> }
    ]
  },
  {
    element: (
      <ProtectedRoute>
        <AuthenticatedShell />
      </ProtectedRoute>
    ),
    children: [
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/spaces", element: <SpacesPage /> },
      { path: "/documents", element: <DocumentsPage /> },
      { path: "/documents/:documentId", element: <DocumentDetailPage /> },
      { path: "/search", element: <SearchPage /> },
      { path: "/chat", element: <ChatPage /> },
      { path: "/chat/:sessionId", element: <ChatPage /> },
      { path: "/entities", element: <EntitiesPage /> },
      { path: "/entities/:entityId", element: <EntityDetailPage /> },
      { path: "/tracked-state", element: <TrackedStatePage /> },
      { path: "/changes", element: <ChangesPage /> },
      { path: "/account", element: <AccountPage /> }
    ]
  },
  {
    element: (
      <AdminRoute>
        <AdminShell />
      </AdminRoute>
    ),
    children: [{ path: "/admin", element: <AdminHomePage /> }]
  },
  {
    path: "*",
    element: <Navigate to="/" replace />
  }
];

export function AppRouter() {
  return useRoutes(appRoutes) ?? <Outlet />;
}
