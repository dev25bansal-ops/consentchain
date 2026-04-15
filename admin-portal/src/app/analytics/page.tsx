'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { api, ConsentTimeSeriesPoint } from '@/lib/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';
import {
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  Calendar,
  ArrowDown,
  ArrowUp,
  Minus,
} from 'lucide-react';

const PIE_COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
];

interface PurposeBreakdown {
  purpose: string;
  count: number;
}

interface DataTypeBreakdown {
  data_type: string;
  count: number;
}

interface AnalyticsOverview {
  consents_over_time: ConsentTimeSeriesPoint[];
  by_purpose: PurposeBreakdown[];
  by_data_type: DataTypeBreakdown[];
}

export default function AnalyticsPage() {
  const [months, setMonths] = useState(6);

  const { data: statsResponse, isLoading: statsLoading } = useQuery({
    queryKey: ['consents', 'stats'],
    queryFn: api.consents.stats,
  });

  const { data: timeseriesResponse, isLoading: timeseriesLoading } = useQuery({
    queryKey: ['consents', 'timeseries', months],
    queryFn: () => api.consents.timeseries(months),
    staleTime: 1000 * 60 * 5,
  });

  const { data: analyticsData, isLoading: analyticsLoading } = useQuery<AnalyticsOverview>({
    queryKey: ['analytics', 'overview', months],
    queryFn: () =>
      fetch(
        `http://localhost:8000/api/v1/analytics/overview?months=${months}`,
      ).then(async (res) => {
        if (!res.ok) throw new Error('Failed to fetch analytics');
        const json = await res.json();
        return json.data ?? json;
      }),
    staleTime: 1000 * 60 * 5,
  });

  const stats = statsResponse || {};
  const timeseries: ConsentTimeSeriesPoint[] =
    timeseriesResponse?.timeseries || [];
  const purposeData: PurposeBreakdown[] = analyticsData?.by_purpose || [];
  const dataTypeData: DataTypeBreakdown[] = analyticsData?.by_data_type || [];

  // Compute trend direction from timeseries
  const getTrend = () => {
    if (timeseries.length < 2) return { direction: 'stable' as const, value: 0 };
    const last = timeseries[timeseries.length - 1];
    const prev = timeseries[timeseries.length - 2];
    const diff = last.granted - prev.granted;
    const pct = prev.granted > 0 ? ((diff / prev.granted) * 100).toFixed(1) : '0';
    return {
      direction: diff > 0 ? ('up' as const) : diff < 0 ? ('down' as const) : ('stable' as const),
      value: Math.abs(Number(pct)),
    };
  };

  const trend = getTrend();

  return (
    <Layout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
            <p className="text-gray-600 mt-1">
              Consent activity trends and insights
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value={1}>Last 1 Month</option>
              <option value={3}>Last 3 Months</option>
              <option value={6}>Last 6 Months</option>
              <option value={12}>Last 12 Months</option>
            </select>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Total Consents</div>
                <div className="text-2xl font-bold text-gray-900 mt-1">
                  {statsLoading
                    ? '...'
                    : (stats.total_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-blue-500 p-3 rounded-lg">
                <FileText className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-sm">
              {trend.direction === 'up' ? (
                <ArrowUp className="w-4 h-4 text-green-500" />
              ) : trend.direction === 'down' ? (
                <ArrowDown className="w-4 h-4 text-red-500" />
              ) : (
                <Minus className="w-4 h-4 text-gray-400" />
              )}
              <span
                className={
                  trend.direction === 'up'
                    ? 'text-green-600'
                    : trend.direction === 'down'
                    ? 'text-red-600'
                    : 'text-gray-500'
                }
              >
                {trend.value}% from previous period
              </span>
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
                <CheckCircle className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="mt-2 text-sm text-gray-500">
              {stats.total_consents
                ? `${((stats.active_consents / stats.total_consents) * 100).toFixed(1)}% of total`
                : '0% of total'}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Revoked</div>
                <div className="text-2xl font-bold text-red-600 mt-1">
                  {statsLoading
                    ? '...'
                    : (stats.revoked_consents ?? 0).toLocaleString()}
                </div>
              </div>
              <div className="bg-red-500 p-3 rounded-lg">
                <XCircle className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="mt-2 text-sm text-gray-500">
              {stats.total_consents
                ? `${((stats.revoked_consents / stats.total_consents) * 100).toFixed(1)}% of total`
                : '0% of total'}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">Avg. Expiry (days)</div>
                <div className="text-2xl font-bold text-yellow-600 mt-1">
                  {statsLoading ? '...' : Math.round(stats.avg_expiry_days ?? 0)}
                </div>
              </div>
              <div className="bg-yellow-500 p-3 rounded-lg">
                <Clock className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-sm text-gray-500">
              <TrendingUp className="w-3.5 h-3.5" />
              Average consent lifetime
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="space-y-6">
          {/* Consents Over Time - Line Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Consents Over Time</h3>
            {timeseriesLoading ? (
              <div className="h-72 flex items-center justify-center text-gray-500">
                Loading chart...
              </div>
            ) : timeseries.length === 0 ? (
              <div className="h-72 flex items-center justify-center text-gray-500">
                No time series data available
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={timeseries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="granted"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      name="Granted"
                    />
                    <Line
                      type="monotone"
                      dataKey="revoked"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      name="Revoked"
                    />
                    <Line
                      type="monotone"
                      dataKey="expired"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      name="Expired"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Purpose & Data Type Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* By Purpose - Pie Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Consents by Purpose</h3>
              {analyticsLoading ? (
                <div className="h-72 flex items-center justify-center text-gray-500">
                  Loading chart...
                </div>
              ) : purposeData.length === 0 ? (
                <div className="h-72 flex items-center justify-center text-gray-500">
                  No purpose data available
                </div>
              ) : (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={purposeData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ purpose, percent }) =>
                          `${purpose} (${(percent * 100).toFixed(0)}%)`
                        }
                        outerRadius={90}
                        fill="#8884d8"
                        dataKey="count"
                        nameKey="purpose"
                      >
                        {purposeData.map((_entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={PIE_COLORS[index % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* By Data Type - Bar Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Consents by Data Type</h3>
              {analyticsLoading ? (
                <div className="h-72 flex items-center justify-center text-gray-500">
                  Loading chart...
                </div>
              ) : dataTypeData.length === 0 ? (
                <div className="h-72 flex items-center justify-center text-gray-500">
                  No data type data available
                </div>
              ) : (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dataTypeData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="data_type"
                        tick={{ fontSize: 12 }}
                        angle={-30}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                        }}
                      />
                      <Bar
                        dataKey="count"
                        fill="#3b82f6"
                        name="Consents"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
