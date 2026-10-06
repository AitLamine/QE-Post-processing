import AppShell from '@/components/AppShell'
import './globals.css'

export const metadata = {
  title: 'DFT Post-Processing Lab',
  description: 'Self-service post-processing and input-generation tools for DFT calculations.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
