# Quick Start Guide

## Backend Setup

1. Start backend:
```bash
cd backend
python run.py
```

Backend sẽ chạy trên `http://localhost:8000`

## Extension Setup

1. Install dependencies:
```bash
cd extension
npm install
```

2. Build extension:
```bash
npm run build
```

3. Load extension in Chrome:
   - Open `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select folder: `extension/.output/chrome-mv3`

## Testing Flow

### Test 1: Account Analysis (Default View)

1. Click extension icon
2. Enter an Ethereum address in "Analyze Account" section
3. Click "Analyze"
4. View account risk score and explanation

### Test 2: Transaction Interception

1. Open a dApp that uses MetaMask (e.g., OpenSea)
2. Initiate a transaction (e.g., transfer NFT)
3. Extension popup should automatically open
4. View transaction details and risk analysis
5. Click "Reject" or "Continue"

### Test 3: New Account (Transaction-Only)

1. Use a new account with no transaction history
2. Initiate transaction in MetaMask
3. Extension should:
   - Show "N/A" for Account Risk
   - Show Transaction Risk score
   - Only display transaction-level explanations

## API Endpoints

### POST /detect
Analyze account with full history.

### POST /detect/transaction
Analyze single transaction (for new accounts).

## Troubleshooting

- **Extension not intercepting**: Check content script permissions
- **Backend not responding**: Verify backend is running on port 8000
- **No risk scores**: Check backend logs for errors
- **UI not showing**: Check browser console for errors

