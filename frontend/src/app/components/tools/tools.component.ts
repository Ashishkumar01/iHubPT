import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../shared/material.module';
import { Tool } from '../../models/agent';
import { ToolService } from '../../services/tool.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';

@Component({
  selector: 'app-tools',
  standalone: true,
  imports: [
    CommonModule,
    MaterialModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatDividerModule,
    MatCardModule,
    MatListModule
  ],
  template: `
    <div class="tools-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Available Tools</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <mat-list>
            <mat-list-item *ngFor="let tool of tools">
              <mat-icon matListItemIcon>build</mat-icon>
              <div matListItemTitle>{{tool.name}}</div>
              <div matListItemLine>{{tool.description}}</div>
              <mat-divider></mat-divider>
            </mat-list-item>
          </mat-list>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .tools-container {
      padding: 20px;
    }
    
    mat-card {
      margin-bottom: 20px;
    }
    
    mat-list-item {
      margin-bottom: 8px;
    }
  `]
})
export class ToolsComponent implements OnInit {
  tools: Tool[] = [];
  loading = false;
  error: string | null = null;

  constructor(private toolService: ToolService) {}

  ngOnInit() {
    this.loadTools();
  }

  loadTools() {
    this.loading = true;
    this.error = null;
    
    this.toolService.getTools().subscribe({
      next: (tools) => {
        this.tools = tools;
        this.loading = false;
      },
      error: (error) => {
        this.error = 'Failed to load tools. Please try again later.';
        console.error('Error loading tools:', error);
        this.loading = false;
      }
    });
  }
} 