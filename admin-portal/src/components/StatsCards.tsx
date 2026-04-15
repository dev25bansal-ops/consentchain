"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Users, FileCheck, XCircle, Clock } from "lucide-react";

export function StatsCards() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: api.consents.stats,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse grid grid-cols-4 gap-4">Loading...</div>
    );
  }

  const cards = [
    {
      label: "Total Consents",
      value: stats?.total_consents ?? 0,
      icon: FileCheck,
      color: "bg-blue-500",
    },
    {
      label: "Active",
      value: stats?.active_consents ?? 0,
      icon: Users,
      color: "bg-green-500",
    },
    {
      label: "Revoked",
      value: stats?.revoked_consents ?? 0,
      icon: XCircle,
      color: "bg-red-500",
    },
    {
      label: "Expired",
      value: stats?.expired_consents ?? 0,
      icon: Clock,
      color: "bg-yellow-500",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div key={card.label} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{card.label}</p>
                <p className="text-2xl font-bold mt-1">
                  {card.value.toLocaleString()}
                </p>
              </div>
              <div className={`${card.color} p-3 rounded-lg`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
