'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { api, ConsentRecord } from '@/lib/api';
import {
  Users,
  FileCheck,
  Hash,
  Search,
  Eye,
  FileText,
  Calendar,
  ArrowUpRight,
} from 'lucide-react';

interface PrincipalRecord {
  wallet_address: string;
  email_hash: string | null;
  consent_count: number;
  created_at: string;
  last_active: string | null;
  consents: ConsentRecord[];
}

interface PrincipalsListResponse {
  data: PrincipalRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export default function PrincipalsPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const limit = 10;

  const { data: statsResponse, isLoading: statsLoading } = useQuery({
    queryKey: ['consents', 'stats'],
    queryFn: api.consents.stats,
  });

  const { data: response, isLoading } = useQuery<PrincipalsListResponse>({
    queryKey: ['principals', 'list', page, limit],
    queryFn: () =>
      fetch(
        `http://localhost:8000/api/v1/principals?page=${page}&limit=${limit}${
          search ? `&search=${encodeURIComponent(search)}` : ''
        }`,
      ).then(async (res) => {
        if (!res.ok) throw new Error('Failed to fetch principals');
        const json = await res.json();
        return json.data ?? json;
      }),
  });

  const principals: PrincipalRecord[] = response?.data || [];
  const total = response?.total || 0;
  const totalPages = response?.total_pages || Math.ceil(total / limit);

  const stats = statsResponse || {};
  const avgConsentsPerUser =
    stats.total_principals > 0
      ? (stats.total_consents / stats.total_principals).toFixed(1)
      : '0';

  const filtered = search
    ? principals.filter(
        (p: PrincipalRecord) =>
          p.wallet_address.toLowerCase().includes(search.toLowerCase()) ||
          (p.email_hash &&
            p.email_hash.toLowerCase().includes(search.toLowerCase())),
      )
    : principals;

  return (
    <Layout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Data Principals</h1>
          <p className="text-gray-600 mt-1">
            Individuals who have granted consent for their data usage
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Total Users</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {statsLoading
                    ? '...'
                    : (stats.total_principals ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-blue-500 p-3 rounded-lg">
                <Users className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Active Consents</div>
                <div className="text-2xl font-bold text-green-600 mt-1">
                  {statsLoading
                    ? '...'
                    : (stats.active_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-green-500 p-3 rounded-lg">
                <FileCheck className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Avg Consents/User</div>
                <div className="text-2xl font-bold text-purple-600 mt-1">
                  {statsLoading ? '...' : avgConsentsPerUser}
                </div>
              </div>
              <div className="bg-purple-500 p-3 rounded-lg">
                <Hash className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Consent Rate</div>
                <div className="text-2xl font-bold text-blue-600 mt-1">
                  {statsLoading
                    ? '...'
                    : `${(stats.consent_rate ?? 0).toFixed(1)}%`}
                </div>
              </div>
              <div className="bg-indigo-500 p-3 rounded-lg">
                <ArrowUpRight className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by wallet address or email hash..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">
              Loading data principals...
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No data principals found
            </div>
          ) : (
            <>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Wallet Address
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email Hash
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Consent Count
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Active
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filtered.map((principal: PrincipalRecord) => (
                    <tr key={principal.wallet_address} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm font-medium text-indigo-700">
                            {principal.wallet_address.charAt(0)}
                          </div>
                          <span className="text-sm font-mono text-gray-900">
                            {principal.wallet_address.slice(0, 6)}...
                            {principal.wallet_address.slice(-4)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono text-xs">
                        {principal.email_hash
                          ? `${principal.email_hash.slice(0, 12)}...`
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${
                            principal.consent_count > 5
                              ? 'bg-green-100 text-green-800'
                              : principal.consent_count > 0
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {principal.consent_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {principal.last_active
                          ? new Date(principal.last_active).toLocaleDateString()
                          : 'Never'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          {new Date(principal.created_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                        <button className="text-blue-600 hover:text-blue-900 inline-flex items-center gap-1">
                          <Eye className="w-3.5 h-3.5" />
                          View Profile
                        </button>
                        <button className="text-green-600 hover:text-green-900 inline-flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" />
                          View Consents
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="bg-gray-50 px-6 py-3 flex items-center justify-between border-t border-gray-200">
                  <div className="text-sm text-gray-700">
                    Showing {(page - 1) * limit + 1} to{' '}
                    {Math.min(page * limit, total)} of {total}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 text-sm"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                      disabled={page === totalPages}
                      className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 text-sm"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
