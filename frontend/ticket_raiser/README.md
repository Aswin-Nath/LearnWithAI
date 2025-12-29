# Ticket Raiser Frontend - Authentication

React + TypeScript frontend with complete authentication integration.

## Project Structure

```
frontend/ticket_raiser/src/
├── core/
│   ├── __init__.ts           # Core exports
│   ├── config.ts             # Configuration & constants
│   ├── api.ts                # Fetch wrapper with error handling
│   └── errors.ts             # Custom error classes
├── schemas/
│   ├── __init__.ts
│   └── auth.ts               # TypeScript interfaces for auth
├── services/
│   ├── __init__.ts
│   └── auth.ts               # Auth service (API integration)
├── hooks/
│   ├── __init__.ts
│   ├── useAuth.ts            # Main auth hook
│   └── useTokenRefresh.ts    # Token refresh hook
├── components/
│   ├── __init__.ts
│   ├── Auth.tsx              # Login, Register, UserProfile components
│   └── ProtectedRoute.tsx    # Route protection & AuthProvider
├── environments/
│   ├── environment.ts        # Development config
│   └── environment.prod.ts   # Production config
├── App.tsx
├── main.tsx
└── index.css
```

## Setup

### 1. Install Dependencies

```bash
cd frontend/ticket_raiser
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Update if needed:

```env
VITE_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

App will be available at `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

## API Integration

### Auth Service

The `authService` handles all API calls:

```typescript
import { authService } from '@/services/auth';

// Register
await authService.register({
  username: 'john',
  email: 'john@example.com',
  password: 'SecurePass123',
  role: 'USER'
});

// Login
await authService.login({
  email: 'john@example.com',
  password: 'SecurePass123'
});

// Refresh token
await authService.refresh(refreshToken);

// Logout
await authService.logout();

// Get current user
const user = await authService.getCurrentUser();
```

### useAuth Hook

Main hook for managing authentication state:

```typescript
import { useAuth } from '@/hooks/useAuth';

function MyComponent() {
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    register,
    login,
    logout,
    logoutAll,
    clearError
  } = useAuth();

  // Use hook methods and state
}
```

## Usage Examples

### Login Component

```typescript
import { LoginForm } from '@/components/Auth';

function App() {
  return <LoginForm />;
}
```

### Register Component

```typescript
import { RegisterForm } from '@/components/Auth';

function App() {
  return <RegisterForm />;
}
```

### User Profile

```typescript
import { UserProfile } from '@/components/Auth';

function Dashboard() {
  return <UserProfile />;
}
```

### Protected Route

```typescript
import { ProtectedRoute } from '@/components/ProtectedRoute';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <ProtectedRoute requiredRole="USER">
      <Dashboard />
    </ProtectedRoute>
  );
}
```

## Error Handling

### API Errors

```typescript
import {
  AuthenticationError,
  AuthorizationError,
  ValidationError,
  ConflictError,
  ServerError
} from '@/core/errors';

try {
  await authService.login(data);
} catch (error) {
  if (error instanceof AuthenticationError) {
    // Handle 401
  } else if (error instanceof ValidationError) {
    // Handle 422
  } else if (error instanceof ConflictError) {
    // Handle 409 (user exists)
  }
}
```

## Local Storage

Auth service automatically uses localStorage:

- `accessToken` - JWT access token
- `refreshToken` - JWT refresh token
- `user` - Current user object

### Clear All Data

```typescript
import { authService } from '@/services/auth';

authService.clearTokens(); // Clears all stored auth data
```

## Next Steps

- [ ] Add problem management pages
- [ ] Add submission handling
- [ ] Add admin dashboard
- [ ] Add user settings page
- [ ] Add notification system

