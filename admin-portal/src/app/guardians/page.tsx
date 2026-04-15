"use client";

import { useQuery } from "@tanstack/react-query";
import { Layout } from "@/components/Layout";
import { UserCheck, Shield, Clock, CheckCircle, XCircle } from "lucide-react";

interface Guardian {
  id: string;
  guardian_wallet: string;
  guardian_name: string;
  guardian_email: string;
  guardian_type: string;
  principal_id: string;
  principal_category: string;
  status: string;
  valid_from: string;
  valid_until?: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  PENDING_VERIFICATION: "bg-yellow-100 text-yellow-800",
  ACTIVE: "bg-green-100 text-green-800",
  SUSPENDED: "bg-red-100 text-red-800",
  REVOKED: "bg-gray-100 text-gray-800",
  EXPIRED: "bg-gray-100 text-gray-600",
};

const guardianTypeLabels: Record<string, string> = {
  PARENT: "Parent",
  LEGAL_GUARDIAN: "Legal Guardian",
  COURT_APPOINTED: "Court Appointed",
  POWER_OF_ATTORNEY: "Power of Attorney",
  CAREGIVER: "Caregiver",
};

const principalCategoryLabels: Record<string, string> = {
  MINOR: "Minor",
  PERSON_WITH_DISABILITY: "Person with Disability",
  INCAPACITATED: "Incapacitated",
  OTHER: "Other",
};

export default function GuardiansPage() {
  const { data: guardians, isLoading } = useQuery({
    queryKey: ["guardians"],
    queryFn: async () => {
      const response = await fetch(
        "http://localhost:8000/api/v1/guardian/list",
      );
      const result = await response.json();
      return result.data?.guardians || [];
    },
  });

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Guardians</h1>
            <p className="text-gray-500">
              DPDP Act Section 14 - Nominated Representatives
            </p>
          </div>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
            Register Guardian
          </button>
        </div>

        <div className="bg-white rounded-lg border">
          <div className="grid grid-cols-1 divide-y">
            {isLoading ? (
              <div className="text-center py-8">Loading...</div>
            ) : guardians?.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No guardians registered
              </div>
            ) : (
              guardians?.map((guardian: Guardian) => (
                <div key={guardian.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                        <UserCheck className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">
                            {guardian.guardian_name}
                          </h3>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs ${
                              statusColors[guardian.status] || "bg-gray-100"
                            }`}
                          >
                            {guardian.status.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">
                          {guardian.guardian_email}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          <span>
                            <Shield className="w-3 h-3 inline mr-1" />
                            {guardianTypeLabels[guardian.guardian_type] ||
                              guardian.guardian_type}
                          </span>
                          <span>
                            Principal:{" "}
                            {principalCategoryLabels[
                              guardian.principal_category
                            ] || guardian.principal_category}
                          </span>
                          <span>
                            <Clock className="w-3 h-3 inline mr-1" />
                            Valid from:{" "}
                            {new Date(guardian.valid_from).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {guardian.status === "PENDING_VERIFICATION" && (
                        <button className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
                          Verify
                        </button>
                      )}
                      {guardian.status === "ACTIVE" && (
                        <>
                          <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">
                            View Audit Log
                          </button>
                          <button className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700">
                            Revoke
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-medium text-blue-800 mb-2">
            DPDP Act Section 14 Compliance
          </h3>
          <p className="text-sm text-blue-700">
            Guardians (Nominated Representatives) can exercise rights on behalf
            of:
          </p>
          <ul className="text-sm text-blue-700 mt-2 list-disc list-inside">
            <li>Minors (under 18 years of age)</li>
            <li>Persons with disabilities</li>
            <li>Incapacitated individuals</li>
          </ul>
        </div>
      </div>
    </Layout>
  );
}
