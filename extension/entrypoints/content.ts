export default defineContentScript({
  matches: ['<all_urls>'],
  runAt: 'document_start',
  main() {
    console.log('[Web3 Antivirus] Content script loaded');
    // Intercept MetaMask transaction requests
    interceptMetaMaskTransactions();
  },
});

function interceptMetaMaskTransactions() {
  // Inject script to intercept window.ethereum before page loads
  const script = document.createElement('script');
  script.id = 'web3-antivirus-injector';
  script.textContent = `
    (function() {
      console.log('[Web3 Antivirus] Injecting MetaMask interceptor...');
      
      // Try to intercept immediately if ethereum exists
      if (window.ethereum) {
        setupInterceptor();
      } else {
        // Watch for ethereum to be added
        let attempts = 0;
        const checkInterval = setInterval(() => {
          attempts++;
          if (window.ethereum) {
            clearInterval(checkInterval);
            console.log('[Web3 Antivirus] Found window.ethereum, setting up interceptor');
            setupInterceptor();
          } else if (attempts > 50) { // 5 seconds max
            clearInterval(checkInterval);
            console.warn('[Web3 Antivirus] window.ethereum not found after 5s');
          }
        }, 100);
      }
      
      function setupInterceptor() {
        if (window.ethereum._web3AntivirusPatched) {
          console.log('[Web3 Antivirus] Already patched');
          return;
        }
        
        const originalRequest = window.ethereum.request.bind(window.ethereum);
        window.ethereum._web3AntivirusPatched = true;
        
        window.ethereum.request = async function(args) {
          console.log('[Web3 Antivirus] Request intercepted:', args.method);
          
          // Intercept transaction requests
          if (args && (args.method === 'eth_sendTransaction' || args.method === 'eth_signTransaction')) {
            const tx = args.params && args.params[0];
            if (tx) {
              console.log('[Web3 Antivirus] Transaction detected, analyzing...', tx);
              
              // Send transaction data to extension via postMessage
              window.postMessage({
                type: 'WEB3_ANTIVIRUS_TRANSACTION',
                data: {
                  from: tx.from || '',
                  to: tx.to || '',
                  value: tx.value || '0x0',
                  data: tx.data || '0x',
                  gas: tx.gas || tx.gasLimit || '0x0',
                  gasPrice: tx.gasPrice || tx.maxFeePerGas || '0x0',
                  chainId: tx.chainId || '0x1',
                  method: args.method
                }
              }, '*');
              
              // Wait for user decision
              return new Promise((resolve, reject) => {
                let timeoutId;
                const checkDecision = setInterval(() => {
                  if (window._web3AntivirusDecision) {
                    clearInterval(checkDecision);
                    clearTimeout(timeoutId);
                    
                    const decision = window._web3AntivirusDecision;
                    delete window._web3AntivirusDecision;
                    
                    if (decision === 'approve') {
                      console.log('[Web3 Antivirus] Transaction APPROVED by user');
                      originalRequest(args).then(resolve).catch(reject);
                    } else {
                      console.log('[Web3 Antivirus] Transaction REJECTED by user');
                      reject(new Error('Transaction rejected by Web3 Antivirus'));
                    }
                  }
                }, 100);
                
                // Timeout after 60 seconds
                timeoutId = setTimeout(() => {
                  clearInterval(checkDecision);
                  console.warn('[Web3 Antivirus] Decision timeout, allowing transaction');
                  originalRequest(args).then(resolve).catch(reject);
                }, 60000);
              });
            }
          }
          
          // For other requests, proceed normally
          return originalRequest(args);
        };
        
        console.log('[Web3 Antivirus] MetaMask interceptor installed successfully!');
      }
    })();
  `;
  
  // Inject script ASAP
  (document.head || document.documentElement).prepend(script);
  
  // Listen for messages from injected script
  window.addEventListener('message', async (event) => {
    if (event.source !== window) return;
    
    if (event.data && event.data.type === 'WEB3_ANTIVIRUS_TRANSACTION') {
      console.log('[Web3 Antivirus] Transaction message received in content script');
      const transactionData = event.data.data;
      
      // Show in-page modal instead of trying to open popup
      showTransactionModal(transactionData);
    }
  });
}

// Create in-page modal for transaction analysis
async function showTransactionModal(transactionData: any) {
  console.log('[Web3 Antivirus] Creating transaction analysis modal...');
  
  // Remove existing modal if any
  const existingModal = document.getElementById('web3-antivirus-modal');
  if (existingModal) {
    existingModal.remove();
  }
  
  // Create modal overlay
  const modal = document.createElement('div');
  modal.id = 'web3-antivirus-modal';
  modal.innerHTML = `
    <style>
      #web3-antivirus-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.85);
        z-index: 999999999;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      #web3-antivirus-content {
        background: #1a1b1f;
        border-radius: 16px;
        padding: 32px;
        max-width: 500px;
        width: 90%;
        color: #fff;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
      }
      #web3-antivirus-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 24px;
      }
      #web3-antivirus-icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
      }
      #web3-antivirus-title {
        font-size: 24px;
        font-weight: 700;
        margin: 0;
      }
      #web3-antivirus-status {
        text-align: center;
        padding: 24px;
        margin: 24px 0;
        border-radius: 12px;
        background: #2a2b30;
      }
      .web3-antivirus-loading {
        display: inline-block;
        width: 40px;
        height: 40px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 16px;
      }
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      #web3-antivirus-details {
        background: #2a2b30;
        border-radius: 12px;
        padding: 16px;
        margin: 16px 0;
        font-size: 14px;
      }
      .web3-antivirus-detail-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #3a3b40;
      }
      .web3-antivirus-detail-row:last-child {
        border-bottom: none;
      }
      .web3-antivirus-label {
        color: #999;
      }
      .web3-antivirus-value {
        color: #fff;
        font-family: monospace;
        font-size: 12px;
      }
      #web3-antivirus-buttons {
        display: flex;
        gap: 12px;
        margin-top: 24px;
      }
      .web3-antivirus-btn {
        flex: 1;
        padding: 14px 24px;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }
      .web3-antivirus-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      #web3-antivirus-reject {
        background: #ef4444;
        color: white;
      }
      #web3-antivirus-reject:hover:not(:disabled) {
        background: #dc2626;
      }
      #web3-antivirus-approve {
        background: #10b981;
        color: white;
      }
      #web3-antivirus-approve:hover:not(:disabled) {
        background: #059669;
      }
      .web3-antivirus-risk-high {
        color: #ef4444;
        font-weight: 700;
      }
      .web3-antivirus-risk-medium {
        color: #f59e0b;
        font-weight: 700;
      }
      .web3-antivirus-risk-low {
        color: #10b981;
        font-weight: 700;
      }
    </style>
    
    <div id="web3-antivirus-content">
      <div id="web3-antivirus-header">
        <div id="web3-antivirus-icon">🛡️</div>
        <h2 id="web3-antivirus-title">Transaction Security Check</h2>
      </div>
      
      <div id="web3-antivirus-status">
        <div class="web3-antivirus-loading"></div>
        <div id="web3-antivirus-status-text">Analyzing transaction...</div>
      </div>
      
      <div id="web3-antivirus-details">
        <div class="web3-antivirus-detail-row">
          <span class="web3-antivirus-label">To:</span>
          <span class="web3-antivirus-value">${transactionData.to ? transactionData.to.substring(0, 10) + '...' + transactionData.to.substring(transactionData.to.length - 8) : 'N/A'}</span>
        </div>
        <div class="web3-antivirus-detail-row">
          <span class="web3-antivirus-label">Value:</span>
          <span class="web3-antivirus-value">${transactionData.value}</span>
        </div>
        <div class="web3-antivirus-detail-row">
          <span class="web3-antivirus-label">Gas Price:</span>
          <span class="web3-antivirus-value">${transactionData.gasPrice}</span>
        </div>
      </div>
      
      <div id="web3-antivirus-result" style="display: none;"></div>
      
      <div id="web3-antivirus-buttons">
        <button id="web3-antivirus-reject" class="web3-antivirus-btn" disabled>
          ❌ Reject
        </button>
        <button id="web3-antivirus-approve" class="web3-antivirus-btn" disabled>
          ✅ Approve
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Analyze transaction
  try {
    const result = await analyzeTransaction(transactionData);
    displayAnalysisResult(result, modal);
  } catch (error: any) {
    displayError(error, modal);
  }
}

async function analyzeTransaction(transactionData: any) {
  // Call backend API
  const response = await fetch('http://localhost:8000/detect/transaction', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from_address: transactionData.from,
      to_address: transactionData.to,
      value: transactionData.value,
      gasPrice: transactionData.gasPrice,
      gasUsed: transactionData.gas,
      explain: true,
      explain_with_llm: true
    })
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return await response.json();
}

function displayAnalysisResult(result: any, modal: HTMLElement) {
  const status = modal.querySelector('#web3-antivirus-status') as HTMLElement;
  const resultDiv = modal.querySelector('#web3-antivirus-result') as HTMLElement;
  const approveBtn = modal.querySelector('#web3-antivirus-approve') as HTMLButtonElement;
  const rejectBtn = modal.querySelector('#web3-antivirus-reject') as HTMLButtonElement;
  
  const prob = result.transaction_scam_probability;
  const isHighRisk = prob > 0.7;
  const isMediumRisk = prob > 0.4 && prob <= 0.7;
  
  status.style.display = 'none';
  resultDiv.style.display = 'block';
  
  const riskClass = isHighRisk ? 'web3-antivirus-risk-high' : 
                     isMediumRisk ? 'web3-antivirus-risk-medium' : 
                     'web3-antivirus-risk-low';
  
  const riskText = isHighRisk ? '🚨 HIGH RISK' :
                   isMediumRisk ? '⚠️ MEDIUM RISK' : 
                   '✅ LOW RISK';
  
  resultDiv.innerHTML = `
    <div style="text-align: center; padding: 20px; background: #2a2b30; border-radius: 12px;">
      <div class="${riskClass}" style="font-size: 20px; margin-bottom: 12px;">
        ${riskText}
      </div>
      <div style="font-size: 24px; font-weight: 700; margin-bottom: 16px;">
        ${(prob * 100).toFixed(1)}% Scam Probability
      </div>
      ${result.llm_explanations?.transaction ? `
        <div style="color: #ccc; font-size: 14px; line-height: 1.6;">
          ${result.llm_explanations.transaction}
        </div>
      ` : ''}
    </div>
  `;
  
  // Enable buttons
  approveBtn.disabled = false;
  rejectBtn.disabled = false;
  
  // Handle user decision
  approveBtn.onclick = () => makeDecision('approve');
  rejectBtn.onclick = () => makeDecision('reject');
}

function displayError(error: any, modal: HTMLElement) {
  const status = modal.querySelector('#web3-antivirus-status-text') as HTMLElement;
  const loadingDiv = modal.querySelector('.web3-antivirus-loading') as HTMLElement;
  const approveBtn = modal.querySelector('#web3-antivirus-approve') as HTMLButtonElement;
  const rejectBtn = modal.querySelector('#web3-antivirus-reject') as HTMLButtonElement;
  
  loadingDiv.style.display = 'none';
  status.innerHTML = `
    <div style="color: #ef4444;">
      ❌ Analysis failed: ${error.message}
    </div>
    <div style="color: #999; font-size: 14px; margin-top: 8px;">
      You can still approve or reject manually
    </div>
  `;
  
  // Enable buttons even on error
  approveBtn.disabled = false;
  rejectBtn.disabled = false;
  
  approveBtn.onclick = () => makeDecision('approve');
  rejectBtn.onclick = () => makeDecision('reject');
}

function makeDecision(decision: 'approve' | 'reject') {
  console.log(`[Web3 Antivirus] User decision: ${decision}`);
  
  // Inject decision into page context for interceptor to read
  const script = document.createElement('script');
  script.textContent = `window._web3AntivirusDecision = '${decision}';`;
  (document.head || document.documentElement).appendChild(script);
  script.remove();
  
  // Remove modal
  const modal = document.getElementById('web3-antivirus-modal');
  if (modal) {
    modal.remove();
  }
}

