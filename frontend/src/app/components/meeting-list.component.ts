import { Component } from '@angular/core';
import { MeetingService } from '../services/meeting.service';
import { Meeting } from '../models/meeting.model';
import { NgIf, NgForOf, DatePipe, AsyncPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';

@Component({
  standalone: true,
  selector: 'app-meeting-list',
  templateUrl: './meeting-list.component.html',
  styleUrls: ['./meeting-list.component.scss'],
  imports: [NgIf, NgForOf, AsyncPipe, DatePipe, RouterModule, MatCardModule, MatButtonModule]
})
export class MeetingListComponent {
  meetings$?: Observable<Meeting[]>;

  constructor(private meetingService: MeetingService) {
    this.loadMeetings();
  }

  loadMeetings(): void {
    this.meetings$ = this.meetingService.getMeetings();
  }

  deleteMeeting(id: number): void {
    if (!confirm('Are you sure you want to delete this meeting?')) return;

    this.meetingService.deleteMeeting(id).subscribe({
      next: () => {
        alert('Meeting deleted');
        this.loadMeetings();
      },
      error: err => console.error(err)
    });
  }
}