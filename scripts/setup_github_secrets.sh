#!/bin/bash
# Setup GitHub Secrets for ConsentChain CI/CD
# Run this script to configure all required secrets

echo "=== ConsentChain GitHub Secrets Setup ==="
echo ""
echo "This script will set up the following secrets:"
echo "  - JWT_SECRET"
echo "  - API_SECRET_KEY"  
echo "  - ALGORAND_MNEMONIC_TESTNET"
echo ""

# Generate random secrets
JWT_SECRET=$(openssl rand -hex 32)
API_SECRET=$(openssl rand -hex 32)

echo "Generated JWT_SECRET: $JWT_SECRET"
echo "Generated API_SECRET_KEY: $API_SECRET"
echo ""

# Set secrets
echo "Setting GitHub secrets..."

gh secret set JWT_SECRET --body "$JWT_SECRET"
gh secret set API_SECRET_KEY --body "$API_SECRET"

echo ""
echo "=== Secrets that need manual setup ==="
echo ""
echo "1. ALGORAND_MNEMONIC_TESTNET"
echo "   - Generate a new Algorand account"
echo "   - Fund it with testnet ALGO: https://bank.testnet.algorand.network/"
echo "   - Set the secret:"
echo "     gh secret set ALGORAND_MNEMONIC_TESTNET --body 'your 25-word mnemonic'"
echo ""
echo "2. ALGORAND_MNEMONIC_MAINNET (for production)"
echo "   - Use a securely generated mainnet account"
echo "   - Set the secret:"
echo "     gh secret set ALGORAND_MNEMONIC_MAINNET --body 'your 25-word mnemonic'"
echo ""
echo "3. PYPI_API_TOKEN (for publishing Python SDK)"
echo "   - Create at: https://pypi.org/manage/account/token/"
echo "   - Set the secret:"
echo "     gh secret set PYPI_API_TOKEN --body 'pypi-token'"
echo ""
echo "4. NPM_TOKEN (for publishing TypeScript SDK)"  
echo "   - Create at: https://www.npmjs.com/settings/tokens"
echo "   - Set the secret:"
echo "     gh secret set NPM_TOKEN --body 'npm-token'"
echo ""
echo "5. SNYK_TOKEN (for security scanning)"
echo "   - Create at: https://app.snyk.io/account"
echo "   - Set the secret:"
echo "     gh secret set SNYK_TOKEN --body 'snyk-token'"
echo ""
echo "=== Done ==="
