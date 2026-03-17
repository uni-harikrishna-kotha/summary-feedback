import { Component, EventEmitter, Output } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { TimeoutError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { ScoringApiService } from '../../services/scoring-api.service';
import { ScoringJobResult } from '../../models/scoring.models';

@Component({
  selector: 'app-scoring-form',
  templateUrl: './scoring-form.component.html',
  styleUrls: ['./scoring-form.component.scss']
})
export class ScoringFormComponent {
  @Output() scoringComplete = new EventEmitter<ScoringJobResult>();

  form: FormGroup;
  isLoading = false;
  errorMessage: string | null = null;

  constructor(private fb: FormBuilder, private scoringApi: ScoringApiService) {
    this.form = this.fb.group({
      tenantId: ['', Validators.required],
      jwtToken: ['', Validators.required],
      environment: ['prod', Validators.required],
      experienceId: [''],
      summaryTemplate: ['', Validators.required],
    });
  }

  onSubmit(): void {
    if (this.form.invalid || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const { tenantId, jwtToken, environment, experienceId, summaryTemplate } = this.form.value;

    this.scoringApi.runScoring({
      tenant_id: tenantId,
      jwt_token: jwtToken,
      environment,
      summary_template: summaryTemplate,
      ...(experienceId ? { experience_id: experienceId } : {}),
    }).subscribe({
      next: (result) => {
        this.isLoading = false;
        this.scoringComplete.emit(result);
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = this.mapError(err);
      }
    });
  }

  private mapError(err: unknown): string {
    if (err instanceof TimeoutError) {
      return 'Scoring timed out. Please try again.';
    }
    if (err instanceof HttpErrorResponse) {
      if (err.status === 401) {
        return 'Invalid or expired token';
      }
      if (err.status === 422) {
        return err.error?.detail || 'Validation error';
      }
      return `Error: ${err.statusText}`;
    }
    return 'An unexpected error occurred.';
  }
}
