import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MatDialog } from '@angular/material/dialog';
import { MatMenuTrigger } from '@angular/material/menu';
import { Router } from '@angular/router';
import { AgentService } from '../../services/agent.service';
import { Agent, AgentStatus } from '../../models/agent';
import { MaterialModule } from '../../shared/material.module';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CreateAgentDialogComponent } from '../../components/create-agent-dialog/create-agent-dialog.component';

@Component({
  selector: 'app-agents',
  standalone: true,
  imports: [MaterialModule, CommonModule, FormsModule, MatProgressSpinnerModule],
  templateUrl: './agents.component.html',
  styleUrls: ['./agents.component.scss']
})
export class AgentsComponent implements OnInit, AfterViewInit {
  displayedColumns: string[] = ['name', 'description', 'status', 'hitl_enabled', 'created_at', 'actions'];
  dataSource: MatTableDataSource<Agent>;
  loading = false;
  error: string | null = null;
  AgentStatus = AgentStatus; // Make enum available in template

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatMenuTrigger) menuTrigger!: MatMenuTrigger;

  constructor(
    private agentService: AgentService,
    private dialog: MatDialog,
    private router: Router
  ) {
    this.dataSource = new MatTableDataSource<Agent>();
  }

  ngOnInit(): void {
    this.loadAgents();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private loadAgents(): void {
    this.loading = true;
    this.error = null;
    
    this.agentService.getAgents().subscribe({
      next: (agents) => {
        this.dataSource.data = agents;
        this.loading = false;
      },
      error: (error) => {
        this.error = 'Failed to load agents. Please try again later.';
        console.error('Error loading agents:', error);
        this.loading = false;
      }
    });
  }

  applyFilter(event: Event): void {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  startAgent(agent: Agent): void {
    if (agent.id) {
      this.loading = true;
      this.agentService.startAgent(agent.id).subscribe({
        next: () => {
          this.loadAgents();
        },
        error: (error) => {
          this.error = 'Failed to start agent. Please try again.';
          console.error('Error starting agent:', error);
          this.loading = false;
        }
      });
    }
  }

  pauseAgent(agent: Agent): void {
    if (agent.id) {
      this.loading = true;
      this.agentService.pauseAgent(agent.id).subscribe({
        next: () => {
          this.loadAgents();
        },
        error: (error) => {
          this.error = 'Failed to pause agent. Please try again.';
          console.error('Error pausing agent:', error);
          this.loading = false;
        }
      });
    }
  }

  resumeAgent(agent: Agent): void {
    if (agent.id) {
      this.loading = true;
      this.agentService.resumeAgent(agent.id).subscribe({
        next: () => {
          this.loadAgents();
        },
        error: (error) => {
          this.error = 'Failed to resume agent. Please try again.';
          console.error('Error resuming agent:', error);
          this.loading = false;
        }
      });
    }
  }

  getStatusColor(status: AgentStatus): string {
    switch (status) {
      case AgentStatus.RUNNING:
        return 'primary';
      case AgentStatus.PAUSED:
        return 'accent';
      case AgentStatus.IDLE:
        return 'warn';
      default:
        return '';
    }
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(CreateAgentDialogComponent, {
      width: '500px'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loading = true;
        this.agentService.createAgent(result).subscribe({
          next: () => {
            this.loadAgents();
          },
          error: (error) => {
            this.error = 'Failed to create agent. Please try again.';
            console.error('Error creating agent:', error);
            this.loading = false;
          }
        });
      }
    });
  }

  deleteAgent(agent: Agent): void {
    if (agent.id) {
      this.loading = true;
      this.agentService.deleteAgent(agent.id).subscribe({
        next: () => {
          this.loadAgents();
        },
        error: (error) => {
          this.error = 'Failed to delete agent. Please try again.';
          console.error('Error deleting agent:', error);
          this.loading = false;
        }
      });
    }
  }

  viewAgent(agent: Agent, event: Event): void {
    console.log('Clicked agent:', agent);
    // Stop event propagation if clicking on action buttons
    if (event?.target instanceof HTMLElement && 
        (event.target.closest('button') || event.target.closest('mat-menu'))) {
      console.log('Clicked on action button or menu, ignoring navigation');
      return;
    }
    if (!agent.id) {
      console.log('No agent ID found');
      return;
    }
    console.log('Navigating to agent:', agent.id);
    this.router.navigate(['/agents', agent.id]);
  }
} 