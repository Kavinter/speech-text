import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Meeting, MeetingDetail, Speaker } from '../models/meeting.model';

@Injectable({
  providedIn: 'root'
})
export class MeetingService {
  private baseUrl = '/api/meetings/';

  constructor(private http: HttpClient) {}

  getMeetings(): Observable<Meeting[]> {
    return this.http.get<Meeting[]>(this.baseUrl);
  }

  getMeeting(id: number): Observable<MeetingDetail> {
    return this.http.get<MeetingDetail>(`${this.baseUrl}${id}`);
  }

  uploadMeeting(formData: FormData): Observable<Meeting> {
    return this.http.post<Meeting>(this.baseUrl, formData);
  }

  deleteMeeting(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}${id}`);
  }

  processMeeting(id: number): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}${id}/process`, {});
  }

  getStatus(id: number): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(`${this.baseUrl}${id}/status`);
  }

  updateSpeakers(id: number, speakers: Speaker[]): Observable<void> {
    return this.http.put<void>(`${this.baseUrl}${id}/speakers`, speakers);
  }

  exportMeeting(id: number, format: string): Observable<Blob> {
    const params = new HttpParams().set('format', format);
    return this.http.get(`${this.baseUrl}${id}/export`, { params, responseType: 'blob' });
  }
}
