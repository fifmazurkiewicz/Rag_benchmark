import { Routes, Route, NavLink } from "react-router-dom";
import ExperimentsPage from "./pages/ExperimentsPage";
import RunPage from "./pages/RunPage";
import DashboardPage from "./pages/DashboardPage";
import DatasetsPage from "./pages/DatasetsPage";
import LeaderboardPage from "./pages/LeaderboardPage";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded text-sm font-medium transition-colors ${
    isActive ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"
  }`;

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <span className="text-lg font-bold text-indigo-400">RAG Benchmark</span>
        <nav className="flex gap-2">
          <NavLink to="/" end className={navClass}>Experiments</NavLink>
          <NavLink to="/datasets" className={navClass}>Datasets</NavLink>
          <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>
          <NavLink to="/leaderboard" className={navClass}>Leaderboard</NavLink>
        </nav>
      </header>
      <main className="flex-1 p-6">
        <Routes>
          <Route path="/" element={<ExperimentsPage />} />
          <Route path="/run/:runId" element={<RunPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/datasets" element={<DatasetsPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
