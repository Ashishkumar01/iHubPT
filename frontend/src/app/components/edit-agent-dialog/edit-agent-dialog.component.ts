import { Component, OnInit, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MaterialModule } from '../../shared/material.module';
import { Agent } from '../../models/agent';
import { AgentService, Tool } from '../../services/agent.service';
import { CommonModule } from '@angular/common';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { MatListModule } from '@angular/material/list';

@Component({
  selector: 'app-edit-agent-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MaterialModule,
    ReactiveFormsModule,
    FormsModule,
    MatCheckboxModule,
    MatTooltipModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatDialogModule,
    MatListModule
  ],
  template: `
    <h2 mat-dialog-title>Edit Agent</h2>
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <mat-dialog-content>
        <mat-form-field appearance="fill">
          <mat-label>Name</mat-label>
          <input matInput formControlName="name" required>
        </mat-form-field>

        <mat-form-field appearance="fill">
          <mat-label>Description</mat-label>
          <textarea matInput formControlName="description" rows="3" required></textarea>
        </mat-form-field>

        <mat-form-field appearance="fill">
          <mat-label>Prompt</mat-label>
          <textarea matInput formControlName="prompt" rows="5" required></textarea>
          <mat-hint>Define the agent's behavior and capabilities</mat-hint>
        </mat-form-field>

        <div class="tools-section">
          <h3>Available Tools</h3>
          <p class="tools-description">Select the tools this agent will have access to:</p>
          <mat-selection-list formControlName="tools" class="tools-list">
            <mat-tooltip [matTooltip]="tool.description" [matTooltipPosition]="'right'" *ngFor="let tool of availableTools">
              <mat-list-option [value]="tool.name">
                <mat-icon matListItemIcon>build</mat-icon>
                <div matListItemTitle>{{tool.name}}</div>
                <div matListItemLine class="tool-description">{{tool.description}}</div>
              </mat-list-option>
            </mat-tooltip>
          </mat-selection-list>
          <mat-error *ngIf="form.get('tools')?.touched && form.get('tools')?.value?.length === 0">
            Please select at least one tool
          </mat-error>
        </div>

        <div class="hitl-section">
          <mat-checkbox formControlName="hitl_enabled" color="primary">
            Enable Human-in-the-Loop
          </mat-checkbox>
          <mat-hint>Allow human intervention during agent execution</mat-hint>
        </div>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()">Cancel</button>
        <button mat-raised-button color="primary" type="submit" [disabled]="!form.valid">
          Save
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [`
    mat-dialog-content {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      min-width: 500px;
      max-height: 80vh;
      padding: 1rem;
    }
    mat-form-field {
      width: 100%;
    }
    .tools-section {
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 1rem;
      margin: 1rem 0;
      background-color: #fafafa;
    }
    .tools-section h3 {
      margin-top: 0;
      color: rgba(0, 0, 0, 0.87);
      font-size: 1.1rem;
      font-weight: 500;
    }
    .tools-description {
      color: rgba(0, 0, 0, 0.6);
      font-size: 0.9rem;
      margin-bottom: 1rem;
    }
    .tools-list {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #eee;
      border-radius: 4px;
    }
    .tool-description {
      color: rgba(0, 0, 0, 0.6);
      font-size: 0.9rem;
    }
    .hitl-section {
      margin-top: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    mat-hint {
      font-size: 0.8rem;
      color: rgba(0, 0, 0, 0.6);
      margin-left: 0;
    }
    ::ng-deep .mat-mdc-list-option {
      border-bottom: 1px solid #eee;
      &:last-child {
        border-bottom: none;
      }
    }
    ::ng-deep .mat-mdc-list-option .mdc-list-item__content {
      padding: 0.5rem 0;
    }
    mat-dialog-actions {
      padding: 1rem;
      margin-bottom: 0;
    }
  `]
})
export class EditAgentDialogComponent implements OnInit {
  form: FormGroup;
  availableTools: Tool[] = [];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<EditAgentDialogComponent>,
    private agentService: AgentService,
    @Inject(MAT_DIALOG_DATA) public data: Agent
  ) {
    this.form = this.fb.group({
      name: [data.name, [Validators.required]],
      description: [data.description, [Validators.required]],
      prompt: [data.prompt, [Validators.required]],
      hitl_enabled: [data.hitl_enabled],
      tools: [data.tools || [], [Validators.required, Validators.minLength(1)]]
    });
  }

  ngOnInit() {
    this.loadTools();
  }

  loadTools() {
    this.agentService.getAvailableTools().subscribe({
      next: (tools) => {
        this.availableTools = tools;
      },
      error: (error) => {
        console.error('Error loading tools:', error);
      }
    });
  }

  onSubmit(): void {
    if (this.form.valid) {
      const formValue = this.form.value;
      const updatedAgent: Partial<Agent> = {
        name: formValue.name,
        description: formValue.description,
        prompt: formValue.prompt,
        hitl_enabled: formValue.hitl_enabled,
        tools: formValue.tools || []
      };
      this.dialogRef.close(updatedAgent);
    } else {
      this.form.markAllAsTouched();
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
} 