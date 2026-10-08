import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoopDrawer } from "./components/LoopDrawer";
import "./index.css";
import { NewMeeting } from "./pages/NewMeeting";
import { Reliability } from "./pages/Reliability";
import { Worklist } from "./pages/Worklist";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
});

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Worklist />, children: [{ path: "loops/:loopId", element: <LoopDrawer /> }] },
      { path: "/reliability", element: <Reliability /> },
      { path: "/meetings/new", element: <NewMeeting /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
