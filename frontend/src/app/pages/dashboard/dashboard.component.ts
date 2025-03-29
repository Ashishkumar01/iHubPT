import { Component, OnInit } from '@angular/core';
import { AgentService } from '../../services/agent.service';
import { Agent, AgentStatus } from '../../models/agent';
import { MaterialModule } from '../../shared/material.module';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [MaterialModule, CommonModule, MatProgressSpinnerModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  agents: Agent[] = [];
  runningAgents: Agent[] = [];
  pausedAgents: Agent[] = [];
  isLoading = false;
  error: string | null = null;
  displayedColumns: string[] = ['name', 'status', 'actions'];

  constructor(private agentService: AgentService) {}

  ngOnInit(): void {
    this.loadAgents();
  }

  private loadAgents(): void {
    this.isLoading = true;
    this.error = null;
    
    this.agentService.getAgents().subscribe({
      next: (agents) => {
        this.agents = agents;
        this.runningAgents = agents.filter(agent => agent.status === AgentStatus.RUNNING);
        this.pausedAgents = agents.filter(agent => agent.status === AgentStatus.PAUSED);
        this.isLoading = false;
      },
      error: (error) => {
        this.error = 'Failed to load agents. Please try again later.';
        console.error('Error loading agents:', error);
        this.isLoading = false;
      }
    });
  }
} 