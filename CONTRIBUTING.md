# Contributing to ConsentChain

Thank you for your interest in contributing to ConsentChain! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of-conduct/). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Poetry (Python package manager)
- Algorand Testnet Account

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/consentchain.git
cd consentchain

# Install Python dependencies
poetry install

# Install frontend dependencies
cd dashboard-v2 && npm install && cd ..

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# Required: JWT_SECRET, DATABASE_URL, MASTER_MNEMONIC

# Run database migrations
poetry run alembic upgrade head

# Start services
docker-compose up -d postgres redis

# Run the API
poetry run uvicorn api.main:app --reload --port 8001

# Run the dashboard (in another terminal)
cd dashboard-v2 && npm run dev
```

### Run Tests

```bash
# Run all tests
poetry run pytest tests/

# Run with coverage
poetry run pytest tests/ --cov=api --cov=core --cov=sdk

# Run specific test file
poetry run pytest tests/test_api.py -v
```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/your-org/consentchain/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with the `enhancement` label
3. Describe the feature and its use case
4. Explain how it fits with DPDP Act compliance

### Code Contributions

1. Pick an issue to work on
2. Comment on the issue to claim it
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes following coding standards
5. Write/update tests
6. Update documentation
7. Submit a pull request

## Coding Standards

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Use type hints for all function parameters and returns
- Write docstrings for all public functions and classes
- Maximum line length: 88 characters (Black default)
- Use async/await for I/O operations

```python
# Good example
async def create_consent(
    principal_id: UUID,
    fiduciary_id: UUID,
    purpose: str,
) -> ConsentRecord:
    """
    Create a new consent record.

    Args:
        principal_id: UUID of the data principal
        fiduciary_id: UUID of the data fiduciary
        purpose: Purpose of data processing

    Returns:
        The created consent record

    Raises:
        ValueError: If purpose is invalid
    """
    ...
```

### TypeScript

- Follow the [Airbnb Style Guide](https://github.com/airbnb/javascript)
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use proper component typing

```typescript
// Good example
interface ConsentCardProps {
  consent: Consent;
  onRevoke: (id: string) => Promise<void>;
}

export const ConsentCard: React.FC<ConsentCardProps> = ({ consent, onRevoke }) => {
  const [loading, setLoading] = useState(false);

  const handleRevoke = async () => {
    setLoading(true);
    await onRevoke(consent.id);
    setLoading(false);
  };

  return <Card>{/* ... */}</Card>;
};
```

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(consent): add batch consent creation endpoint

Add support for creating multiple consents in a single API call.
This improves performance for bulk operations.

Closes #123
```

```
fix(auth): correct JWT token validation

The token expiration check was comparing timestamps incorrectly.
Now properly validates token expiry.

Fixes #456
```

## Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following coding standards
3. **Write/update tests** for your changes
4. **Update documentation** if needed
5. **Run the test suite** and ensure all tests pass
6. **Submit a pull request** with:
   - Clear title and description
   - Reference to related issue(s)
   - Screenshots for UI changes
   - Testing instructions

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] CHANGELOG.md updated (for significant changes)

## Testing

### Test Structure

```
tests/
├── conftest.py          # Fixtures and test configuration
├── test_api.py          # API endpoint tests
├── test_crypto.py       # Cryptographic utility tests
├── test_sdk.py          # SDK client tests
├── test_blockchain.py   # Blockchain integration tests
├── test_features.py     # Feature module tests
└── test_architecture.py # Architecture pattern tests
```

### Writing Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_consent(client: AsyncClient, auth_headers: dict):
    """Test consent creation endpoint."""
    response = await client.post(
        "/api/v1/consent/create",
        json={
            "principal_wallet": "test-wallet",
            "purpose": "MARKETING",
            "data_types": ["email"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "consent_id" in data["data"]
```

## Documentation

### Code Documentation

- Use docstrings for all public APIs
- Include type hints
- Provide usage examples for complex functions

### API Documentation

- Document all endpoints in OpenAPI format
- Include request/response examples
- Document error codes and their meanings

### Architecture Documentation

- Update `docs/ARCHITECTURE.md` for significant changes
- Add diagrams for complex flows
- Document design decisions

## Questions?

- Open a [Discussion](https://github.com/your-org/consentchain/discussions)
- Join our [Discord](https://discord.gg/consentchain)
- Email: support@consentchain.io

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to ConsentChain! 🎉
