import { Component, OnInit } from '@angular/core';
import { Tool } from '../../models/agent';
import { ToolService } from '../../services/tool.service';
import { MaterialModule } from '../../shared/material.module';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-tools',
  standalone: true,
  imports: [MaterialModule, CommonModule, MatProgressSpinnerModule],
  templateUrl: './tools.component.html',
  styleUrls: ['./tools.component.scss']
})
export class ToolsComponent implements OnInit {
  tools: Tool[] = [];
  loading = false;
  error: string | null = null;
  protected Object = Object;

  constructor(private toolService: ToolService) {}

  ngOnInit(): void {
    this.loadTools();
  }

  private loadTools(): void {
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