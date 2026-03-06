import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SkillForge AI — Career Intelligence Engine",
  description:
    "Autonomous workforce reskilling powered by Amazon Nova. " +
    "Voice coaching, skills gap analysis, and automated enrollment.",
  openGraph: {
    title: "SkillForge AI",
    description: "Your autonomous career reskilling engine",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-white antialiased`}>
        {children}
      </body>
    </html>
  );
}