import { Component, OnInit, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MaterialModule } from '../../shared/material.module';
import { Agent, AgentUpdate } from '../../models/agent';
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
import { A11yModule } from '@angular/cdk/a11y';

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
    MatListModule,
    A11yModule
  ],
  template: `
    <h2 mat-dialog-title id="edit-agent-dialog-title">Edit Agent</h2>
    <form [formGroup]="form" (ngSubmit)="onSubmit()" cdkTrapFocus cdkTrapFocusAutoCapture>
      <mat-dialog-content aria-labelledby="edit-agent-dialog-title">
        <mat-form-field appearance="fill">
          <mat-label>Name</mat-label>
          <input matInput formControlName="name" required cdkFocusInitial>
          <mat-error *ngIf="form.get('name')?.invalid && form.get('name')?.touched">
            Name is required
          </mat-error>
        </mat-form-field>

        <mat-form-field appearance="fill">
          <mat-label>Description</mat-label>
          <textarea matInput formControlName="description" rows="3" required></textarea>
          <mat-error *ngIf="form.get('description')?.invalid && form.get('description')?.touched">
            Description is required
          </mat-error>
        </mat-form-field>

        <mat-form-field appearance="fill">
          <mat-label>Prompt</mat-label>
          <textarea matInput formControlName="prompt" rows="5" required></textarea>
          <mat-hint>Define the agent's behavior and capabilities</mat-hint>
          <mat-error *ngIf="form.get('prompt')?.invalid && form.get('prompt')?.touched">
            Prompt is required
          </mat-error>
        </mat-form-field>

        <div class="tools-section" role="region" aria-labelledby="tools-section-title">
          <h3 id="tools-section-title">Available Tools</h3>
          <p class="tools-description">Select the tools this agent will have access to:</p>
          <mat-selection-list formControlName="tools" class="tools-list" aria-label="Available tools">
            <mat-tooltip [matTooltip]="tool.description" [matTooltipPosition]="'right'" *ngFor="let tool of availableTools">
              <mat-list-option [value]="tool.name" [attr.aria-label]="tool.name + ': ' + tool.description">
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

        <div class="hitl-section" role="region" aria-labelledby="hitl-section-title">
          <h3 id="hitl-section-title" class="visually-hidden">Human-in-the-Loop Settings</h3>
          <mat-checkbox formControlName="hitl_enabled" color="primary">
            Enable Human-in-the-Loop
          </mat-checkbox>
          <mat-hint>Allow human intervention during agent execution</mat-hint>
        </div>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button type="button" (click)="onCancel()">Cancel</button>
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
    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
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
      // Ensure we have a valid agent ID
      if (!this.data?.id) {
        console.error('Missing agent ID');
        this.dialogRef.close(null);
        return;
      }

      const formValue = this.form.value;
      const updatedAgent: AgentUpdate = {
        name: formValue.name || undefined,
        description: formValue.description || undefined,
        prompt: formValue.prompt || undefined,
        hitl_enabled: formValue.hitl_enabled,
        tools: formValue.tools || []
      };

      // Log the update data for debugging
      console.log('Submitting agent update:', updatedAgent);
      
      // Remove any undefined values
      const cleanedUpdate = Object.fromEntries(
        Object.entries(updatedAgent).filter(([_, value]) => value !== undefined)
      ) as AgentUpdate;

      this.dialogRef.close(cleanedUpdate);
    } else {
      this.form.markAllAsTouched();
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
} 