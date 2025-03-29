import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ChatLog {
  id?: string;
  timestamp: string;
  agent_id: string;
  request_message: string;
  response_message: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  requestor_id: string;
  model_name: string;
  duration_ms: number;
  status: string;
  error_message?: string;
  cost: number;
  metadata?: any;
  user?: string;
  department?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatLogService {
  private apiUrl = `${environment.apiUrl}/chat-logs`;

  constructor(private http: HttpClient) {}

  getChatLogs(startDate?: Date, endDate?: Date, agentId?: string, status?: string): Observable<ChatLog[]> {
    let url = `${this.apiUrl}/timerange`;
    const params: any = {};
    
    if (startDate) {
      params.start_time = startDate.toISOString();
    }
    if (endDate) {
      params.end_time = endDate.toISOString();
    }
    if (agentId) {
      params.agent_id = agentId;
    }
    if (status) {
      params.status = status;
    }

    // If no dates provided, use last 7 days as default
    if (!startDate && !endDate) {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      params.start_time = start.toISOString();
      params.end_time = end.toISOString();
    }

    return this.http.get<ChatLog[]>(url, { params });
  }

  getChatLogById(id: string): Observable<ChatLog> {
    return this.http.get<ChatLog>(`${this.apiUrl}/${id}`);
  }
} 