import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MeetingService } from '../services/meeting.service';
import { Meeting } from '../models/meeting.model';
import { NgIf, NgForOf, DatePipe, AsyncPipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable, switchMap, interval, takeWhile, map } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';


@Component({
  standalone: true,
  selector: 'app-meeting-detail',
  templateUrl: './meeting-detail.component.html',
  styleUrls: ['./meeting-detail.component.scss'],
  imports: [
    NgIf, 
    NgForOf, 
    FormsModule, 
    DatePipe, 
    AsyncPipe,
    DecimalPipe,
    MatCardModule, 
    MatButtonModule, 
    MatProgressSpinnerModule,
    MatTabsModule
  ]
})
export class MeetingDetailComponent {
  meeting$?: Observable<Meeting>;
  processing = false;

  constructor(
    private route: ActivatedRoute,
    private meetingService: MeetingService
  ) {
    this.loadMeeting();
  }

  private loadMeeting() {
    this.meeting$ = this.route.paramMap.pipe(
      switchMap(params => {
        const id = Number(params.get('id'));
        return this.meetingService.getMeeting(id);
      })
    );
  }

  parseJsonArray(jsonStr?: string | null): string[] {
    if (!jsonStr) return [];
    try {
      return JSON.parse(jsonStr);
    } catch {
      return [];
    }
  }

  processMeeting(meeting: Meeting): void {
    this.processing = true;

    this.meetingService.processMeeting(meeting.id).subscribe({
      next: () => {
        interval(2000).pipe(
          switchMap(() => this.meetingService.getStatus(meeting.id)),
          takeWhile(status => status.status !== 'completed' && status.status !== 'failed', true)
        ).subscribe({
          next: status => {
            if (status.status === 'completed' || status.status === 'failed') {
              this.processing = false;
              this.meeting$ = this.meetingService.getMeeting(meeting.id);
            }
          },
          error: err => {
            console.error(err);
            this.processing = false;
          }
        });
      },
      error: err => {
        console.error(err);
        this.processing = false;
      }
    });
  }

  exportMeeting(meeting: Meeting, format: string): void {
    this.meetingService.exportMeeting(meeting.id, format).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `meeting_${meeting.id}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  updateSpeakers(meeting: Meeting): void {
    if (!meeting.speakers) return;
    this.meetingService.updateSpeakers(meeting.id, meeting.speakers).subscribe({
      next: () => alert('Speakers updated'),
      error: err => console.error(err)
    });
  }
}