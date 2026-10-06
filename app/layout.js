import AppShell from '@/components/AppShell'
import './globals.css'
import { Analytics } from '@vercel/analytics/next'

export const metadata = {
  title: 'QE Post-processing Lab',
  description: 'Self-service post-processing and input-generation tools for DFT calculations.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
        <Analytics />
      </body>
    </html>
  )
}
