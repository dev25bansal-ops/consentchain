'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { api, ConsentRecord } from '@/lib/api';
import {
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Search,
  Eye,
  Ban,
  Calendar,
} from 'lucide-react';

const statusColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  REVOKED: 'bg-red-100 text-red-800',
  EXPIRED: 'bg-yellow-100 text-yellow-800',
  PENDING: 'bg-blue-100 text-blue-800',
};

const purposeOptions = [
  'all',
  'analytics',
  'marketing',
  'service-delivery',
  'research',
  'compliance',
  'personalization',
];

export default function ConsentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [purposeFilter, setPurposeFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const limit = 10;

  const { data: statsResponse, isLoading: statsLoading } = useQuery({
    queryKey: ['consents', 'stats'],
    queryFn: api.consents.stats,
  });

  const { data: response, isLoading } = useQuery({
    queryKey: ['consents', 'list', page, limit, statusFilter, purposeFilter],
    queryFn: () =>
      api.consents.list({
        page,
        limit,
        status: statusFilter === 'all' ? undefined : statusFilter,
      }),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) =>
      fetch(`http://localhost:8000/api/v1/consent/${id}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }).then((res) => {
        if (!res.ok) throw new Error('Failed to revoke consent');
        return res.json();
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consents', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['consents', 'stats'] });
    },
  });

  const consents: ConsentRecord[] = response?.data || [];
  const total = response?.total || 0;
  const totalPages = response?.pages || Math.ceil(total / limit);

  const filtered = consents.filter((c: ConsentRecord) => {
    if (
      statusFilter !== 'all' &&
      c.status !== statusFilter.toUpperCase() &&
      c.status !== statusFilter
    )
      return false;
    if (
      purposeFilter !== 'all' &&
      c.purpose !== purposeFilter
    )
      return false;
    if (dateFrom && c.granted_at && new Date(c.granted_at) < new Date(dateFrom))
      return false;
    if (dateTo && c.granted_at && new Date(c.granted_at) > new Date(dateTo + 'T23:59:59'))
      return false;
    if (search) {
      const lower = search.toLowerCase();
      return (
        c.id.toLowerCase().includes(lower) ||
        c.principal_id.toLowerCase().includes(lower) ||
        c.fiduciary_id.toLowerCase().includes(lower) ||
        c.purpose.toLowerCase().includes(lower)
      );
    }
    return true;
  });

  const handleRevoke = (id: string) => {
    if (confirm('Are you sure you want to revoke this consent?')) {
      revokeMutation.mutate(id);
    }
  };

  const stats = statsResponse || {};

  return (
    <Layout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Consent Records</h1>
          <p className="text-gray-600 mt-1">
            Manage and monitor all consent grants across the platform
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Total Consents</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {statsLoading ? '...' : (stats.total_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-blue-500 p-3 rounded-lg">
                <FileText className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Active</div>
                <div className="text-2xl font-bold text-green-600 mt-1">
                  {statsLoading ? '...' : (stats.active_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-green-500 p-3 rounded-lg">
                <CheckCircle className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Revoked</div>
                <div className="text-2xl font-bold text-red-600 mt-1">
                  {statsLoading ? '...' : (stats.revoked_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-red-500 p-3 rounded-lg">
                <XCircle className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Expired</div>
                <div className="text-2xl font-bold text-yellow-600 mt-1">
                  {statsLoading ? '...' : (stats.expired_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-yellow-500 p-3 rounded-lg">
                <Clock className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Pending</div>
                <div className="text-2xl font-bold text-blue-600 mt-1">
                  {statsLoading
                    ? '...'
                    : Math.max(
                        0,
                        (stats.total_consents ?? 0) -
                          (stats.active_consents ?? 0) -
                          (stats.revoked_consents ?? 0) -
                          (stats.expired_consents ?? 0),
                      ).toLocaleString()}
                </div>
              </div>
              <div className="bg-purple-500 p-3 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by ID, principal, fiduciary, or purpose..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="ACTIVE">Active</option>
              <option value="REVOKED">Revoked</option>
              <option value="EXPIRED">Expired</option>
              <option value="PENDING">Pending</option>
            </select>
            <select
              value={purposeFilter}
              onChange={(e) => setPurposeFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {purposeOptions.map((p) => (
                <option key={p} value={p}>
                  {p === 'all' ? 'All Purposes' : p.charAt(0).toUpperCase() + p.slice(1).replace('-', ' ')}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-gray-400" />
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                placeholder="From"
              />
              <span className="text-gray-400">-</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                placeholder="To"
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Loading consent records...</div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No consent records found matching your filters
            </div>
          ) : (
            <>
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Principal
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fiduciary
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Purpose
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Granted
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Expires
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filtered.map((consent: ConsentRecord) => (
                    <tr key={consent.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                        {consent.consent_hash
                          ? consent.consent_hash.slice(0, 10) + '...'
                          : consent.id.slice(0, 8)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-xs font-medium text-blue-700">
                            P
                          </div>
                          <span className="font-mono text-xs">
                            {consent.principal_id.slice(0, 10)}...
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className="font-mono text-xs">
                          {consent.fiduciary_id.slice(0, 10)}...
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className="px-2 py-1 bg-gray-100 rounded text-xs capitalize">
                          {consent.purpose}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${
                            statusColors[consent.status] || 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {consent.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {consent.granted_at
                          ? new Date(consent.granted_at).toLocaleDateString()
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {consent.expires_at
                          ? new Date(consent.expires_at).toLocaleDateString()
                          : 'No expiry'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                        <button className="text-blue-600 hover:text-blue-900 inline-flex items-center gap-1">
                          <Eye className="w-3.5 h-3.5" />
                          View
                        </button>
                        {consent.status === 'ACTIVE' && (
                          <button
                            onClick={() => handleRevoke(consent.id)}
                            disabled={revokeMutation.isPending}
                            className="text-red-600 hover:text-red-900 inline-flex items-center gap-1 disabled:opacity-50"
                          >
                            <Ban className="w-3.5 h-3.5" />
                            Revoke
                          </button>
                        )}
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
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
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
