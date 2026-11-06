import { NavLink, Outlet, createBrowserRouter } from "react-router";

import { Home } from "@/pages/Home";
import { Profile } from "@/pages/Profile";
import { Settings } from "@/pages/Settings";
import { Usage } from "@/pages/Usage";

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "font-medium text-slate-900" : "text-slate-500 hover:text-slate-900";

function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <span className="font-semibold">Tailor</span>
          <NavLink to="/" end className={navClass}>
            Accueil
          </NavLink>
          <NavLink to="/profil" className={navClass}>
            Profil
          </NavLink>
          <NavLink to="/consommation" className={navClass}>
            Consommation
          </NavLink>
          <NavLink to="/reglages" className={navClass}>
            Réglages
          </NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "profil", element: <Profile /> },
      { path: "consommation", element: <Usage /> },
      { path: "reglages", element: <Settings /> },
    ],
  },
]);
