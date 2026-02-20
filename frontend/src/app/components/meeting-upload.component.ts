import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { MeetingService } from '../services/meeting.service';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { NgIf} from '@angular/common';

@Component({
  standalone: true,
  selector: 'app-meeting-upload',
  templateUrl: './meeting-upload.component.html',
  styleUrls: ['./meeting-upload.component.scss'],
  imports: [
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    RouterModule,
    MatCheckboxModule,
    NgIf
  ]
})
export class MeetingUploadComponent {
  title = '';
  date = '';
  file?: File;
  uploading = false;
  diarization = false;
  numSpeakers: number | null = null;

  constructor(private meetingService: MeetingService, private router: Router) {}

  onFileSelected(event: any): void {
    this.file = event.target.files[0];
  }

  upload(): void {
    if (!this.title || !this.date || !this.file) {
      alert('Title, date, and audio file are required');
      return;
    }

    const formData = new FormData();
    formData.append('title', this.title);
    formData.append('date', this.date);
    formData.append('file', this.file);
    formData.append('diarization', String(this.diarization));
    if (this.diarization && this.numSpeakers) {
      formData.append('num_speakers', String(this.numSpeakers));
    }

    this.uploading = true;
    this.meetingService.uploadMeeting(formData).subscribe({
      next: () => {
        this.uploading = false;
        this.router.navigate(['/meetings']);
      },
      error: err => {
        console.error(err);
        this.uploading = false;
      }
    });
  }
}
