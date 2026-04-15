'use client';

import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import {
  Settings,
  Save,
  Globe,
  Key,
  Link,
  Bell,
  Shield,
  Puzzle,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
} from 'lucide-react';

type ToastType = 'success' | 'error';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface SettingsForm {
  // General
  siteName: string;
  siteUrl: string;
  timezone: string;
  language: string;

  // API
  apiUrl: string;
  apiKey: string;
  rateLimitPerMinute: string;
  enableCors: boolean;

  // Blockchain
  network: string;
  rpcUrl: string;
  contractAddress: string;
  gasLimit: string;
  confirmationBlocks: string;

  // Notifications
  emailNotifications: boolean;
  webhookRetryCount: string;
  notificationEmail: string;
  slackWebhookUrl: string;

  // Security
  mfaEnabled: boolean;
  sessionTimeout: string;
  ipWhitelist: string;
  auditLogEnabled: boolean;

  // Integrations
  sentryDsn: string;
  datadogApiKey: string;
  enableMetrics: boolean;
  logLevel: string;
}

const initialSettings: SettingsForm = {
  siteName: 'ConsentChain Admin',
  siteUrl: 'http://localhost:3001',
  timezone: 'UTC',
  language: 'en',

  apiUrl: 'http://localhost:8000',
  apiKey: '',
  rateLimitPerMinute: '60',
  enableCors: true,

  network: 'testnet',
  rpcUrl: 'https://testnet-api.algonode.cloud',
  contractAddress: '',
  gasLimit: '1000',
  confirmationBlocks: '3',

  emailNotifications: true,
  webhookRetryCount: '3',
  notificationEmail: 'admin@consentchain.com',
  slackWebhookUrl: '',

  mfaEnabled: false,
  sessionTimeout: '30',
  ipWhitelist: '',
  auditLogEnabled: true,

  sentryDsn: '',
  datadogApiKey: '',
  enableMetrics: true,
  logLevel: 'info',
};

const sectionIcons: Record<string, React.ReactNode> = {
  general: <Globe className="w-5 h-5" />,
  api: <Key className="w-5 h-5" />,
  blockchain: <Link className="w-5 h-5" />,
  notifications: <Bell className="w-5 h-5" />,
  security: <Shield className="w-5 h-5" />,
  integrations: <Puzzle className="w-5 h-5" />,
};

const sections = [
  { id: 'general', label: 'General' },
  { id: 'api', label: 'API Configuration' },
  { id: 'blockchain', label: 'Blockchain' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'security', label: 'Security' },
  { id: 'integrations', label: 'Integrations' },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsForm>(initialSettings);
  const [activeSection, setActiveSection] = useState('general');
  const [showApiKey, setShowApiKey] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const saveMutation = useMutation({
    mutationFn: async (data: SettingsForm) => {
      const response = await fetch('http://localhost:8000/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to save settings');
      }
      return response.json();
    },
    onSuccess: () => {
      addToast('success', 'Settings saved successfully');
    },
    onError: (error: Error) => {
      addToast('error', `Failed to save settings: ${error.message}`);
    },
  });

  const handleSave = () => {
    saveMutation.mutate(settings);
  };

  const updateSetting = <K extends keyof SettingsForm>(
    key: K,
    value: SettingsForm[K],
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const renderGeneralSection = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Site Name
        </label>
        <input
          type="text"
          value={settings.siteName}
          onChange={(e) => updateSetting('siteName', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="ConsentChain Admin"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Site URL
        </label>
        <input
          type="url"
          value={settings.siteUrl}
          onChange={(e) => updateSetting('siteUrl', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="https://admin.consentchain.com"
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Timezone
          </label>
          <select
            value={settings.timezone}
            onChange={(e) => updateSetting('timezone', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="UTC">UTC</option>
            <option value="America/New_York">Eastern Time</option>
            <option value="America/Chicago">Central Time</option>
            <option value="America/Denver">Mountain Time</option>
            <option value="America/Los_Angeles">Pacific Time</option>
            <option value="Europe/London">London</option>
            <option value="Europe/Paris">Paris</option>
            <option value="Asia/Kolkata">India Standard Time</option>
            <option value="Asia/Tokyo">Tokyo</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Language
          </label>
          <select
            value={settings.language}
            onChange={(e) => updateSetting('language', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
            <option value="hi">Hindi</option>
          </select>
        </div>
      </div>
    </div>
  );

  const renderApiSection = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          API Base URL
        </label>
        <input
          type="url"
          value={settings.apiUrl}
          onChange={(e) => updateSetting('apiUrl', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="http://localhost:8000"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          API Key
        </label>
        <div className="relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            value={settings.apiKey}
            onChange={(e) => updateSetting('apiKey', e.target.value)}
            className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
            placeholder="Enter API key"
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {showApiKey ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Rate Limit (requests/min)
          </label>
          <input
            type="number"
            value={settings.rateLimitPerMinute}
            onChange={(e) =>
              updateSetting('rateLimitPerMinute', e.target.value)
            }
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="1"
            max="1000"
          />
        </div>
        <div className="flex items-center pt-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enableCors}
              onChange={(e) => updateSetting('enableCors', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Enable CORS</span>
          </label>
        </div>
      </div>
    </div>
  );

  const renderBlockchainSection = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Network
        </label>
        <select
          value={settings.network}
          onChange={(e) => updateSetting('network', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="mainnet">Algorand Mainnet</option>
          <option value="testnet">Algorand Testnet</option>
          <option value="betanet">Algorand Betanet</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          RPC URL
        </label>
        <input
          type="url"
          value={settings.rpcUrl}
          onChange={(e) => updateSetting('rpcUrl', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="https://mainnet-api.algonode.cloud"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Contract Address (ASA ID)
        </label>
        <input
          type="text"
          value={settings.contractAddress}
          onChange={(e) => updateSetting('contractAddress', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="Enter ASA ID or smart contract address"
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Gas Limit (microAlgos)
          </label>
          <input
            type="number"
            value={settings.gasLimit}
            onChange={(e) => updateSetting('gasLimit', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="100"
            max="10000"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Confirmation Blocks
          </label>
          <input
            type="number"
            value={settings.confirmationBlocks}
            onChange={(e) =>
              updateSetting('confirmationBlocks', e.target.value)
            }
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="1"
            max="100"
          />
        </div>
      </div>
    </div>
  );

  const renderNotificationsSection = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.emailNotifications}
            onChange={(e) =>
              updateSetting('emailNotifications', e.target.checked)
            }
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">
            Enable Email Notifications
          </span>
        </label>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Notification Email
        </label>
        <input
          type="email"
          value={settings.notificationEmail}
          onChange={(e) =>
            updateSetting('notificationEmail', e.target.value)
          }
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="admin@consentchain.com"
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Webhook Retry Count
          </label>
          <input
            type="number"
            value={settings.webhookRetryCount}
            onChange={(e) =>
              updateSetting('webhookRetryCount', e.target.value)
            }
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="0"
            max="10"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Slack Webhook URL
          </label>
          <input
            type="url"
            value={settings.slackWebhookUrl}
            onChange={(e) =>
              updateSetting('slackWebhookUrl', e.target.value)
            }
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            placeholder="https://hooks.slack.com/services/..."
          />
        </div>
      </div>
    </div>
  );

  const renderSecuritySection = () => (
    <div className="space-y-4">
      <div className="space-y-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.mfaEnabled}
            onChange={(e) => updateSetting('mfaEnabled', e.target.checked)}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">
            Enable Multi-Factor Authentication
          </span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.auditLogEnabled}
            onChange={(e) =>
              updateSetting('auditLogEnabled', e.target.checked)
            }
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Enable Audit Logging</span>
        </label>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Session Timeout (minutes)
        </label>
        <input
          type="number"
          value={settings.sessionTimeout}
          onChange={(e) => updateSetting('sessionTimeout', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          min="5"
          max="480"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          IP Whitelist (comma-separated)
        </label>
        <input
          type="text"
          value={settings.ipWhitelist}
          onChange={(e) => updateSetting('ipWhitelist', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="192.168.1.1, 10.0.0.0/8"
        />
        <p className="text-xs text-gray-500 mt-1">
          Leave empty to allow all IPs. Use CIDR notation for ranges.
        </p>
      </div>
    </div>
  );

  const renderIntegrationsSection = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Sentry DSN
        </label>
        <input
          type="text"
          value={settings.sentryDsn}
          onChange={(e) => updateSetting('sentryDsn', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="https://xxx@o0.ingest.sentry.io/0"
        />
        <p className="text-xs text-gray-500 mt-1">
          For error tracking and crash reporting
        </p>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Datadog API Key
        </label>
        <input
          type="password"
          value={settings.datadogApiKey}
          onChange={(e) => updateSetting('datadogApiKey', e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="Enter Datadog API key"
        />
        <p className="text-xs text-gray-500 mt-1">
          For metrics and log aggregation
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex items-center pt-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enableMetrics}
              onChange={(e) =>
                updateSetting('enableMetrics', e.target.checked)
              }
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">
              Enable Metrics Collection
            </span>
          </label>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Log Level
          </label>
          <select
            value={settings.logLevel}
            onChange={(e) => updateSetting('logLevel', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warn">Warning</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>
    </div>
  );

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'general':
        return renderGeneralSection();
      case 'api':
        return renderApiSection();
      case 'blockchain':
        return renderBlockchainSection();
      case 'notifications':
        return renderNotificationsSection();
      case 'security':
        return renderSecuritySection();
      case 'integrations':
        return renderIntegrationsSection();
      default:
        return null;
    }
  };

  return (
    <Layout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600 mt-1">
              Configure your ConsentChain admin portal
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save className="w-4 h-4" />
            {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Section Navigation */}
          <div className="lg:col-span-1">
            <nav className="bg-white rounded-lg shadow p-2 space-y-1">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors text-left ${
                    activeSection === section.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <span
                    className={
                      activeSection === section.id
                        ? 'text-blue-600'
                        : 'text-gray-400'
                    }
                  >
                    {sectionIcons[section.id]}
                  </span>
                  {section.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Section Content */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <span className="text-blue-600">
                  {sectionIcons[activeSection]}
                </span>
                {sections.find((s) => s.id === activeSection)?.label}
              </h2>
              {renderActiveSection()}
            </div>
          </div>
        </div>
      </div>

      {/* Toast Notifications */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-white ${
              toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle className="w-5 h-5" />
            ) : (
              <XCircle className="w-5 h-5" />
            )}
            <span className="text-sm">{toast.message}</span>
          </div>
        ))}
      </div>
    </Layout>
  );
}
