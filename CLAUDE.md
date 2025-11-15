# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YNAmazon is a Python CLI tool that annotates YNAB (You Need A Budget) transactions with Amazon order information. It matches Amazon purchases to YNAB transactions by amount and automatically updates transaction memos with item details and order links.

**Key workflow:**
1. Retrieves YNAB transactions marked with a specific payee (default: "Amazon - Needs Memo")
2. Fetches Amazon order history and transaction data using the `amazon-orders` library
3. Matches transactions by amount
4. Generates detailed memos with item lists and order links
5. Updates YNAB transactions with the processed memo and changes payee to indicate completion

## Development Commands

### Environment Setup
```bash
# Install dependencies (basic)
uv sync

# Install with AI summarization features
uv sync --extra ai

# Install development dependencies
uv sync --group dev

# Install test dependencies
uv sync --group test
```

### Testing
```bash
# IMPORTANT: Always run tests with uv run to ensure proper environment
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/ynab/test_memo_truncation.py

# Run with coverage
uv run pytest --cov=ynamazon

# Run with verbose output
uv run pytest -v
```

### Code Quality
```bash
# Run linter
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy src/ynamazon

# Check dependencies
deptry .
```

### CLI Usage
```bash
# Main command to match and update transactions
yna ynamazon

# Print YNAB transactions
yna print-ynab

# Print Amazon transactions
yna print-amazon [--years YEAR] [--days DAYS]

# Check Amazon orders integration status
yna utils check-amazon-orders
```

### Build Documentation
```bash
# Generate CLI documentation
./scripts/build_cli_docs.sh
```

## Architecture

### Core Components

**Settings (`settings.py`)**
- Uses `pydantic-settings` with `.env` file configuration
- Manages credentials (YNAB API key, Amazon credentials, OpenAI API key)
- **Multi-Account Support**: `get_amazon_accounts()` method dynamically loads multiple Amazon accounts
  - Checks for numbered env vars: `AMAZON_USER_1`, `AMAZON_PASSWORD_1`, `AMAZON_USER_2`, `AMAZON_PASSWORD_2`, etc.
  - Falls back to legacy single account (`AMAZON_USER`, `AMAZON_PASSWORD`) if no numbered accounts found
  - Returns list of (account_name, email, password) tuples
- Controls feature flags (`ynab_use_markdown`, `use_ai_summarization`, `suppress_partial_order_warning`)
- Validates that OpenAI API key exists when AI summarization is enabled

**Amazon Integration (`amazon_transactions.py`)**
- `AmazonConfig`: Configuration model with username, password, and account_name fields
- `AmazonTransactionRetriever`: Fetches and caches Amazon orders and transactions
  - Each instance is associated with a specific `AmazonConfig` (account)
  - Automatically tags transactions with the account name
- `AmazonTransactionWithOrderInfo`: Pydantic model linking transactions to order details
  - Includes `account_name` field to track which Amazon account the transaction came from
- Uses 2-hour cache in temp directory to avoid excessive Amazon API calls (per-account caching)
- `locate_amazon_transaction_by_amount()`: Matches YNAB amounts to Amazon transactions

**YNAB Integration (`ynab_transactions.py`)**
- `TempYnabTransaction`: Extended YNAB transaction model with `amount_decimal` property
- `Payees` and `TempYnabTransactions`: Pydantic `ListRootModel` wrappers for type safety
- `get_ynab_transactions()`: Retrieves unprocessed transactions by payee name
- `update_ynab_transaction()`: Updates memo and payee, with 500-char truncation logic

**Memo Processing (`ynab_memo.py`)**
- `process_memo()`: Main entry point - uses AI or truncation based on settings
- `generate_ai_summary()`: Calls OpenAI GPT-4o-mini to summarize item lists
- `truncate_memo()`: Fallback truncation preserving partial order warnings and URLs
- YNAB has a 500-character limit for memos - all processing respects this

**Main Workflow (`main.py`)**
- `process_transactions()`: Orchestrates the entire matching and update process
  - Accepts `list[AmazonConfig]` to support multiple Amazon accounts
  - Creates separate `AmazonTransactionRetriever` for each account
  - Merges transactions from all accounts into a single list for matching
  - Adds account identifier prefix to memos when multiple accounts are configured
- Interactive prompts for date mismatches and update confirmations
- Rich console output for user feedback (shows which account matched each transaction)

### Data Flow

1. **Fetch Phase**: Retrieve YNAB transactions (filtered by payee) and Amazon data from all configured accounts
   - For each Amazon account, create `AmazonTransactionRetriever` instance
   - Fetch orders and transactions for each account
   - Merge all transactions into single list with account metadata preserved
2. **Matching Phase**: For each YNAB transaction, find corresponding Amazon transaction by amount
3. **Memo Generation Phase**: Build memo with account identifier (if multiple accounts), item list, order link, and optional partial order warning
4. **Processing Phase**: Apply AI summarization (if enabled) or truncation (if needed)
   - Both functions preserve the account identifier prefix
5. **Update Phase**: Push updated memo and payee back to YNAB (with user confirmation)

### Important Models

**`AmazonTransactionWithOrderInfo`**
- Links an Amazon transaction to its full order details
- Inverts transaction amount (Amazon returns negative values)
- Contains: `completed_date`, `transaction_total`, `order_total`, `order_number`, `order_link`, `items`, `account_name`
- The `account_name` field identifies which Amazon account the transaction belongs to

**`ListRootModel` (`base.py`)**
- Generic base class for Pydantic lists with utility methods
- Provides `filter()`, `append()`, `empty()` class method
- Used by `Payees` and `TempYnabTransactions` for type-safe collections

### Key Design Patterns

- **Caching**: Amazon data is cached for 2 hours to minimize web scraping
- **Validation**: Pydantic models ensure data integrity throughout the pipeline
- **Error Handling**: Specific exceptions for YNAB setup errors, missing API keys, etc.
- **Optional AI**: AI summarization is an optional feature (extra dependency group)
- **Markdown Support**: Memos can use markdown links if YNAB Toolkit is installed

## Important Constraints

- **YNAB Memo Limit**: 500 characters maximum - all memo processing must respect this
- **Amazon Library**: Uses `amazon-orders` library which only supports amazon.com (not international sites)
- **Matching Logic**: Matches by transaction amount only (assumes amounts are unique enough)
- **Split Orders**: When Amazon splits an order into multiple transactions, all get the same memo with a warning
- **Python Version**: Requires Python 3.9-3.12 (incompatible with 3.13+)

## Environment Variables

Required in `.env` file:
- `YNAB_API_KEY`: YNAB personal access token
- `YNAB_BUDGET_ID`: Target budget UUID
- `YNAB_PAYEE_NAME_TO_BE_PROCESSED`: Payee name for unprocessed transactions (default: "Amazon - Needs Memo")
- `YNAB_PAYEE_NAME_PROCESSING_COMPLETED`: Payee name after processing (default: "Amazon")

**Amazon Account Configuration (choose one approach):**

*Single Account (Legacy):*
- `AMAZON_USER`: Amazon account email
- `AMAZON_PASSWORD`: Amazon account password

*Multiple Accounts (Recommended for households with multiple Amazon accounts):*
- `AMAZON_USER_1`: First Amazon account email
- `AMAZON_PASSWORD_1`: First Amazon account password
- `AMAZON_USER_2`: Second Amazon account email
- `AMAZON_PASSWORD_2`: Second Amazon account password
- *(Continue with `_3`, `_4`, etc. as needed)*

**How it works:**
- The system automatically detects numbered account variables (`AMAZON_USER_1`, `AMAZON_USER_2`, etc.)
- If numbered accounts are found, they are used; otherwise falls back to single account mode
- When multiple accounts are configured, memos include an account identifier like `[Account 1]` or `[Account 2]`
- All accounts are fetched and merged automatically when running `yna ynamazon`

Optional:
- `YNAB_USE_MARKDOWN`: Enable markdown formatting in memos (default: false)
- `USE_AI_SUMMARIZATION`: Use OpenAI to summarize long orders (default: false)
- `OPENAI_API_KEY`: Required if `USE_AI_SUMMARIZATION=true`
- `SUPPRESS_PARTIAL_ORDER_WARNING`: Hide partial order warnings (default: false)

## Testing Notes

- **Test Environment Setup**: A `tests/conftest.py` file sets up test environment variables at import time to satisfy Pydantic settings validation
- **Dependencies**: Tests require both base dependencies and AI extras (`uv sync --extra ai --group test`)
- **Running Tests**: Always use `uv run pytest` to ensure the correct virtual environment is activated
- **Test Data**: `polyfactory` and `faker` used for test data generation
- **Test Files**: Follow `test_*.py` naming convention
- **Key Test Areas**: memo truncation, transaction matching, Amazon data parsing
- **Mock Data**: Factories in `tests/factories.py`
- **Known Issues**:
  - `tests/amazon/test_transactions.py` contains 4 skipped tests for `_fetch_amazon_order_history` function which was refactored into `AmazonTransactionRetriever` class
  - These tests need to be rewritten to test the new API
