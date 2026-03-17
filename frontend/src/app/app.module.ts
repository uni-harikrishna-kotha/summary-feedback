import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppComponent } from './app.component';
import { ScoringFormComponent } from './components/scoring-form/scoring-form.component';
import { ResultsTableComponent } from './components/results-table/results-table.component';
import { DebugPanelComponent } from './components/debug-panel/debug-panel.component';
import { DebugInterceptor } from './interceptors/debug.interceptor';

@NgModule({
  declarations: [
    AppComponent,
    ScoringFormComponent,
    ResultsTableComponent,
    DebugPanelComponent,
  ],
  imports: [
    BrowserModule,
    ReactiveFormsModule,
    HttpClientModule,
  ],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: DebugInterceptor, multi: true },
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }