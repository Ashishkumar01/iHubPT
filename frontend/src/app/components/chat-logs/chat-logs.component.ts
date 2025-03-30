import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MatDialog } from '@angular/material/dialog';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MaterialModule } from '../../shared/material.module';
import { ChatLogDetailsDialog } from './chat-log-details-dialog.component';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ChatLogService, ChatLog } from '../../services/chat-log.service';
import { AgentService } from '../../services/agent.service';
import { Subject, takeUntil } from 'rxjs';

interface Agent {
  id: string;
  name: string;
}

@Component({
  selector: 'app-chat-logs',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MaterialModule,
    ChatLogDetailsDialog,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule
  ],
  templateUrl: './chat-logs.component.html',
  styleUrls: ['./chat-logs.component.scss'],
  providers: [DatePipe]
})
export class ChatLogsComponent implements OnInit, OnDestroy {
  displayedColumns: string[] = [
    'timestamp',
    'agent_id',
    'user',
    'department',
    'request_message',
    'response_message',
    'input_tokens',
    'output_tokens',
    'total_tokens',
    'cost',
    'duration_ms',
    'status',
    'actions'
  ];
  
  dataSource: MatTableDataSource<ChatLog>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  startDate = new FormControl();
  endDate = new FormControl();
  agentFilter = new FormControl();
  statusFilter = new FormControl();

  agents: Agent[] = [];
  statuses = ['success', 'error'];
  loading = false;
  private destroy$ = new Subject<void>();

  constructor(
    private chatLogService: ChatLogService,
    private agentService: AgentService,
    private dialog: MatDialog,
    private datePipe: DatePipe
  ) {
    this.dataSource = new MatTableDataSource<ChatLog>([]);
  }

  ngOnInit() {
    this.loadChatLogs();
    this.loadAgents();
    
    // Set up filters
    this.dataSource.filterPredicate = this.createFilter();
    
    this.startDate.valueChanges.subscribe(() => this.applyFilter());
    this.endDate.valueChanges.subscribe(() => this.applyFilter());
    this.agentFilter.valueChanges.subscribe(() => this.applyFilter());
    this.statusFilter.valueChanges.subscribe(() => this.applyFilter());
  }

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadChatLogs() {
    this.loading = true;
    // Load all chat logs initially
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7); // Last 7 days by default

    this.chatLogService.getChatLogs(startDate, endDate)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (logs) => {
          console.log('Received chat logs:', logs);
          this.dataSource.data = logs.map(log => ({
            ...log,
            input_tokens: log.input_tokens || 0,
            output_tokens: log.output_tokens || 0,
            total_tokens: log.total_tokens || 0,
            cost: log.cost || 0,
            duration_ms: log.duration_ms || 0,
            user: log.user || 'Administrator',
            department: log.department || 'Post Trade'
          }));
          this.loading = false;
        },
        error: (error) => {
          console.error('Error loading chat logs:', error);
          this.loading = false;
        }
      });
  }

  loadAgents() {
    this.agentService.getAgents()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (agents) => {
          this.agents = agents;
        },
        error: (error) => {
          console.error('Error loading agents:', error);
        }
      });
  }

  createFilter(): (data: ChatLog, filter: string) => boolean {
    return (data: ChatLog, filter: string): boolean => {
      const searchTerms = JSON.parse(filter);
      
      const timestampValid = !searchTerms.startDate || !searchTerms.endDate || 
        (new Date(data.timestamp) >= new Date(searchTerms.startDate) &&
         new Date(data.timestamp) <= new Date(searchTerms.endDate));
      
      const agentValid = !searchTerms.agent || data.agent_id === searchTerms.agent;
      const statusValid = !searchTerms.status || data.status === searchTerms.status;

      return timestampValid && agentValid && statusValid;
    };
  }

  applyFilter() {
    const filterValue = {
      startDate: this.startDate.value,
      endDate: this.endDate.value,
      agent: this.agentFilter.value,
      status: this.statusFilter.value
    };
    
    this.dataSource.filter = JSON.stringify(filterValue);
  }

  formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  }

  formatTimestamp(timestamp: string): string {
    return this.datePipe.transform(timestamp, 'MMM d, y HH:mm:ss') || timestamp;
  }

  formatCost(cost: number): string {
    return `$${cost.toFixed(4)}`;
  }

  viewDetails(log: ChatLog) {
    this.dialog.open(ChatLogDetailsDialog, {
      width: '800px',
      data: log
    });
  }

  clearFilters() {
    this.startDate.reset();
    this.endDate.reset();
    this.agentFilter.reset();
    this.statusFilter.reset();
    this.dataSource.filter = '';
  }

  getAgentName(agentId: string): string {
    const agent = this.agents.find(a => a.id === agentId);
    return agent ? agent.name : agentId;
  }
} 