import './style.css';
export const metadata = { title: 'EU AI Act | Evidence Explorer', description: 'Traceable retrieval across selected AI Act and GDPR articles.' };
export default function Layout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
