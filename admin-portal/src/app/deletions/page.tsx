"use client";

import { useQuery } from "@tanstack/react-query";
import { Layout } from "@/components/Layout";
import {
  Trash2,
  Clock,
  CheckCircle,
  AlertTriangle,
  FileText,
} from "lucide-react";

interface DeletionRequest {
  id: string;
  principal_id: string;
  fiduciary_id: string;
  scope: string;
  status: string;
  requested_at: string;
  scheduled_at?: string;
  completed_at?: string;
}

const statusColors: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  VERIFICATION_IN_PROGRESS: "bg-blue-100 text-blue-800",
  SCHEDULED: "bg-purple-100 text-purple-800",
  IN_PROGRESS: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
  REJECTED: "bg-gray-100 text-gray-800",
};

const scopeLabels: Record<string, string> = {
  FULL: "Full Deletion",
  PARTIAL: "Partial Deletion",
  SPECIFIC_CONSENT: "Specific Consent",
};

export default function DeletionsPage() {
  const { data: deletions, isLoading } = useQuery({
    queryKey: ["deletions"],
    queryFn: async () => {
      const response = await fetch(
        "http://localhost:8000/api/v1/deletion/list",
      );
      const result = await response.json();
      return result.data?.deletions || [];
    },
  });

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Data Deletion Requests
            </h1>
            <p className="text-gray-500">
              DPDP Act Section 9 - Right to Erasure
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-yellow-500" />
              <span className="text-sm text-gray-500">Pending</span>
            </div>
            <p className="text-2xl font-bold mt-1">
              {deletions?.filter((d: DeletionRequest) => d.status === "PENDING")
                .length || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              <span className="text-sm text-gray-500">In Progress</span>
            </div>
            <p className="text-2xl font-bold mt-1">
              {deletions?.filter(
                (d: DeletionRequest) => d.status === "IN_PROGRESS",
              ).length || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-sm text-gray-500">Completed</span>
            </div>
            <p className="text-2xl font-bold mt-1">
              {deletions?.filter(
                (d: DeletionRequest) => d.status === "COMPLETED",
              ).length || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-500" />
              <span className="text-sm text-gray-500">Total</span>
            </div>
            <p className="text-2xl font-bold mt-1">{deletions?.length || 0}</p>
          </div>
        </div>

        <div className="bg-white rounded-lg border">
          <div className="grid grid-cols-1 divide-y">
            {isLoading ? (
              <div className="text-center py-8">Loading...</div>
            ) : deletions?.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No deletion requests
              </div>
            ) : (
              deletions?.map((deletion: DeletionRequest) => (
                <div key={deletion.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                        <Trash2 className="w-5 h-5 text-red-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">
                            {scopeLabels[deletion.scope] || deletion.scope}
                          </h3>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs ${
                              statusColors[deletion.status] || "bg-gray-100"
                            }`}
                          >
                            {deletion.status.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">
                          Principal: {deletion.principal_id.slice(0, 8)}... |
                          Fiduciary: {deletion.fiduciary_id.slice(0, 8)}...
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          Requested:{" "}
                          {new Date(deletion.requested_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {deletion.status === "COMPLETED" && (
                        <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50 flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          Certificate
                        </button>
                      )}
                      {deletion.status === "PENDING" && (
                        <button className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700">
                          Execute
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="font-medium text-yellow-800 mb-2">
            Data Deletion Workflow
          </h3>
          <ol className="text-sm text-yellow-700 list-decimal list-inside space-y-1">
            <li>Identity verification of the data principal</li>
            <li>Check for active consents and legal holds</li>
            <li>Create backup for compliance retention</li>
            <li>Delete records from database, cache, and file storage</li>
            <li>Notify third parties of deletion</li>
            <li>Generate deletion certificate on blockchain</li>
          </ol>
        </div>
      </div>
    </Layout>
  );
}
