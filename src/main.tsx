import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import Workspace from './Workspace';
import ProjectMonitor from './project-monitor/ProjectMonitor';
import './index.css';

const monitor = window.location.pathname === '/monitor' || window.location.pathname === '/status';
createRoot(document.getElementById('root')!).render(
  <StrictMode>{monitor ? <ProjectMonitor /> : <Workspace />}</StrictMode>
);
