import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatToolbarModule } from '@angular/material/toolbar';

@Component({
  standalone: true,
  selector: 'app-home',
  templateUrl: './meeting-home.component.html',
  styleUrls: ['./meeting-home.component.scss'],
  imports: [
    RouterModule,
    MatButtonModule,
    MatCardModule,
    MatToolbarModule
  ]
})
export class MeetingHomeComponent {}