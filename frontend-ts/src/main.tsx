import React from "react";
import ReactDOM from "react-dom/client";

import AuthShell from "./AuthShell";
import { applyShellWallpaper } from "./shellAppearance";
import { ensureProfessionalThemePreset } from "./shellTheme";
import "./styles.css";

applyShellWallpaper();
ensureProfessionalThemePreset();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthShell />
  </React.StrictMode>,
);
