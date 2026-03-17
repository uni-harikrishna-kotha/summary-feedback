import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommonModule } from '@angular/common';

import { ResultsTableComponent } from './results-table.component';
import { ScoringJobResult, CallScoreResult } from '../../models/scoring.models';

describe('ResultsTableComponent', () => {
  let component: ResultsTableComponent;
  let fixture: ComponentFixture<ResultsTableComponent>;

  const scoredCall: CallScoreResult = {
    call_id: 'call_001',
    call_end_time: '2026-03-17T15:00:00Z',
    summary_present: true,
    accuracy: 8.0,
    information_capture: 7.0,
    context_adherence: 9.0,
    composite_score: 8.0,
    status: 'scored',
    rationale: {
      accuracy: 'Accurate.',
      information_capture: 'Most info captured.',
      context_adherence: 'Follows template.'
    }
  };

  const noSummaryCall: CallScoreResult = {
    call_id: 'call_002',
    call_end_time: '2026-03-17T14:00:00Z',
    summary_present: false,
    accuracy: null,
    information_capture: null,
    context_adherence: null,
    composite_score: 0.0,
    status: 'no_summary',
    rationale: null
  };

  const mockResult: ScoringJobResult = {
    job_id: 'score_test',
    tenant_id: 'acme',
    status: 'completed',
    overall_score: 7.5,
    window_start: '2026-03-16T17:00:00Z',
    window_end: '2026-03-17T17:00:00Z',
    calls_scored: 1,
    calls_missing_summary: 1,
    calls_unscored: 0,
    computed_at: '2026-03-17T17:00:30Z',
    calls: [scoredCall, noSummaryCall],
    error: null
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CommonModule],
      declarations: [ResultsTableComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ResultsTableComponent);
    component = fixture.componentInstance;
    component.result = mockResult;
    fixture.detectChanges();
  });

  it('should render one <tr> per call', () => {
    const rows = fixture.nativeElement.querySelectorAll('tbody tr:not(.rationale-row)');
    expect(rows.length).toBe(2);
  });

  it('should show "N/A" when overall_score is null', () => {
    component.result = { ...mockResult, overall_score: null };
    fixture.detectChanges();
    const scoreEl = fixture.nativeElement.querySelector('.score-value span');
    expect(scoreEl.textContent.trim()).toBe('N/A');
  });

  it('should expand row on click and collapse on second click', () => {
    expect(component.isExpanded('call_001')).toBeFalse();

    component.toggleRow('call_001');
    fixture.detectChanges();
    expect(component.isExpanded('call_001')).toBeTrue();

    const rationaleRows = fixture.nativeElement.querySelectorAll('.rationale-row');
    expect(rationaleRows.length).toBe(1);

    component.toggleRow('call_001');
    fixture.detectChanges();
    expect(component.isExpanded('call_001')).toBeFalse();
  });

  it('no_summary row should show "No Summary" label', () => {
    const rows = fixture.nativeElement.querySelectorAll('tbody tr:not(.rationale-row)');
    const noSummaryRow = rows[1];
    expect(noSummaryRow.textContent).toContain('No Summary');
  });
});
