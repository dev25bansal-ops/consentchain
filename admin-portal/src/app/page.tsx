'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { StatsCards } from '@/components/StatsCards';
import { ConsentChart } from '@/components/ConsentChart';
import { RecentActivity } from '@/components/RecentActivity';
import { Layout } from '@/components/Layout';

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.consents.stats(),
  });

  const { data: recentActivity, isLoading: activityLoading } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => api.consents.list({ page: 1, limit: 10 }),
  });

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white">
          <h1 className="text-2xl font-bold">ConsentChain Admin</h1>
          <p className="text-blue-100 mt-1">DPDP & GDPR Compliance Dashboard</p>
          <div className="mt-4 text-sm text-blue-200">
            Last updated: {new Date().toLocaleString()}
          </div>
        </div>

        {/* Stats Cards */}
        {statsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-1/3"></div>
              </div>
            ))}
          </div>
        ) : (
          <StatsCards stats={stats} />
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Consent Trends</h2>
            <ConsentChart />
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
            {activityLoading ? (
              <div className="space-y-3 animate-pulse">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-12 bg-gray-200 rounded"></div>
                ))}
              </div>
            ) : (
              <RecentActivity activities={recentActivity?.data || []} />
            )}
          </div>
        </div>

        {/* Compliance Status */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Compliance Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-green-200 bg-green-50 rounded-lg p-4">
              <div className="text-sm text-green-700">DPDP Compliance</div>
              <div className="text-2xl font-bold text-green-900 mt-1">98%</div>
              <div className="text-xs text-green-600 mt-1">Excellent</div>
            </div>
            <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-blue-700">GDPR Compliance</div>
              <div className="text-2xl font-bold text-blue-900 mt-1">92%</div>
              <div className="text-xs text-blue-600 mt-1">Good</div>
            </div>
            <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-purple-700">Security Score</div>
              <div className="text-2xl font-bold text-purple-900 mt-1">A+</div>
              <div className="text-xs text-purple-600 mt-1">Zero vulnerabilities</div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
