import { test, expect } from '@playwright/test';

/**
 * Playwright end-to-end tests for the Architectural Planning Platform.
 *
 * Structure:
 *  Group 1 — Landing page (no backend needed)
 *  Group 2 — Studio navigation (Landing → Setup → Studio)
 *  Group 3 — Workflow tab (Archi Copilot integration)
 *  Group 4 — Viewport2D SVG structure (needs Studio + mocked API)
 *
 * The old tests assumed the app opened directly into the Studio SVG viewport.
 * The app now has: Landing → Setup → Studio (Geometry tab | Workflow tab).
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Mock ALL API calls so the Studio doesn't hang waiting for a backend. */
async function mockAllAPIs(page: any) {
  const analysisBody = JSON.stringify({
    status: 'engine-unavailable',
    spaces: [], graph: { nodes: [], edges: [], routes: [] },
    openings: [], findings: [], findingCounts: {},
  });

  // All /api/* routes (covers /api/v1/projects/.../analysis, /api/workflow/*, etc.)
  await page.route('http://localhost:8000/**', route => {
    route.fulfill({ status: 200, contentType: 'application/json', body: analysisBody });
  });

  // Vite dev server proxied /api routes
  await page.route('**/api/**', route => {
    const url = route.request().url();
    if (url.includes('brief-analysis')) {
      route.fulfill({ status: 200, contentType: 'application/json', body: 'null' });
    } else if (url.includes('/versions')) {
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    } else if (url.includes('/suggestions')) {
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    } else {
      route.fulfill({ status: 200, contentType: 'application/json', body: analysisBody });
    }
  });

  // Legacy /analysis path (direct fetch, no /api prefix)
  await page.route('http://localhost:5173/analysis*', route => {
    route.fulfill({ status: 200, contentType: 'application/json', body: analysisBody });
  });
}

/** Navigate past Landing → Setup to the Studio. */
async function openStudio(page: any) {
  await page.goto('/');
  await page.waitForSelector('h1', { timeout: 5000 });
  await mockAllAPIs(page);

  // Open workspace
  await page.getByRole('button', { name: /open workspace/i }).first().click();
  await page.waitForSelector('.setup-page', { timeout: 8000 });

  // Fill project name to enable button
  await page.locator('input.setup-input').first().fill('Test Project');

  // Wait for button to become enabled
  await page.waitForFunction(() => {
    const btn = document.querySelector('[data-testid="start-working-btn"]') as HTMLButtonElement;
    return btn && !btn.disabled;
  }, { timeout: 5000 });

  // Click the Start working button
  await page.locator('[data-testid="start-working-btn"]').click();

  // Fixed wait — diagnostic confirmed Studio renders in ~3s in dev mode.
  // waitForSelector/waitForFunction don't reliably detect React Strict Mode
  // double-renders when Playwright manages the Vite dev server.
  await page.waitForTimeout(4000);
}

// ── Group 1: Landing page ────────────────────────────────────────────────────

test.describe('Landing Page', () => {
  test('loads and shows the main heading', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByText(/From first brief/i)).toBeVisible();
  });

  test('shows Open workspace button', async ({ page }) => {
    await page.goto('/');
    const btn = page.getByRole('button', { name: /open workspace/i }).first();
    await expect(btn).toBeVisible();
  });

  test('shows workflow section', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/The planning loop/i)).toBeVisible();
  });

  test('navigation links are present', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: /workflows/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /validation/i })).toBeVisible();
  });

  test('footer is visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('footer')).toBeVisible();
  });
});

// ── Group 2: Studio navigation ───────────────────────────────────────────────

test.describe('Studio Navigation', () => {
  test('clicking Open workspace shows project setup', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /open workspace/i }).first().click();
    await expect(page.getByText(/PROJECT INTAKE/i)).toBeVisible();
  });

  test('setup page shows New project and Continue existing tabs', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /open workspace/i }).first().click();
    await expect(page.getByText(/New project/i)).toBeVisible();
    await expect(page.getByText(/Continue existing/i)).toBeVisible();
  });

  test('can start working with existing project', async ({ page }) => {
    await openStudio(page);
    await expect(page.locator('.studio-header')).toBeVisible();
    await expect(page.locator('.studio-title')).toBeVisible();
  });

  test('studio shows Geometry and Workflow tabs', async ({ page }) => {
    await openStudio(page);
    await expect(page.locator('[data-testid="geometry-tab-btn"]')).toBeVisible();
    await expect(page.locator('[data-testid="workflow-tab-btn"]')).toBeVisible();
  });

  test('can navigate back from studio to landing', async ({ page }) => {
    await openStudio(page);
    await page.locator('[data-testid="back-btn"]').click();
    await expect(page.getByText(/From first brief/i)).toBeVisible();
  });
});

// ── Group 3: Workflow tab ────────────────────────────────────────────────────

test.describe('Workflow Tab', () => {
  test.beforeEach(async ({ page }) => {
    await openStudio(page);
    await page.getByRole('button', { name: /workflow/i }).click();
    await page.waitForTimeout(500);
  });

  test('workflow tab renders the Brief panel', async ({ page }) => {
    await expect(page.getByText(/Client Brief/i)).toBeVisible();
  });

  test('workflow tab shows Analyze Brief button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /analyze brief/i })).toBeVisible();
  });

  test('workflow tab shows canvas area', async ({ page }) => {
    await expect(page.getByText(/Add zones/i)).toBeVisible();
  });

  test('workflow tab shows Versions panel', async ({ page }) => {
    await expect(page.getByText(/No saved versions yet/i)).toBeVisible();
  });

  test('Save version button is present', async ({ page }) => {
    await expect(page.getByRole('button', { name: /save/i })).toBeVisible();
  });

  test('Export button is present', async ({ page }) => {
    await expect(page.getByRole('button', { name: /export/i })).toBeVisible();
  });

  test('Promote button is present but disabled without zones', async ({ page }) => {
    const promoteBtn = page.getByRole('button', { name: /promote/i });
    await expect(promoteBtn).toBeVisible();
    await expect(promoteBtn).toBeDisabled();
  });
});

// ── Group 4: Viewport2D SVG (mocked API, Geometry tab) ───────────────────────

test.describe('Viewport2D SVG Structure', () => {
  test.beforeEach(async ({ page }) => {
    await openStudio(page);
    // Stay on Geometry tab (default)
  });

  test('renders an SVG element in the studio', async ({ page }) => {
    // The plan-preview SVG on the landing is gone; studio has its own SVG
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
  });

  test('SVG has a viewBox attribute', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    const viewBox = await svg.getAttribute('viewBox');
    expect(viewBox).not.toBeNull();
  });

  test('Viewport2D shows engine-unavailable gracefully', async ({ page }) => {
    // API is mocked to return engine-unavailable sentinel
    // The viewport component should render a fallback, not throw
    const studio = page.locator('.studio-viewport');
    await expect(studio).toBeVisible();
  });
});

// ── Group 5: Accessibility basics ────────────────────────────────────────────

test.describe('Accessibility', () => {
  test('landing page has a main landmark', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main')).toBeVisible();
  });

  test('landing page has a footer landmark', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('footer')).toBeVisible();
  });

  test('brand link has accessible label', async ({ page }) => {
    await page.goto('/');
    const brand = page.getByRole('link', { name: /advocate chambers home/i }).first();
    await expect(brand).toBeVisible();
  });

  test('page title is set', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });
});
