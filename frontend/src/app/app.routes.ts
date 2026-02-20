import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MeetingListComponent } from './components/meeting-list.component';
import { MeetingUploadComponent } from './components/meeting-upload.component';
import { MeetingDetailComponent } from './components/meeting-detail.component';
import { MeetingHomeComponent } from './components/meeting-home.component';

export const routes: Routes = [
  { path: '', component: MeetingHomeComponent },
  { path: 'meetings', component: MeetingListComponent },
  { path: 'meetings/upload', component: MeetingUploadComponent },
  { path: 'meetings/:id', component: MeetingDetailComponent },
  { path: '**', redirectTo: '' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
