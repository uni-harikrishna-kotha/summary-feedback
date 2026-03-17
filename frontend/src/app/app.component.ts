import { Component } from '@angular/core';
import { ScoringJobResult } from './models/scoring.models';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'Summary Feedback Scoring';
  result: ScoringJobResult | null = null;

  onResult(result: ScoringJobResult): void {
    this.result = result;
  }
}
