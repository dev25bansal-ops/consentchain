'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { api, WebhookSubscription } from '@/lib/api';
import {
  Bell,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Search,
  Play,
  Trash2,
  ExternalLink,
  Clock,
  Zap,
} from 'lucide-react';

interface WebhookDeliveryAttempt {
  id: string;
  webhook_id: string;
  event_type: string;
  status: 'success' | 'failed' | 'pending';
  response_code: number | null;
  response_body: string | null;
  attempted_at: string;
  next_retry_at: string | null;
}

interface WebhookWithStats extends WebhookSubscription {
  last_delivery_at: string | null;
  last_delivery_status: 'success' | 'failed' | null;
  success_rate: number;
  total_deliveries: number;
  failed_deliveries: number;
}

interface WebhooksListResponse {
  data: WebhookWithStats[];
  total: number;
}

export default function WebhooksPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const { data: response, isLoading } = useQuery<WebhooksListResponse>({
    queryKey: ['webhooks', 'list', statusFilter],
    queryFn: () =>
      fetch(
        `http://localhost:8000/api/v1/webhooks${
          statusFilter !== 'all' ? `?status=${statusFilter}` : ''
        }`,
      ).then(async (res) => {
        if (!res.ok) throw new Error('Failed to fetch webhooks');
        const json = await res.json();
        return json.data ?? json;
      }),
  });

  const { data: recentDeliveries, isLoading: deliveriesLoading } = useQuery<WebhookDeliveryAttempt[]>({
    queryKey: ['webhooks', 'recent-deliveries'],
    queryFn: () =>
      fetch('http://localhost:8000/api/v1/webhooks/deliveries?limit=10').then(
        async (res) => {
          if (!res.ok) throw new Error('Failed to fetch deliveries');
          const json = await res.json();
          return json.data ?? json;
        },
      ),
    refetchInterval: 30000,
  });

  const testWebhookMutation = useMutation({
    mutationFn: (id: string) =>
      fetch(`http://localhost:8000/api/v1/webhooks/${id}/test`, {
        method: 'POST',
      }).then(async (res) => {
        if (!res.ok) throw new Error('Failed to test webhook');
        return res.json();
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks', 'list'] });
    },
  });

  const deleteWebhookMutation = useMutation({
    mutationFn: (id: string) =>
      fetch(`http://localhost:8000/api/v1/webhooks/${id}`, {
        method: 'DELETE',
      }).then(async (res) => {
        if (!res.ok) throw new Error('Failed to delete webhook');
        return res.json();
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks', 'list'] });
    },
  });

  const webhooks: WebhookWithStats[] = response?.data || [];
  const deliveries: WebhookDeliveryAttempt[] = recentDeliveries || [];

  const totalWebhooks = webhooks.length;
  const activeWebhooks = webhooks.filter((w) => w.active).length;
  const totalFailed = webhooks.reduce((sum, w) => sum + w.failed_deliveries, 0);

  const filtered = webhooks.filter((w) => {
    if (search) {
      const lower = search.toLowerCase();
      return (
        w.callback_url.toLowerCase().includes(lower) ||
        w.fiduciary_id.toLowerCase().includes(lower) ||
        w.events.some((e) => e.toLowerCase().includes(lower))
      );
    }
    return true;
  });

  const handleTest = (id: string) => {
    testWebhookMutation.mutate(id);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this webhook subscription?')) {
      deleteWebhookMutation.mutate(id);
    }
  };

  return (
    <Layout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="text-gray-600 mt-1">
            Manage webhook subscriptions and monitor delivery status
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Total Subscriptions</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {totalWebhooks}
                </div>
              </div>
              <div className="bg-blue-500 p-3 rounded-lg">
                <Bell className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Active</div>
                <div className="text-2xl font-bold text-green-600 mt-1">
                  {activeWebhooks}
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
                <div className="text-sm text-gray-600">Inactive</div>
                <div className="text-2xl font-bold text-gray-600 mt-1">
                  {totalWebhooks - activeWebhooks}
                </div>
              </div>
              <div className="bg-gray-500 p-3 rounded-lg">
                <XCircle className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Failed Deliveries</div>
                <div className="text-2xl font-bold text-red-600 mt-1">
                  {totalFailed}
                </div>
              </div>
              <div className="bg-red-500 p-3 rounded-lg">
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
                placeholder="Search by URL, fiduciary, or event..."
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
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        {/* Webhooks Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">
              Loading webhook subscriptions...
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No webhook subscriptions found
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fiduciary
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Callback URL
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Events
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Delivery
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Success Rate
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filtered.map((webhook: WebhookWithStats) => (
                  <tr key={webhook.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className="font-mono text-xs">
                        {webhook.fiduciary_id.slice(0, 10)}...
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600">
                      <a
                        href={webhook.callback_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 hover:underline"
                      >
                        {webhook.callback_url.length > 40
                          ? webhook.callback_url.slice(0, 40) + '...'
                          : webhook.callback_url}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-wrap gap-1">
                        {webhook.events.slice(0, 3).map((event: string) => (
                          <span
                            key={event}
                            className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs capitalize"
                          >
                            {event.replace(/_/g, ' ')}
                          </span>
                        ))}
                        {webhook.events.length > 3 && (
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
                            +{webhook.events.length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          webhook.active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {webhook.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {webhook.last_delivery_at ? (
                        <div className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {new Date(
                            webhook.last_delivery_at,
                          ).toLocaleDateString()}
                          <span
                            className={`ml-1 w-2 h-2 rounded-full ${
                              webhook.last_delivery_status === 'success'
                                ? 'bg-green-500'
                                : 'bg-red-500'
                            }`}
                          />
                        </div>
                      ) : (
                        'Never'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              webhook.success_rate >= 90
                                ? 'bg-green-500'
                                : webhook.success_rate >= 70
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                            }`}
                            style={{ width: `${webhook.success_rate}%` }}
                          />
                        </div>
                        <span className="text-gray-600 text-xs">
                          {webhook.success_rate.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => handleTest(webhook.id)}
                        disabled={testWebhookMutation.isPending}
                        className="text-blue-600 hover:text-blue-900 inline-flex items-center gap-1 disabled:opacity-50"
                      >
                        <Zap className="w-3.5 h-3.5" />
                        Test
                      </button>
                      <button
                        onClick={() => handleDelete(webhook.id)}
                        disabled={deleteWebhookMutation.isPending}
                        className="text-red-600 hover:text-red-900 inline-flex items-center gap-1 disabled:opacity-50"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Recent Delivery Attempts */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Delivery Attempts</h3>
          {deliveriesLoading ? (
            <div className="text-center py-4 text-gray-500">
              Loading delivery attempts...
            </div>
          ) : deliveries.length === 0 ? (
            <div className="text-center py-4 text-gray-500">
              No recent delivery attempts
            </div>
          ) : (
            <div className="space-y-3">
              {deliveries.map((delivery: WebhookDeliveryAttempt) => (
                <div
                  key={delivery.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        delivery.status === 'success'
                          ? 'bg-green-500'
                          : delivery.status === 'failed'
                          ? 'bg-red-500'
                          : 'bg-yellow-500'
                      }`}
                    />
                    <div>
                      <div className="text-sm font-medium text-gray-900 capitalize">
                        {delivery.event_type.replace(/_/g, ' ')}
                      </div>
                      <div className="text-xs text-gray-500 font-mono">
                        Webhook: {delivery.webhook_id.slice(0, 10)}...
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {delivery.response_code && (
                      <span
                        className={`text-xs font-mono px-2 py-0.5 rounded ${
                          delivery.response_code >= 200 &&
                          delivery.response_code < 300
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {delivery.response_code}
                      </span>
                    )}
                    <span className="text-xs text-gray-500">
                      {new Date(delivery.attempted_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
