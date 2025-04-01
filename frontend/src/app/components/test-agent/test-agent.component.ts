import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { AgentService } from '../../services/agent.service';
import { Agent, AgentStatus } from '../../models/agent';
import { EditAgentDialogComponent } from '../edit-agent-dialog/edit-agent-dialog.component';

interface ChatResponse {
  content: string;
}

@Component({
  selector: 'app-test-agent',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatIconModule,
    MatMenuModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatDividerModule
  ],
  templateUrl: './test-agent.component.html',
  styleUrls: ['./test-agent.component.scss']
})
export class TestAgentComponent implements OnInit, OnDestroy {
  agents: Agent[] = [];
  selectedAgent: Agent | null = null;
  messages: Array<{ role: 'user' | 'assistant', content: string, timestamp: Date }> = [];
  newMessage: string = '';
  isLoading: boolean = false;
  AgentStatus = AgentStatus;
  private statusSubscription: Subscription | null = null;

  constructor(
    public route: ActivatedRoute,
    private agentService: AgentService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadAgents();
    const agentId = this.route.snapshot.paramMap.get('id');
    if (agentId) {
      this.selectAgent(agentId);
    }
  }

  ngOnDestroy(): void {
    this.stopStatusPolling();
  }

  loadAgents(): void {
    this.agentService.getAgents().subscribe({
      next: (agents) => {
        this.agents = agents;
      },
      error: (error) => {
        console.error('Error loading agents:', error);
        this.snackBar.open('Failed to load agents', 'Close', { duration: 3000 });
      }
    });
  }

  selectAgent(agentId: string): void {
    this.agentService.getAgent(agentId).subscribe({
      next: (agent) => {
        this.selectedAgent = agent;
        if (agent.context?.chat_history) {
          this.messages = agent.context.chat_history.map(msg => ({
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            timestamp: new Date(msg.timestamp)
          }));
        } else {
          this.messages = [];
        }
        this.startStatusPolling(agent.id);
      },
      error: (error) => {
        console.error('Error loading agent:', error);
        this.snackBar.open('Failed to load agent details', 'Close', { duration: 3000 });
      }
    });
  }

  startStatusPolling(agentId: string): void {
    this.stopStatusPolling();
    this.statusSubscription = interval(5000)
      .pipe(
        takeWhile(() => this.selectedAgent?.id === agentId),
        switchMap(() => this.agentService.getAgent(agentId))
      )
      .subscribe({
        next: (agent) => {
          if (this.selectedAgent) {
            this.selectedAgent = agent;
          }
        },
        error: (error) => {
          console.error('Error polling agent status:', error);
        }
      });
  }

  stopStatusPolling(): void {
    if (this.statusSubscription) {
      this.statusSubscription.unsubscribe();
      this.statusSubscription = null;
    }
  }

  startAgent(): void {
    if (!this.selectedAgent) return;
    this.agentService.startAgent(this.selectedAgent.id).subscribe({
      next: (agent: Agent) => {
        this.selectedAgent = agent;
        this.snackBar.open('Agent started successfully', 'Close', { duration: 3000 });
      },
      error: (error: Error) => {
        console.error('Error starting agent:', error);
        this.snackBar.open('Failed to start agent', 'Close', { duration: 3000 });
      }
    });
  }

  stopAgent(): void {
    if (!this.selectedAgent) return;
    this.agentService.stopAgent(this.selectedAgent.id).subscribe({
      next: (agent: Agent) => {
        this.selectedAgent = agent;
        this.snackBar.open('Agent stopped successfully', 'Close', { duration: 3000 });
      },
      error: (error: Error) => {
        console.error('Error stopping agent:', error);
        this.snackBar.open('Failed to stop agent', 'Close', { duration: 3000 });
      }
    });
  }

  sendMessage(): void {
    if (!this.selectedAgent || !this.newMessage.trim()) return;

    const message = this.newMessage.trim();
    const timestamp = new Date();
    
    this.messages.push({ 
      role: 'user', 
      content: message, 
      timestamp: timestamp 
    });
    this.newMessage = '';
    this.isLoading = true;

    if (!this.selectedAgent.context) {
      this.selectedAgent.context = {};
    }
    if (!this.selectedAgent.context.chat_history) {
      this.selectedAgent.context.chat_history = [];
    }
    
    this.selectedAgent.context.chat_history.push({
      role: 'user',
      content: message,
      timestamp: timestamp.toISOString()
    });

    this.agentService.sendMessage(this.selectedAgent.id, message).subscribe({
      next: (response: ChatResponse) => {
        const responseTimestamp = new Date();
        
        this.messages.push({
          role: 'assistant',
          content: response.content,
          timestamp: responseTimestamp
        });
        
        if (this.selectedAgent && this.selectedAgent.context?.chat_history) {
          this.selectedAgent.context.chat_history.push({
            role: 'assistant',
            content: response.content,
            timestamp: responseTimestamp.toISOString()
          });
        }
        
        this.isLoading = false;
      },
      error: (error: Error) => {
        console.error('Error sending message:', error);
        this.snackBar.open('Failed to send message', 'Close', { duration: 3000 });
        this.isLoading = false;
      }
    });
  }

  canSendMessage(): boolean {
    if (!this.selectedAgent) return false;
    return this.selectedAgent.status === AgentStatus.RUNNING || 
           this.selectedAgent.status === AgentStatus.COMPLETED;
  }

  openEditDialog(): void {
    if (!this.selectedAgent) return;

    const dialogRef = this.dialog.open(EditAgentDialogComponent, {
      data: this.selectedAgent,
      width: '600px',
      autoFocus: true,
      restoreFocus: true,
      ariaLabel: 'Edit Agent Dialog'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        console.log('Selected agent ID:', this.selectedAgent?.id);
        console.log('Update data:', result);
        
        if (!this.selectedAgent?.id) {
          console.error('No agent ID available');
          this.snackBar.open('Error: Missing agent ID', 'Close', { duration: 5000 });
          return;
        }

        this.agentService.updateAgent(this.selectedAgent.id, result).subscribe({
          next: (updatedAgent: Agent) => {
            console.log('Agent updated successfully:', updatedAgent);
            this.selectedAgent = updatedAgent;
            this.snackBar.open('Agent updated successfully', 'Close', { duration: 3000 });
          },
          error: (error: any) => {
            console.error('Error updating agent:', error);
            this.snackBar.open(
              error.error?.detail || 'Failed to update agent. Please try again.',
              'Close',
              { duration: 5000 }
            );
          }
        });
      }
    });
  }
} 