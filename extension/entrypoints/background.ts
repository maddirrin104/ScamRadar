export default defineBackground(() => {
  console.log('[Web3 Antivirus] Background service worker loaded');

  // Listen for messages from content script (optional logging/analytics)
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'METAMASK_TRANSACTION') {
      console.log('[Web3 Antivirus] Transaction detected from tab:', sender.tab?.id);
      // Content script handles UI directly with in-page modal
      // Background script can log, track analytics, etc.
      sendResponse({ success: true });
    }
    return true;
  });
  
  console.log('[Web3 Antivirus] Ready to intercept transactions');
});

