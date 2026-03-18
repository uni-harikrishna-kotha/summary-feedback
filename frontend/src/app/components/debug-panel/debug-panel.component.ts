import { Component, OnInit } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { DebugService, DebugEntry } from '../../services/debug.service';

@Component({
  selector: 'app-debug-panel',
  templateUrl: './debug-panel.component.html',
  styleUrls: ['./debug-panel.component.scss'],
})
export class DebugPanelComponent implements OnInit {
  readonly debugMode = environment.debugMode;
  logs$!: Observable<DebugEntry[]>;
  collapsed = false;
  expandedIds = new Set<number>();

  constructor(private debug: DebugService) {}

  ngOnInit(): void {
    this.logs$ = this.debug.logs$;
  }

  toggle(): void {
    this.collapsed = !this.collapsed;
  }

  toggleEntry(id: number): void {
    if (this.expandedIds.has(id)) {
      this.expandedIds.delete(id);
    } else {
      this.expandedIds.add(id);
    }
  }

  isExpanded(id: number): boolean {
    return this.expandedIds.has(id);
  }

  clear(): void {
    this.debug.clear();
    this.expandedIds.clear();
  }

  formatJson(value: any): string {
    if (value === undefined || value === null) return '—';
    return JSON.stringify(value, null, 2);
  }

  statusClass(entry: DebugEntry): string {
    if (entry.pending) return 'status-pending';
    if (entry.error || (entry.status && entry.status >= 400)) return 'status-error';
    return 'status-ok';
  }
}