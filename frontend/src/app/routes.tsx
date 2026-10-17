// Route table: DESIGN.md §3. Guards: RequireRole (T-011).
// Staff and customer surfaces are lazy-loaded so the trusted-contact page stays light
// (DESIGN §2: < 150 KB excluding fonts, no charts).
import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, type RouteObject } from 'react-router'

import type { Role } from '../api/types'
import { SkeletonRows } from '../components/States'
import { ForbiddenPage } from '../features/auth/ForbiddenPage'
import { LoginPage } from '../features/auth/LoginPage'
import { NotFoundPage } from '../features/auth/NotFoundPage'
import { TrustedContactPage } from '../features/trusted/TrustedContactPage'
import { RequireRole } from './auth'

const StaffLayout = lazy(() =>
  import('../components/StaffLayout').then((m) => ({ default: m.StaffLayout })),
)
const OpsDashboard = lazy(() =>
  import('../features/ops/OpsDashboard').then((m) => ({ default: m.OpsDashboard })),
)
const HoldDetailPage = lazy(() =>
  import('../features/ops/HoldDetailPage').then((m) => ({ default: m.HoldDetailPage })),
)
const CustomerRiskPage = lazy(() =>
  import('../features/ops/CustomerRiskPage').then((m) => ({ default: m.CustomerRiskPage })),
)
const TellerConsole = lazy(() =>
  import('../features/teller/TellerConsole').then((m) => ({ default: m.TellerConsole })),
)
const DemoPanel = lazy(() =>
  import('../features/demo/DemoPanel').then((m) => ({ default: m.DemoPanel })),
)
const CustomerApp = lazy(() =>
  import('../features/customer/CustomerApp').then((m) => ({ default: m.CustomerApp })),
)

function guarded(roles: Role[], node: ReactNode) {
  return (
    <RequireRole roles={roles}>
      <Suspense fallback={<SkeletonRows rows={6} />}>{node}</Suspense>
    </RequireRole>
  )
}

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/login" replace /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/t/:token', element: <TrustedContactPage /> },
  { path: '/customer', element: guarded(['CUSTOMER'], <CustomerApp />) },
  {
    element: guarded(['TELLER', 'OFFICER', 'ADMIN'], <StaffLayout />),
    children: [
      { path: '/ops', element: guarded(['OFFICER', 'ADMIN'], <OpsDashboard />) },
      { path: '/ops/holds/:holdId', element: guarded(['OFFICER', 'ADMIN'], <HoldDetailPage />) },
      {
        path: '/ops/customers/:id',
        element: guarded(['OFFICER', 'ADMIN', 'TELLER'], <CustomerRiskPage />),
      },
      { path: '/teller', element: guarded(['TELLER', 'OFFICER'], <TellerConsole />) },
      { path: '/teller/holds/:holdId', element: guarded(['TELLER', 'OFFICER'], <TellerConsole />) },
      { path: '/demo', element: guarded(['ADMIN'], <DemoPanel />) },
      { path: '/403', element: <ForbiddenPage /> },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]
