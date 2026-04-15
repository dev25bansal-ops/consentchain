import { Sidebar } from "@/components/Sidebar";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8 bg-gray-50 overflow-auto">{children}</main>
    </div>
  );
}
