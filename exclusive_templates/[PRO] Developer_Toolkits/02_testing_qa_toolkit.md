# 🧪 Complete Testing & QA Toolkit

> **Estimated market value: $49**
>
> Pre-configured tests for Next.js, React, and APIs using Jest, React Testing Library,
> and Playwright for End-to-End testing.

---

## 1. Jest & React Testing Library Setup

### Component Test Example
```tsx
// src/__tests__/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button Component', () => {
  it('renders correctly', () => {
    render(<Button>Click Me</Button>)
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })

  it('triggers onClick when clicked', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click Me</Button>)
    
    fireEvent.click(screen.getByRole('button', { name: /click me/i }))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click Me</Button>)
    expect(screen.getByRole('button', { name: /click me/i })).toBeDisabled()
  })
})
```

---

## 2. API Route Testing

### API Test Example (Node-Mocks-HTTP)
```typescript
// src/__tests__/api/user.test.ts
import { createMocks } from 'node-mocks-http'
import { GET } from '@/app/api/user/route'

jest.mock('@/lib/auth', () => ({
  auth: jest.fn().mockResolvedValue({ user: { id: '1', role: 'ADMIN' } })
}))

describe('User API', () => {
  it('returns 200 and user data for authenticated request', async () => {
    const { req, res } = createMocks({ method: 'GET' })
    
    // Pass the mock request to the Next.js App Router handler
    const response = await GET(req as any)
    const json = await response.json()

    expect(response.status).toBe(200)
    expect(json).toHaveProperty('role', 'ADMIN')
  })
})
```

---

## 3. End-to-End (E2E) Testing with Playwright

### Auth Flow E2E Test
```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('should allow user to login and reach dashboard', async ({ page }) => {
    // Navigate to login
    await page.goto('/login')
    
    // Fill credentials
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    
    // Submit
    await Promise.all([
      page.waitForNavigation(),
      page.click('button[type="submit"]')
    ])
    
    // Verify redirect to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/)
    
    // Verify dashboard content
    await expect(page.locator('h1')).toContainText('Dashboard')
  })
})
```
