# ================================================================
# Lambda Package Debugging Commands
# ================================================================

# 1. EXTRACT AND EXAMINE THE LAMBDA ZIP PACKAGE
# ================================================================

# Navigate to where your Lambda package is stored
cd ../terraform/lambda_packages

# Extract the zip to examine contents
unzip -q cost_optimisation_mcp_adapter.zip -d /tmp/lambda_debug/
cd /tmp/lambda_debug/

# 2. CHECK PACKAGE STRUCTURE
# ================================================================

echo "=== PACKAGE STRUCTURE ==="
find . -type f -name "*.py" | head -20
echo ""

echo "=== ROOT LEVEL FILES ==="
ls -la
echo ""

echo "=== LAMBDA HANDLER CHECK ==="
if [ -f "lambda_function.py" ]; then
    echo "✅ lambda_function.py found"
    head -10 lambda_function.py
else
    echo "❌ lambda_function.py NOT found"
fi
echo ""

# 3. CHECK RPDS INSTALLATION
# ================================================================

echo "=== RPDS PACKAGE CHECK ==="
if [ -d "rpds" ]; then
    echo "✅ rpds directory found"
    ls -la rpds/
    echo ""

    # Check for the specific rpds.rpds module
    if [ -f "rpds/__init__.py" ]; then
        echo "✅ rpds/__init__.py found"
    else
        echo "❌ rpds/__init__.py NOT found"
    fi

    # Look for rpds.so or rpds.cpython files
    find rpds/ -name "*rpds*" -type f
    echo ""

else
    echo "❌ rpds directory NOT found"
fi

# 4. CHECK MCP DEPENDENCIES
# ================================================================

echo "=== MCP PACKAGE CHECK ==="
if [ -d "mcp" ]; then
    echo "✅ mcp directory found"
    ls -la mcp/
    echo ""

    # Check MCP dependencies
    if [ -f "mcp/requirements.txt" ] || [ -f "mcp/pyproject.toml" ]; then
        echo "MCP dependency files:"
        find mcp/ -name "requirements.txt" -o -name "pyproject.toml" | xargs cat 2>/dev/null
    fi
    echo ""
else
    echo "❌ mcp directory NOT found"
fi

# 5. CHECK ALL DEPENDENCIES
# ================================================================

echo "=== ALL INSTALLED PACKAGES ==="
find . -maxdepth 1 -type d -name "[a-zA-Z]*" | sort
echo ""

# 6. CHECK FOR BINARY DEPENDENCIES
# ================================================================

echo "=== BINARY FILES CHECK ==="
find . -name "*.so" -o -name "*.dylib" -o -name "*.pyd" | head -10
echo ""

# 7. CHECK ARCHITECTURE-SPECIFIC FILES
# ================================================================

echo "=== ARCHITECTURE-SPECIFIC FILES ==="
find . -name "*x86_64*" -o -name "*aarch64*" -o -name "*arm64*" -o -name "*linux*" | head -10
echo ""

# 8. DETAILED RPDS INVESTIGATION
# ================================================================

echo "=== DETAILED RPDS INVESTIGATION ==="
if [ -d "rpds" ]; then
    echo "RPDS directory contents:"
    find rpds/ -type f | head -20
    echo ""

    echo "RPDS Python files:"
    find rpds/ -name "*.py" | head -10
    echo ""

    echo "RPDS binary files:"
    find rpds/ -name "*.so" -o -name "*.pyd" | head -10
    echo ""

    # Check for wheel info
    find . -name "*rpds*.dist-info" -type d
    if [ $? -eq 0 ]; then
        echo "RPDS wheel info found:"
        find . -name "*rpds*.dist-info" -type d | xargs ls -la
    fi
fi

# 9. CHECK IMPORT PATH
# ================================================================

echo "=== PYTHON IMPORT TEST ==="
python3 -c "
import sys
sys.path.insert(0, '.')
print('Python path:', sys.path[:3])

try:
    import rpds
    print('✅ rpds import successful')
    print('rpds location:', rpds.__file__)
except ImportError as e:
    print('❌ rpds import failed:', str(e))

try:
    from rpds import rpds as rpds_rpds
    print('✅ rpds.rpds import successful')
except ImportError as e:
    print('❌ rpds.rpds import failed:', str(e))

try:
    import cost_optimisation_mcp_adapter
    print('✅ cost_optimisation_mcp_adapter import successful')
except ImportError as e:
    print('❌ cost_optimisation_mcp_adapter import failed:', str(e))
"

# 10. CHECK REQUIREMENTS.TXT
# ================================================================

echo "=== REQUIREMENTS CHECK ==="
if [ -f "requirements.txt" ]; then
    echo "Requirements.txt found:"
    cat requirements.txt
else
    echo "❌ requirements.txt not found at root level"
fi
echo ""

# 11. SIMULATE LAMBDA IMPORT
# ================================================================

echo "=== SIMULATE LAMBDA IMPORT ==="
python3 -c "
import sys
import os
sys.path.insert(0, '.')

print('Current directory:', os.getcwd())
print('Directory contents:', sorted(os.listdir('.')))

try:
    import lambda_function
    print('✅ lambda_function import successful')

    # Check if handler exists
    if hasattr(lambda_function, 'lambda_handler'):
        print('✅ lambda_handler function found')
    else:
        print('❌ lambda_handler function not found')

except ImportError as e:
    print('❌ lambda_function import failed:', str(e))
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== DEBUGGING COMPLETE ==="