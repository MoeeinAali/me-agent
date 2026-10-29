import "@fontsource-variable/geist";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/vazirmatn";
import "./globals.css";

import type { Metadata, Viewport } from "next";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: "Ask Moeein — an interview agent that doesn't make things up",
  description:
    "Ask about Moeein Aali's projects, experience, courses, and fit for a role. Every answer shows the fields it read and the action it took.",
};

export const viewport: Viewport = {
  themeColor: "#18181b",
  colorScheme: "dark",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full">
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster position="top-center" />
      </body>
    </html>
  );
}
