// Route table: DESIGN.md §3. Screens are placeholders until their tasks (T-011, T-033–T-039).
import type { RouteObject } from 'react-router'

import { Placeholder } from '../features/placeholder/Placeholder'

export const routes: RouteObject[] = [
  { path: '/', element: <Placeholder screen="screen.login" /> },
  { path: '/login', element: <Placeholder screen="screen.login" /> },
  { path: '/ops', element: <Placeholder screen="screen.ops" /> },
  { path: '/ops/holds/:holdId', element: <Placeholder screen="screen.ops_hold" /> },
  { path: '/ops/customers/:id', element: <Placeholder screen="screen.ops_customer" /> },
  { path: '/teller', element: <Placeholder screen="screen.teller" /> },
  { path: '/teller/holds/:holdId', element: <Placeholder screen="screen.teller_hold" /> },
  { path: '/customer', element: <Placeholder screen="screen.customer" /> },
  { path: '/t/:token', element: <Placeholder screen="screen.trusted" /> },
  { path: '/demo', element: <Placeholder screen="screen.demo" /> },
  { path: '*', element: <Placeholder screen="screen.not_found" /> },
]
