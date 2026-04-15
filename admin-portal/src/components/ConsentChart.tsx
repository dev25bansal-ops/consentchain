"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { api, ConsentTimeSeriesPoint } from "@/lib/api";

export function ConsentChart() {
  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["consents", "timeseries"],
    queryFn: () => api.consents.timeseries(6),
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Consent Activity</h3>
        <div className="h-64 flex items-center justify-center">
          <p className="text-gray-500">Loading chart data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Consent Activity</h3>
        <div className="h-64 flex items-center justify-center">
          <p className="text-red-500">Failed to load chart data</p>
        </div>
      </div>
    );
  }

  const chartData: ConsentTimeSeriesPoint[] = data?.timeseries || [];

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Consent Activity</h3>
        <div className="h-64 flex items-center justify-center">
          <p className="text-gray-500">No data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Consent Activity</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="granted" fill="#3b82f6" name="Granted" />
            <Bar dataKey="revoked" fill="#ef4444" name="Revoked" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
