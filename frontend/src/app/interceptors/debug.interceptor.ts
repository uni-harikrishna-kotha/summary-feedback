import { Injectable } from '@angular/core';
import {
  HttpInterceptor, HttpRequest, HttpHandler,
  HttpEvent, HttpResponse, HttpErrorResponse,
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

import { environment } from '../../environments/environment';
import { DebugService } from '../services/debug.service';

@Injectable()
export class DebugInterceptor implements HttpInterceptor {
  constructor(private debug: DebugService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!environment.debugMode) {
      return next.handle(req);
    }

    const start = Date.now();
    const sanitizedBody = this.sanitizeBody(req.body);

    const id = this.debug.add({
      step: this.stepLabel(req.method, req.url),
      method: req.method,
      url: req.url,
      requestBody: sanitizedBody,
    });

    return next.handle(req).pipe(
      tap({
        next: (event) => {
          if (event instanceof HttpResponse) {
            this.debug.update(id, {
              status: event.status,
              responseBody: this.summarizeResponse(event.body),
              durationMs: Date.now() - start,
            });
          }
        },
        error: (err: HttpErrorResponse) => {
          this.debug.update(id, {
            status: err.status,
            error: err.error?.detail || err.message,
            durationMs: Date.now() - start,
          });
        },
      })
    );
  }

  private sanitizeBody(body: any): any {
    if (!body) return undefined;
    const clone = { ...body };
    if (clone.jwt_token) {
      clone.jwt_token = '***redacted***';
    }
    return clone;
  }

  private stepLabel(method: string, url: string): string {
    if (method === 'POST' && url.includes('/scoring/run')) {
      return 'Submit scoring job';
    }
    if (method === 'GET' && url.includes('/scoring/run/')) {
      return 'Poll job status';
    }
    return `${method} ${url}`;
  }

  private summarizeResponse(body: any): any {
    if (!body) return null;
    if (body.job_id && body.status === 'processing') {
      return { job_id: body.job_id, status: body.status };
    }
    if (body.job_id && body.status === 'completed') {
      return {
        job_id: body.job_id,
        status: body.status,
        overall_score: body.overall_score,
        calls_scored: body.calls_scored,
        calls_missing_summary: body.calls_missing_summary,
        calls_unscored: body.calls_unscored,
      };
    }
    return body;
  }
}