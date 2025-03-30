import { Component, Inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MaterialModule } from '../../shared/material.module';

@Component({
  selector: 'app-chat-log-details-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MaterialModule
  ],
  template: `
    <h2 mat-dialog-title>Chat Log Details</h2>
    <mat-dialog-content class="chat-log-details-dialog">
      <!-- Stats Section -->
      <div class="stats-section">
        <div class="stat-item">
          <div class="stat-label">Input Tokens</div>
          <div class="stat-value">{{data.input_tokens}}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Output Tokens</div>
          <div class="stat-value">{{data.output_tokens}}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Total Tokens</div>
          <div class="stat-value">{{data.total_tokens}}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Cost</div>
          <div class="stat-value">{{formatCost(data.cost)}}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Duration</div>
          <div class="stat-value">{{formatDuration(data.duration_ms)}}</div>
        </div>
      </div>

      <!-- Messages Section -->
      <div class="message-section">
        <div class="message-label">Request Message</div>
        <div class="message-content">{{data.request_message}}</div>
      </div>

      <div class="message-section">
        <div class="message-label">Response Message</div>
        <div class="message-content">{{data.response_message}}</div>
      </div>

      <!-- Additional Info -->
      <div class="message-section">
        <div class="message-label">Additional Information</div>
        <div class="message-content">
          <div><strong>Timestamp:</strong> {{formatTimestamp(data.timestamp)}}</div>
          <div><strong>Model:</strong> {{data.model_name}}</div>
          <div><strong>Requestor:</strong> {{data.requestor_id}}</div>
          <div><strong>Status:</strong> {{data.status}}</div>
          <div *ngIf="data.error_message"><strong>Error:</strong> {{data.error_message}}</div>
        </div>
      </div>

      <!-- Metadata Section -->
      <div class="metadata-section" *ngIf="data.metadata">
        <div class="message-label">Metadata</div>
        <pre>{{formatMetadata(data.metadata)}}</pre>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Close</button>
    </mat-dialog-actions>
  `,
  providers: [DatePipe]
})
export class ChatLogDetailsDialog {
  constructor(
    @Inject(MAT_DIALOG_DATA) public data: any,
    private datePipe: DatePipe
  ) {}

  formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  }

  formatTimestamp(timestamp: string): string {
    return this.datePipe.transform(timestamp, 'MMM d, y HH:mm:ss') || timestamp;
  }

  formatMetadata(metadata: any): string {
    return JSON.stringify(metadata, null, 2);
  }

  formatCost(cost: number): string {
    return `$${cost.toFixed(4)}`;
  }
} 