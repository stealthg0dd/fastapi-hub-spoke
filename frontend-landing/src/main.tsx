// Force Cache Invalidation - Build V2
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "./styles/neufin-overrides.css"; // MUST be last — wins cascade over all @layer rules

createRoot(document.getElementById("root")!).render(<App />);
