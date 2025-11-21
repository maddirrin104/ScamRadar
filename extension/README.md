# Web3 Antivirus Extension

Real-time scam protection for Web3 transactions. Intercepts MetaMask transactions before signing and provides risk analysis using ML models.

## Features

- 🛡️ **Real-time Transaction Interception**: Automatically detects MetaMask transactions before signing
- 📊 **Risk Analysis**: Account-level and transaction-level risk scoring
- 🤖 **AI Explanations**: LLM-powered explanations of detected risks
- 🎨 **Yellow/White Theme**: Clean, modern dark theme with yellow accents
- ✅ **Transaction Control**: Accept or reject transactions based on risk assessment

## Installation

1. Install dependencies:
```bash
npm install
```

2. Build extension:
```bash
npm run build
```

3. Load extension in Chrome:
   - Open Chrome → Extensions (chrome://extensions/)
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `.output/chrome-mv3` directory

## Development

```bash
# Development mode with hot reload
npm run dev

# Build for production
npm run build

# Package extension
npm run zip
```

## Configuration

Update API URL in `popup/main.ts`:
```typescript
const API_BASE_URL = 'http://localhost:8000'; // Backend API URL
```

## Project Structure

```
extension/
├── background/          # Background service worker
├── content/            # Content scripts for intercepting transactions
├── popup/              # Extension popup UI
│   ├── index.html     # HTML structure
│   ├── style.css      # Yellow/white theme styles
│   └── main.ts        # Popup logic
├── icons/              # Extension icons
└── wxt.config.ts       # WXT configuration
```

## Usage

### Default View
- **Analyze Account**: Enter wallet address to check account risk
- **Analyze Transaction**: Enter transaction hash to analyze

### Transaction Interception
When user signs a transaction in MetaMask:
1. Extension intercepts the transaction
2. Popup automatically opens with risk analysis
3. User sees:
   - From/To addresses
   - ETH amount being sent
   - NFT information (if applicable)
   - Account risk score
   - Transaction risk score
   - Risk details with explanations
4. User can:
   - **Reject**: Cancel transaction
   - **Continue**: Approve transaction in MetaMask
   - **View on Etherscan**: Open address in Etherscan

## Flow

```
1. User initiates transaction in MetaMask
   ↓
2. Content script intercepts window.ethereum.request()
   ↓
3. Transaction data sent to background script
   ↓
4. Background script stores data and opens popup
   ↓
5. Popup calls backend API:
   ├─> /detect (for account analysis)
   └─> /detect/transaction (if account is new)
   ↓
6. Backend returns risk scores + explanations
   ↓
7. Popup displays risk analysis
   ↓
8. User decides:
   ├─> Reject → Transaction canceled
   └─> Continue → Transaction proceeds in MetaMask
```

## Notes

- Extension requires access to all websites to intercept MetaMask
- Backend must be running on configured API URL
- For new accounts (no transaction history), only transaction-level detection is available
- UI dynamically adapts based on available data

