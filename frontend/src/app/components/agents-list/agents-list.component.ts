import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../shared/material.module';
import { AgentService, Tool } from '../../services/agent.service';
import { Agent, AgentStatus } from '../../models/agent';
import { MatTooltipModule } from '@angular/material/tooltip';
import { CreateAgentDialogComponent } from '../create-agent-dialog/create-agent-dialog.component';
import { EditAgentDialogComponent } from '../edit-agent-dialog/edit-agent-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';

@Component({
  selector: 'app-agents-list',
  standalone: true,
  imports: [
    CommonModule,
    MaterialModule,
    MatTooltipModule,
    MatTableModule,
    MatMenuModule,
    MatIconModule,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatChipsModule
  ],
  templateUrl: './agents-list.component.html',
  styleUrls: ['./agents-list.component.scss']
})
export class AgentsListComponent implements OnInit, OnDestroy {
  agents: Agent[] = [];
  loading = true;
  displayedColumns: string[] = ['name', 'description', 'tools', 'status', 'actions'];
  AgentStatus = AgentStatus;
  private destroy$ = new Subject<void>();
  private toolDescriptions: Map<string, string> = new Map();

  constructor(
    private agentService: AgentService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadAgents();
    this.loadTools();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadAgents(): void {
    this.loading = true;
    this.agentService.getAgents()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (agents) => {
          this.agents = agents;
          this.loading = false;
        },
        error: (error) => {
          console.error('Error loading agents:', error);
          this.loading = false;
          this.snackBar.open('Failed to load agents', 'Close', { duration: 3000 });
        }
      });
  }

  loadTools(): void {
    this.agentService.getAvailableTools()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (tools) => {
          tools.forEach(tool => {
            this.toolDescriptions.set(tool.name, tool.description);
          });
        },
        error: (error) => {
          console.error('Error loading tools:', error);
        }
      });
  }

  getToolDescription(toolName: string): string {
    return this.toolDescriptions.get(toolName) || toolName;
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(CreateAgentDialogComponent, {
      width: '600px'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.agentService.createAgent(result).subscribe({
          next: () => {
            this.loadAgents();
            this.snackBar.open('Agent created successfully', 'Close', { duration: 3000 });
          },
          error: (error) => {
            console.error('Error creating agent:', error);
            this.snackBar.open('Failed to create agent', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  editAgent(agent: Agent): void {
    const dialogRef = this.dialog.open(EditAgentDialogComponent, {
      width: '600px',
      data: agent
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.agentService.updateAgent(agent.id, result).subscribe({
          next: () => {
            this.loadAgents();
            this.snackBar.open('Agent updated successfully', 'Close', { duration: 3000 });
          },
          error: (error) => {
            console.error('Error updating agent:', error);
            this.snackBar.open('Failed to update agent', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  deleteAgent(agent: Agent): void {
    if (confirm(`Are you sure you want to delete agent "${agent.name}"?`)) {
      this.agentService.deleteAgent(agent.id).subscribe({
        next: () => {
          this.loadAgents();
          this.snackBar.open('Agent deleted successfully', 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Error deleting agent:', error);
          this.snackBar.open('Failed to delete agent', 'Close', { duration: 3000 });
        }
      });
    }
  }

  startAgent(agent: Agent): void {
    this.agentService.startAgent(agent.id).subscribe({
      next: () => {
        this.loadAgents();
        this.snackBar.open('Agent started successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Error starting agent:', error);
        this.snackBar.open('Failed to start agent', 'Close', { duration: 3000 });
      }
    });
  }

  pauseAgent(agent: Agent): void {
    this.agentService.pauseAgent(agent.id).subscribe({
      next: () => {
        this.loadAgents();
        this.snackBar.open('Agent paused successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Error pausing agent:', error);
        this.snackBar.open('Failed to pause agent', 'Close', { duration: 3000 });
      }
    });
  }

  resumeAgent(agent: Agent): void {
    this.agentService.resumeAgent(agent.id).subscribe({
      next: () => {
        this.loadAgents();
        this.snackBar.open('Agent resumed successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Error resuming agent:', error);
        this.snackBar.open('Failed to resume agent', 'Close', { duration: 3000 });
      }
    });
  }

  viewAgent(agent: Agent, event: MouseEvent): void {
    // Ignore if clicking on action buttons
    if ((event.target as HTMLElement).closest('.mat-mdc-menu-trigger, .mat-mdc-menu-item')) {
      return;
    }
    this.router.navigate(['/agents', agent.id]);
  }
} 