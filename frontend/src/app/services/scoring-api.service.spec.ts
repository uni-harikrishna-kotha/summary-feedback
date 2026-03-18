import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { ScoringApiService } from './scoring-api.service';
import { ScoringJobResult, ScoringRunAccepted } from '../models/scoring.models';

describe('ScoringApiService', () => {
  let service: ScoringApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ScoringApiService]
    });
    service = TestBed.inject(ScoringApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should POST with correct body', () => {
    const request = { tenant_id: 'acme', jwt_token: 'tok123' };
    const accepted: ScoringRunAccepted = { job_id: 'score_abc', status: 'processing', tenant_id: 'acme' };
    const completed: ScoringJobResult = {
      job_id: 'score_abc', tenant_id: 'acme', status: 'completed',
      overall_score: 8.0, window_start: null, window_end: null,
      calls_scored: 1, calls_missing_summary: 0, calls_unscored: 0,
      computed_at: null, calls: [], error: null
    };

    let result: ScoringJobResult | undefined;
    service.runScoring(request).subscribe(r => result = r);

    const postReq = httpMock.expectOne('http://localhost:8000/v1/scoring/run');
    expect(postReq.request.method).toBe('POST');
    expect(postReq.request.body).toEqual(request);
    postReq.flush(accepted);

    const getReq = httpMock.expectOne('http://localhost:8000/v1/scoring/run/score_abc');
    expect(getReq.request.method).toBe('GET');
    getReq.flush(completed);

    expect(result).toEqual(completed);
  });

  it('should poll GET until status is completed', fakeAsync(() => {
    const request = { tenant_id: 'acme', jwt_token: 'tok123' };
    const accepted: ScoringRunAccepted = { job_id: 'score_poll', status: 'processing', tenant_id: 'acme' };
    const processing: ScoringJobResult = {
      job_id: 'score_poll', tenant_id: 'acme', status: 'processing',
      overall_score: null, window_start: null, window_end: null,
      calls_scored: 0, calls_missing_summary: 0, calls_unscored: 0,
      computed_at: null, calls: [], error: null
    };
    const completed: ScoringJobResult = { ...processing, status: 'completed', overall_score: 7.5 };

    let result: ScoringJobResult | undefined;
    service.runScoring(request).subscribe(r => result = r);

    const postReq = httpMock.expectOne('http://localhost:8000/v1/scoring/run');
    postReq.flush(accepted);

    tick(2000);
    const getReq1 = httpMock.expectOne('http://localhost:8000/v1/scoring/run/score_poll');
    getReq1.flush(processing);

    tick(2000);
    const getReq2 = httpMock.expectOne('http://localhost:8000/v1/scoring/run/score_poll');
    getReq2.flush(completed);

    expect(result).toEqual(completed);
  }));

  it('should emit error on HTTP 401', () => {
    const request = { tenant_id: 'acme', jwt_token: 'bad-token' };

    let error: any;
    service.runScoring(request).subscribe({
      error: (e) => error = e
    });

    const postReq = httpMock.expectOne('http://localhost:8000/v1/scoring/run');
    postReq.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(error).toBeTruthy();
    expect(error.status).toBe(401);
  });
});
