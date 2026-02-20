import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { MeetingService } from '../services/meeting.service';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

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
    RouterModule
  ]
})
export class MeetingUploadComponent {
  title = '';
  date = '';
  file?: File;
  uploading = false;

  constructor(private meetingService: MeetingService, private router: Router) {}

  onFileSelected(event: any): void {
    this.file = event.target.files[0];
  }

  upload(): void {
    if (!this.title || !this.date || !this.file) {
      alert('All fields are required');
      return;
    }

    const formData = new FormData();
    formData.append('title', this.title);
    formData.append('date', this.date);
    formData.append('file', this.file);

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
