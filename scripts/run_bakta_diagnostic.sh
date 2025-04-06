#!/bin/bash
# Run Bakta diagnostic tests to identify and fix Docker integration issues

set -e  # Exit on error

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Bakta Integration Diagnostic Tool ===${NC}"
echo "This script will run diagnostic tests to identify and fix Bakta integration issues."

# Step 1: Check if running in Docker
echo -e "\n${YELLOW}Checking if running in Docker environment...${NC}"
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    echo -e "${GREEN}✓ Running in Docker environment${NC}"
    DOCKER_ENV=true
else
    echo -e "${YELLOW}⚠ Not running in Docker environment - some tests may be skipped${NC}"
    DOCKER_ENV=false
fi

# Step 2: Check environment variables
echo -e "\n${YELLOW}Checking environment variables...${NC}"
env | grep -E "BAKTA_|PG_|AMR_" | sort

# Step 3: Check if Bakta modules are importable
echo -e "\n${YELLOW}Checking if Bakta modules are importable...${NC}"
python3 -c "
import sys
try:
    import amr_predictor.bakta
    print('\033[0;32m✓ Bakta module is importable\033[0m')
    print(f'  Module path: {amr_predictor.bakta.__file__}')
except ImportError as e:
    print(f'\033[0;31m✗ Bakta module import error: {e}\033[0m')
    sys.exit(1)
" || echo -e "${RED}✗ Failed to import Bakta module${NC}"

# Step 4: Run the diagnostic script
echo -e "\n${YELLOW}Running Bakta diagnostic script...${NC}"
echo "Results will be saved to bakta_diagnostic_results.log"
python3 /Users/alakob/projects/gast-app-streamlit/scripts/bakta_diagnostic.py | tee bakta_diagnostic_results.log

# Step 5: Run the Docker fix script separately
echo -e "\n${YELLOW}Testing Bakta Docker fix module...${NC}"
python3 -c "
try:
    from streamlit.bakta_docker_fix import BaktaDockerFix, FIXES_APPLIED
    print(f'\033[0;32m✓ Docker fixes applied: {FIXES_APPLIED}\033[0m')
except ImportError as e:
    print(f'\033[0;31m✗ Failed to load Docker fix module: {e}\033[0m')
"

# Step 6: Test the unified adapter
echo -e "\n${YELLOW}Testing Bakta unified adapter...${NC}"
python3 -c "
try:
    from amr_predictor.bakta.unified_adapter import get_adapter, run_async
    print('\033[0;32m✓ Unified adapter module loaded successfully\033[0m')
    # Create adapter instance
    adapter = get_adapter()
    print('\033[0;32m✓ Adapter instance created successfully\033[0m')
except ImportError as e:
    print(f'\033[0;31m✗ Failed to load unified adapter: {e}\033[0m')
except Exception as e:
    print(f'\033[0;31m✗ Error creating adapter instance: {e}\033[0m')
"

# Step 7: Compare standalone script vs module approach
echo -e "\n${YELLOW}Comparing standalone script with module implementation...${NC}"
echo "Checking for key differences in API handling"

# Find authentication approach differences
echo -e "${YELLOW}Authentication differences:${NC}"
grep -n "api_key\|API_KEY\|token\|TOKEN" /Users/alakob/projects/gast-app-streamlit/scripts/submit_bakta.py 2>/dev/null || echo "No authentication references found in standalone script"

# Find async vs sync differences
echo -e "\n${YELLOW}Async/sync differences:${NC}"
grep -n "async\|await" /Users/alakob/projects/gast-app-streamlit/scripts/submit_bakta.py 2>/dev/null || echo "No async references found in standalone script"

# Find URL differences
echo -e "\n${YELLOW}API URL differences:${NC}"
grep -n "BASE_URL\|bakta.computational.bio" /Users/alakob/projects/gast-app-streamlit/scripts/submit_bakta.py 2>/dev/null || echo "No URL references found in standalone script"

# Step 8: Verify if our patches are correctly installed
echo -e "\n${YELLOW}Verifying if integration patches are correctly installed...${NC}"
python3 -c "
try:
    import streamlit.bakta_integration_patch
    print('\033[0;32m✓ Bakta integration patch loaded successfully\033[0m')
except ImportError as e:
    print(f'\033[0;31m✗ Failed to load integration patch: {e}\033[0m')
"

echo -e "\n${GREEN}=== Diagnostic Complete ===${NC}"
echo "To apply all fixes, make sure to add the import statement for bakta_integration_patch at the beginning of your Streamlit app."
echo "Check bakta_diagnostic_results.log for detailed results."
