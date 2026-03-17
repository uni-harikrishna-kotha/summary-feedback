import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, interval } from 'rxjs';
import { switchMap, takeWhile, filter, timeout, catchError } from 'rxjs/operators';

import { ScoringRunRequest, ScoringRunAccepted, ScoringJobResult } from '../models/scoring.models';

@Injectable({
  providedIn: 'root'
})
export class ScoringApiService {
  private readonly baseUrl = 'http://localhost:8000/v1';

  constructor(private http: HttpClient) {}

  runScoring(request: ScoringRunRequest): Observable<ScoringJobResult> {
    return this.http.post<ScoringRunAccepted>(`${this.baseUrl}/scoring/run`, request).pipe(
      switchMap((accepted) => {
        return interval(2000).pipe(
          switchMap(() =>
            this.http.get<ScoringJobResult>(`${this.baseUrl}/scoring/run/${accepted.job_id}`)
          ),
          takeWhile((result) => result.status === 'processing', true),
          filter((result) => result.status !== 'processing'),
          timeout(95000)
        );
      }),
      catchError((err: HttpErrorResponse | Error) => throwError(() => err))
    );
  }
}
