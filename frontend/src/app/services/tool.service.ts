import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Tool } from '../models/agent';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ToolService {
  private apiUrl = `${environment.apiUrl}/tools`;

  constructor(private http: HttpClient) {}

  getTools(): Observable<Tool[]> {
    return this.http.get<Tool[]>(this.apiUrl);
  }

  getTool(name: string): Observable<Tool> {
    return this.http.get<Tool>(`${this.apiUrl}/${name}`);
  }

  registerTool(tool: Tool): Observable<Tool> {
    return this.http.post<Tool>(this.apiUrl, tool);
  }

  unregisterTool(name: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${name}`);
  }

  executeTool(name: string, parameters: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${name}/execute`, { parameters });
  }
} 