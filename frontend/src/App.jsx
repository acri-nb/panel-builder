import { BrowserRouter, Routes, Route } from "react-router-dom";

import HomePage from "./pages/HomePage";
import PanelDetailsPage from "./pages/PanelDetailsPage";
import ExternalUpdatesPage from "./pages/ExternalUpdatesPage";
import Navbar from "./components/Navbar";
import GroupedDiseasePage from "./pages/GroupedDiseasePage";
import LabPanelsPage from "./pages/LabPanelsPage";
import CreateLabPanelPage from "./pages/CreateLabPanelPage";
import EditLabPanelPage from "./pages/EditLabPanelPage";
import LabPanelChangesPage from "./pages/LabPanelChangesPage";
import LabPanelHistoryPage from "./pages/LabPanelHistoryPage";
import ExternalChangeDetailsPage from "./pages/ExternalChangeDetailsPage";
import CopyLabPanelPage from "./pages/CopyLabPanelPage.jsx";
import LabPanelSourceUpdatesPage from "./pages/LabPanelSourceUpdatesPage";

function App() {
  return (
    <BrowserRouter>


      <Navbar />


      <Routes>
        {/*http://localhost:5173/ shows the home page */}
        <Route path="/" element={<HomePage />} />
        {/*http://localhost:5173/panels/1 shows panel details*/}
        <Route path="/panels/:panelId" element={<PanelDetailsPage />} />
        {/*http://localhost:5173/external-updates shows external updates*/}
        <Route path="/external-updates" element={<ExternalUpdatesPage />} />
        <Route path="/external-updates/change/:changeId" element={<ExternalChangeDetailsPage />} />
        <Route path="/grouped-disease/:source/:name" element={<GroupedDiseasePage />} />
        <Route path="/lab-panels" element={<LabPanelsPage />} />
        <Route path="/lab-panels/create" element={<CreateLabPanelPage />} />
        <Route path="/lab-panels/:panelId/edit" element={<EditLabPanelPage />} />
        <Route path="/lab-panels/:panelId/changes" element={<LabPanelChangesPage />} />
        <Route path="/lab-panels/:panelId/history" element={<LabPanelHistoryPage />} />
        <Route path="/lab-panels/copy" element={<CopyLabPanelPage />} />
        <Route path="/lab-panels/:panelId/source-updates" element={<LabPanelSourceUpdatesPage />}/>
      </Routes>
    </BrowserRouter>
  );
}

export default App;