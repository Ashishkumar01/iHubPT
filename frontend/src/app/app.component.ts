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
      background-color: #f5f5f5;
    }

    mat-toolbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 1000;
      display: flex;
      align-items: center;
      padding: 0 24px;
      background-color: #2c2c2c;
      height: 64px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .brand {
      display: flex;
      align-items: center;
      text-decoration: none;
      color: white;
      height: 100%;
      
      .logo-img {
        height: 40px;
        width: 40px;
        margin-right: 16px;
        display: inline-flex;
        object-fit: contain;
      }
      
      span {
        font-size: 1.2rem;
        font-weight: 400;
        letter-spacing: 0.5px;
        white-space: nowrap;
      }
    }

    .content {
      margin-top: 64px;
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      max-width: 1400px;
      margin-left: auto;
      margin-right: auto;
      box-sizing: border-box;
    }

    .spacer {
      flex: 1 1 auto;
    }

    nav {
      display: flex;
      gap: 8px;
      height: 100%;
      
      a {
        height: 100%;
        padding: 0 16px;
        display: flex;
        align-items: center;
        color: rgba(255, 255, 255, 0.9);
        text-decoration: none;
        transition: all 0.2s ease;
        
        mat-icon {
          margin-right: 8px;
          opacity: 0.9;
        }
        
        &:hover {
          background-color: rgba(255, 255, 255, 0.1);
          color: white;
        }
        
        &.active {
          background-color: rgba(255, 255, 255, 0.15);
          border-bottom: 3px solid #64b5f6;
          color: white;
        }
      }
    }
  `]
})
export class AppComponent {
  title = 'PostTrade IntelligenceHub';

  constructor(private router: Router) {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      window.scrollTo(0, 0);
    });
  }
}
