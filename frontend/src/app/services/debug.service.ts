import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface DebugEntry {
  id: number;
  timestamp: Date;
  step: string;
  method: string;
  url: string;
  requestBody?: any;
  status?: number;
  responseBody?: any;
  error?: string;
  durationMs?: number;
  pending: boolean;
}

@Injectable({ providedIn: 'root' })
export class DebugService {
  private entriesSubject = new BehaviorSubject<DebugEntry[]>([]);
  readonly logs$ = this.entriesSubject.asObservable();

  private counter = 0;

  add(entry: Omit<DebugEntry, 'id' | 'timestamp' | 'pending'>): number {
    const id = ++this.counter;
    this.entriesSubject.next([
      ...this.entriesSubject.value,
      { id, timestamp: new Date(), pending: true, ...entry },
    ]);
    return id;
  }

  update(id: number, updates: Partial<DebugEntry>): void {
    this.entriesSubject.next(
      this.entriesSubject.value.map(e =>
        e.id === id ? { ...e, pending: false, ...updates } : e
      )
    );
  }

  clear(): void {
    this.entriesSubject.next([]);
    this.counter = 0;
  }
}