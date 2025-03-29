import { Component } from '@angular/core';
import { Router, NavigationEnd, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs/operators';
import { MaterialModule } from './shared/material.module';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MaterialModule
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100vh;
    }

    mat-toolbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 1000;
    }

    .content {
      margin-top: 64px;
      flex: 1;
      overflow-y: auto;
      padding: 20px;
    }

    .spacer {
      flex: 1 1 auto;
    }

    nav {
      display: flex;
      gap: 8px;
    }

    .active {
      background-color: rgba(255, 255, 255, 0.1);
    }
  `]
})
export class AppComponent {
  title = 'iHubPT';

  constructor(private router: Router) {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      window.scrollTo(0, 0);
    });
  }
}
