import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import AddInventory from "./pages/AddInventory";
import InventoryList from "./pages/InventoryList";
import SalesHistory from "./pages/SalesHistory";
import Settings from "./pages/Settings";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/add", label: "Add Cards" },
  { to: "/inventory", label: "Inventory" },
  { to: "/sales", label: "Sales" },
  { to: "/settings", label: "Settings" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <header className="bg-[#111111] border-b border-[#2a2a2a] px-6 py-3 flex items-center gap-8">
        <span className="text-xl font-bold text-red-500">NottMyTradeBinder</span>
        <nav className="flex gap-1">
          {nav.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `text-sm px-3 py-1.5 rounded transition-colors ${
                  isActive
                    ? "bg-red-700 text-white"
                    : "text-neutral-400 hover:text-white hover:bg-[#1e1e1e]"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/add" element={<AddInventory />} />
          <Route path="/inventory" element={<InventoryList />} />
          <Route path="/sales" element={<SalesHistory />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
