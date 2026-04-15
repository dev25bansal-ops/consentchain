"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout } from "@/components/Layout";
import { api } from "@/lib/api";
import { useState } from "react";
import { AlertCircle, CheckCircle, Clock, Search } from "lucide-react";

interface Grievance {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  type: string;
  status: string;
  priority: string;
  subject: string;
  description: string;
  created_at: string;
  expected_resolution_date?: string;
  resolution?: string;
}

const statusColors: Record<string, string> = {
  SUBMITTED: "bg-yellow-100 text-yellow-800",
  ACKNOWLEDGED: "bg-blue-100 text-blue-800",
  IN_PROGRESS: "bg-purple-100 text-purple-800",
  RESOLVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  ESCALATED: "bg-red-200 text-red-900",
};

const priorityColors: Record<string, string> = {
  LOW: "text-gray-600",
  MEDIUM: "text-yellow-600",
  HIGH: "text-orange-600",
  URGENT: "text-red-600",
};

export default function GrievancesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: grievances, isLoading } = useQuery({
    queryKey: ["grievances", statusFilter],
    queryFn: async () => {
      const response = await fetch(
        `http://localhost:8000/api/v1/grievance/list${statusFilter ? `?status=${statusFilter}` : ""}`,
      );
      const result = await response.json();
      return result.data?.grievances || [];
    },
  });

  const filteredGrievances = grievances?.filter(
    (g: Grievance) =>
      g.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      g.description.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Grievances</h1>
            <p className="text-gray-500">
              DPDP Act Section 13 - Grievance Redressal
            </p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search grievances..."
              className="w-full pl-10 pr-4 py-2 border rounded-lg"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <select
            className="border rounded-lg px-4 py-2"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="ESCALATED">Escalated</option>
          </select>
        </div>

        <div className="grid gap-4">
          {isLoading ? (
            <div className="text-center py-8">Loading...</div>
          ) : filteredGrievances?.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No grievances found
            </div>
          ) : (
            filteredGrievances?.map((grievance: Grievance) => (
              <div
                key={grievance.id}
                className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-gray-400" />
                      <h3 className="font-medium">{grievance.subject}</h3>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${
                          statusColors[grievance.status] || "bg-gray-100"
                        }`}
                      >
                        {grievance.status}
                      </span>
                      <span
                        className={`text-xs font-medium ${
                          priorityColors[grievance.priority] || ""
                        }`}
                      >
                        {grievance.priority}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">
                      {grievance.description.substring(0, 150)}...
                    </p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Type: {grievance.type}</span>
                      <span>
                        Principal: {grievance.principal_id.slice(0, 8)}...
                      </span>
                      <span>
                        <Clock className="w-3 h-3 inline mr-1" />
                        {new Date(grievance.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {grievance.status === "SUBMITTED" && (
                      <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
                        Acknowledge
                      </button>
                    )}
                    {grievance.status !== "RESOLVED" &&
                      grievance.status !== "REJECTED" && (
                        <button className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
                          Resolve
                        </button>
                      )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
}
