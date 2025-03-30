import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { 
    path: 'dashboard', 
    loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent),
    title: 'Dashboard'
  },
  { 
    path: 'agents', 
    loadComponent: () => import('./components/agents-list/agents-list.component').then(m => m.AgentsListComponent),
    title: 'Agents'
  },
  {
    path: 'agents/:id',
    loadComponent: () => import('./components/test-agent/test-agent.component').then(m => m.TestAgentComponent),
    title: 'Chat with Agent'
  },
  { 
    path: 'chat-logs', 
    loadComponent: () => import('./components/chat-logs/chat-logs.component').then(m => m.ChatLogsComponent),
    title: 'Chat Logs'
  },
  { 
    path: 'tools', 
    loadComponent: () => import('./components/tools/tools.component').then(m => m.ToolsComponent),
    title: 'Tools'
  },
  { path: '**', redirectTo: '/dashboard' }
];
