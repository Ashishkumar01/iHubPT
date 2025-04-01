import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Agent, AgentCreate, AgentUpdate, AgentStatus } from '../models/agent';
import { environment } from '../../environments/environment';
import { tap } from 'rxjs/operators';
import { map } from 'rxjs/operators';
import { switchMap } from 'rxjs/operators';

interface ChatResponse {
  content: string;
}

export interface Tool {
  name: string;
  description: string;
  parameters: any;
}

@Injectable({
  providedIn: 'root'
})
export class AgentService {
  private apiUrl = `${environment.apiUrl}/agents`;

  constructor(private http: HttpClient) {}

  createAgent(agent: Partial<Agent>): Observable<Agent> {
    return this.http.post<Agent>(this.apiUrl, agent);
  }

  getAgents(): Observable<Agent[]> {
    return this.http.get<Agent[]>(this.apiUrl);
  }

  getAgent(id: string): Observable<Agent> {
    return this.http.get<Agent>(`${this.apiUrl}/${id}`);
  }

  updateAgent(id: string, agent: AgentUpdate): Observable<Agent> {
    console.log(`Updating agent ${id} with data:`, agent);
    if (!id) {
      console.error('No agent ID provided to updateAgent');
      throw new Error('Agent ID is required for update');
    }
    return this.http.put<Agent>(`${this.apiUrl}/${id}`, agent).pipe(
      tap({
        next: (response) => console.log('Update successful:', response),
        error: (error) => console.error('Update failed:', error)
      })
    );
  }

  deleteAgent(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  startAgent(id: string): Observable<Agent> {
    return this.http.post<Agent>(`${this.apiUrl}/${id}/start`, {});
  }

  pauseAgent(id: string): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.apiUrl}/${id}/pause`, {});
  }

  resumeAgent(id: string): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.apiUrl}/${id}/resume`, {});
  }

  getAgentStatus(id: string): Observable<{ status: AgentStatus }> {
    return this.http.get<{ status: AgentStatus }>(`${this.apiUrl}/${id}/status`);
  }

  chatWithAgent(agentId: string, message: string): Observable<{ content: string }> {
    return this.http.post<{ content: string }>(`${this.apiUrl}/${agentId}/chat`, { content: message });
  }

  stopAgent(id: string): Observable<Agent> {
    return this.http.post<Agent>(`${this.apiUrl}/${id}/stop`, {});
  }

  sendMessage(agentId: string, message: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.apiUrl}/${agentId}/chat`, {
      content: message
    });
  }

  getAvailableTools(): Observable<Tool[]> {
    return this.http.get<Tool[]>(`${environment.apiUrl}/tools`);
  }
} 