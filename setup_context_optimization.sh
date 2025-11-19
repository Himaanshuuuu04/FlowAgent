#!/bin/bash

echo "=================================================="
echo "Context Optimization Setup"
echo "=================================================="
echo ""

cd "$(dirname "$0")/himanshu"

echo "📦 Installing required dependencies..."
echo ""

# Install tiktoken for token counting
pip install tiktoken

echo ""
echo "=================================================="
echo "✅ Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Review configuration in himanshu/server.py (lines 20-40)"
echo "2. Start the server: python server.py"
echo "3. Test with complex pages (Gmail, Twitter, etc.)"
echo "4. Monitor logs for token compression"
echo ""
echo "Configuration defaults:"
echo "  - MAX_HISTORY_MESSAGES = 10"
echo "  - MAX_DOM_ELEMENTS = 50"
echo "  - MAX_DOM_DEPTH = 3"
echo "  - MAX_TEXT_LENGTH = 100"
echo ""
echo "Expected savings: ~79% token reduction"
echo ""
echo "See CONTEXT_FIX_SUMMARY.md for complete guide"
echo "=================================================="
