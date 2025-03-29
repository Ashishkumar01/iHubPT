import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AgentService } from '../../services/agent.service';
import { Agent, AgentStatus } from '../../models/agent';
import { MaterialModule } from '../../shared/material.module';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MaterialModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    RouterModule
  ],
  template: `
    <div class="dashboard-container">
      <!-- Loading Spinner -->
      <div class="loading-container" *ngIf="isLoading">
        <mat-spinner diameter="48"></mat-spinner>
      </div>

      <!-- Error Message -->
      <div class="error-content" *ngIf="error">
        <mat-icon>error</mat-icon>
        <span>{{error}}</span>
      </div>

      <!-- Dashboard Content -->
      <div class="dashboard-content" *ngIf="!isLoading && !error">
        <!-- Summary Cards -->
        <div class="summary-cards">
          <mat-card>
            <mat-card-header>
              <mat-card-title>Active Agents</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="stat-value">{{runningAgents.length}}</div>
            </mat-card-content>
          </mat-card>

          <mat-card>
            <mat-card-header>
              <mat-card-title>Paused Agents</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="stat-value">{{pausedAgents.length}}</div>
            </mat-card-content>
          </mat-card>

          <mat-card>
            <mat-card-header>
              <mat-card-title>Total Agents</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="stat-value">{{agents.length}}</div>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Recent Agents Table -->
        <mat-card class="recent-agents">
          <mat-card-header>
            <mat-card-title>Recent Agents</mat-card-title>
            <div class="header-actions">
              <button mat-button color="primary" routerLink="/agents">
                View All
                <mat-icon>chevron_right</mat-icon>
              </button>
            </div>
          </mat-card-header>
          <mat-card-content>
            <table mat-table [dataSource]="agents.slice(0, 5)">
              <!-- Name Column -->
              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef>Name</th>
                <td mat-cell *matCellDef="let agent">{{agent.name}}</td>
              </ng-container>

              <!-- Status Column -->
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let agent">
                  <span class="status-badge" [class.active]="agent.status === AgentStatus.RUNNING">
                    {{agent.status}}
                  </span>
                </td>
              </ng-container>

              <!-- Actions Column -->
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Actions</th>
                <td mat-cell *matCellDef="let agent">
                  <button mat-icon-button [routerLink]="['/agents', agent.id]">
                    <mat-icon>visibility</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container {
      padding: 20px;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 200px;
    }

    .error-content {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #f44336;
      padding: 16px;
    }

    .summary-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 20px;
    }

    .stat-value {
      font-size: 2.5rem;
      font-weight: 500;
      text-align: center;
      padding: 20px 0;
    }

    .recent-agents {
      margin-top: 20px;
    }

    .header-actions {
      margin-left: auto;
    }

    table {
      width: 100%;
    }

    .status-badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      background-color: #f5f5f5;
      color: #666;
    }

    .status-badge.active {
      background-color: #e8f5e9;
      color: #2e7d32;
    }

    mat-card-header {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
    }
  `]
})
export class DashboardComponent implements OnInit {
  agents: Agent[] = [];
  runningAgents: Agent[] = [];
  pausedAgents: Agent[] = [];
  isLoading = false;
  error: string | null = null;
  displayedColumns: string[] = ['name', 'status', 'actions'];
  AgentStatus = AgentStatus;

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