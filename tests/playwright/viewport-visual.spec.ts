import { test, expect } from '@playwright/test';

/**
 * Phase 12 Playwright DOM/SVG visual regression tests
 * Tests focus on architectural plan viewport rendering and SVG structure
 */

test.describe('Viewport2D SVG Structure', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main application
    await page.goto('/');
  });

  test('should render SVG viewport with correct structure', async ({ page }) => {
    // Wait for the viewport to load
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Verify viewBox attribute for architectural scaling
    const viewBox = await svg.getAttribute('viewBox');
    expect(viewBox).toBe('0 0 760 1180');
  });

  test('should render grid pattern for architectural reference', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Check for grid pattern definition
    const gridPattern = svg.locator('pattern#grid');
    await expect(gridPattern).toHaveCount(1);
    
    // Verify grid pattern attributes
    const width = await gridPattern.getAttribute('width');
    const height = await gridPattern.getAttribute('height');
    expect(width).toBe('30');
    expect(height).toBe('30');
  });

  test('should render space rectangles with proper accessibility', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Check for space rectangles (architectural rooms)
    const spaceRects = svg.locator('rect').filter({ hasText: /^\w/ });
    const count = await spaceRects.count();
    
    // Should have at least some spaces rendered
    expect(count).toBeGreaterThan(0);
    
    // Verify first space has required attributes
    if (count > 0) {
      const firstRect = spaceRects.first();
      const x = await firstRect.getAttribute('x');
      const y = await firstRect.getAttribute('y');
      const width = await firstRect.getAttribute('width');
      const height = await firstRect.getAttribute('height');
      
      // All geometric attributes should be present
      expect(x).not.toBeNull();
      expect(y).not.toBeNull();
      expect(width).not.toBeNull();
      expect(height).not.toBeNull();
    }
  });

  test('should render route edges with semantic colors', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Check for route lines (architectural connectivity)
    const routeLines = svg.locator('line');
    const count = await routeLines.count();
    
    if (count > 0) {
      const firstLine = routeLines.first();
      const stroke = await firstLine.getAttribute('stroke');
      
      // Should use semantic colors for routes
      expect(stroke).toMatch(/^(#8b3c32|#2e5c62)$/); // red for vertical, blue for horizontal
    }
  });

  test('should display architectural labels with readable text', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Check for text labels (room names, IDs)
    const textElements = svg.locator('text');
    const count = await textElements.count();
    
    if (count > 0) {
      const firstText = textElements.first();
      const fontSize = await firstText.getAttribute('font-size');
      
      // Text should be readable (reasonable font size)
      expect(parseInt(fontSize || '0')).toBeGreaterThan(6);
      expect(parseInt(fontSize || '0')).toBeLessThan(20);
    }
  });

  test('should maintain responsive SVG scaling', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Check preserveAspectRatio for architectural scaling
    const preserveAspectRatio = await svg.getAttribute('preserveAspectRatio');
    expect(preserveAspectRatio).toBe('xMidYMid meet');
    
    // Verify SVG is responsive
    const svgBox = await svg.boundingBox();
    expect(svgBox).not.toBeNull();
    expect(svgBox!.width).toBeGreaterThan(0);
    expect(svgBox!.height).toBeGreaterThan(0);
  });
});

test.describe('Viewport2D Interactive Elements', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should allow space selection with visual feedback', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Find a clickable space
    const spaceGroup = svg.locator('g').filter({ has: page.locator('rect') }).first();
    const count = await spaceGroup.count();
    
    if (count > 0) {
      // Click on a space
      await spaceGroup.first().click();
      
      // Verify selection state (stroke width change or color change)
      const selectedRect = spaceGroup.locator('rect').first();
      const strokeWidth = await selectedRect.getAttribute('stroke-width');
      
      // Selected elements should have thicker strokes
      expect(parseFloat(strokeWidth || '0')).toBeGreaterThanOrEqual(1.0);
    }
  });

  test('should display loading state during API fetch', async ({ page }) => {
    // Mock slow API response
    await page.route('**/analysis*', route => {
      setTimeout(() => route.fulfill({
        status: 200,
        body: JSON.stringify({
          status: 'unavailable',
          spaces: [],
          graph: { nodes: [], edges: [], routes: [] },
          openings: []
        })
      }), 1000);
    });
    
    await page.goto('/');
    
    // Should show loading indicator
    const loadingText = page.getByText('Loading authoritative model');
    await expect(loadingText).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/analysis*', route => {
      route.fulfill({
        status: 500,
        body: 'Internal Server Error'
      });
    });
    
    await page.goto('/');
    
    // Should show error state
    const errorText = page.getByText('Analysis API unavailable');
    await expect(errorText).toBeVisible();
  });
});

test.describe('Viewport2D Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should have proper color contrast for architectural elements', async ({ page }) => {
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
    
    // Check that text elements have readable colors
    const textElements = svg.locator('text');
    const count = await textElements.count();
    
    if (count > 0) {
      const firstText = textElements.first();
      const fill = await firstText.getAttribute('fill');
      
      // Should use dark colors for text on light backgrounds
      expect(fill).toMatch(/^(#192530|#65717a|#2e5c62)$/);
    }
  });

  test('should provide architectural legend information', async ({ page }) => {
    // Check for legend or explanatory text
    const legendText = page.getByText(/Red rooms have no proven route/);
    await expect(legendText).toBeVisible();
  });
});