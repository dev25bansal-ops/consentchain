"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";

export function RecentActivity() {
  const { data: consents } = useQuery({
    queryKey: ["recent-consents"],
    queryFn: () => api.consents.list({ status: "GRANTED" }),
  });

  const recentConsents = consents?.slice(0, 5) ?? [];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {recentConsents.length === 0 ? (
          <p className="text-gray-500 text-sm">No recent activity</p>
        ) : (
          recentConsents.map((consent) => (
            <div
              key={consent.id}
              className="flex items-center justify-between py-2 border-b"
            >
              <div>
                <p className="text-sm font-medium">{consent.purpose}</p>
                <p className="text-xs text-gray-500">
                  {consent.created_at &&
                    formatDistanceToNow(new Date(consent.created_at))}{" "}
                  ago
                </p>
              </div>
              <span
                className={`px-2 py-1 text-xs rounded-full ${
                  consent.status === "GRANTED"
                    ? "bg-green-100 text-green-800"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                {consent.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
