import { Component, Input } from '@angular/core';
import { ScoringJobResult, CallScoreResult } from '../../models/scoring.models';

@Component({
  selector: 'app-results-table',
  templateUrl: './results-table.component.html',
  styleUrls: ['./results-table.component.scss']
})
export class ResultsTableComponent {
  @Input() result!: ScoringJobResult;

  expandedRows = new Set<string>();

  toggleRow(callId: string): void {
    if (this.expandedRows.has(callId)) {
      this.expandedRows.delete(callId);
    } else {
      this.expandedRows.add(callId);
    }
  }

  isExpanded(callId: string): boolean {
    return this.expandedRows.has(callId);
  }

  getStatusLabel(call: CallScoreResult): string {
    if (call.status === 'no_summary') return 'No Summary — Score: 0';
    if (call.status === 'unscored' || call.status === 'empty_transcript') return 'Scoring Failed';
    return '';
  }

  formatScore(score: number | null): string {
    if (score === null || score === undefined) return '—';
    return score.toFixed(2);
  }

  get hasUnscoredCalls(): boolean {
    return this.result.calls.some(
      c => c.status === 'unscored' || c.status === 'empty_transcript'
    );
  }
}
