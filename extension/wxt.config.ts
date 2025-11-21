import { defineConfig } from 'wxt';

// See https://wxt.dev/api/config.html
export default defineConfig({
  extensionApi: 'chrome',
  manifest: {
    name: 'Web3 Antivirus',
    description: 'Real-time scam protection for Web3 transactions',
    version: '1.0.0',
    permissions: [
      'activeTab',
      'storage',
      'scripting',
      'webRequest',
      'webNavigation',
      'notifications'
    ],
    host_permissions: [
      'https://api.etherscan.io/*',
      'https://api.rarible.org/*',
      'http://localhost:8000/*'
    ],
    action: {
      default_popup: 'popup.html'
    }
  }
});

