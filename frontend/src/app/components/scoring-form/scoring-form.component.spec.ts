import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { ScoringFormComponent } from './scoring-form.component';
import { ScoringApiService } from '../../services/scoring-api.service';
import { ScoringJobResult } from '../../models/scoring.models';

describe('ScoringFormComponent', () => {
  let component: ScoringFormComponent;
  let fixture: ComponentFixture<ScoringFormComponent>;
  let mockScoringApi: jasmine.SpyObj<ScoringApiService>;

  const mockResult: ScoringJobResult = {
    job_id: 'score_123',
    tenant_id: 'acme',
    status: 'completed',
    overall_score: 8.0,
    window_start: '2026-03-16T17:00:00Z',
    window_end: '2026-03-17T17:00:00Z',
    calls_scored: 5,
    calls_missing_summary: 0,
    calls_unscored: 0,
    computed_at: '2026-03-17T17:00:30Z',
    calls: [],
    error: null
  };

  beforeEach(async () => {
    mockScoringApi = jasmine.createSpyObj('ScoringApiService', ['runScoring']);

    await TestBed.configureTestingModule({
      imports: [ReactiveFormsModule, HttpClientTestingModule],
      declarations: [ScoringFormComponent],
      providers: [
        { provide: ScoringApiService, useValue: mockScoringApi }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ScoringFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('form should be invalid when fields are empty', () => {
    expect(component.form.valid).toBeFalse();
  });

  it('form should be valid when both fields are filled', () => {
    component.form.setValue({ tenantId: 'acme', jwtToken: 'tok123' });
    expect(component.form.valid).toBeTrue();
  });

  it('button should be disabled when isLoading is true', () => {
    component.form.setValue({ tenantId: 'acme', jwtToken: 'tok123' });
    component.isLoading = true;
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector('button[type="submit"]');
    expect(button.disabled).toBeTrue();
  });

  it('button should be disabled when form is invalid', () => {
    fixture.detectChanges();
    const button = fixture.nativeElement.querySelector('button[type="submit"]');
    expect(button.disabled).toBeTrue();
  });

  it('should show "Invalid or expired token" on 401', () => {
    component.form.setValue({ tenantId: 'acme', jwtToken: 'bad-token' });
    const error = new HttpErrorResponse({ status: 401, statusText: 'Unauthorized' });
    mockScoringApi.runScoring.and.returnValue(throwError(() => error));

    component.onSubmit();
    fixture.detectChanges();

    expect(component.errorMessage).toBe('Invalid or expired token');
    const errorEl = fixture.nativeElement.querySelector('.error-message');
    expect(errorEl.textContent.trim()).toBe('Invalid or expired token');
  });
});
