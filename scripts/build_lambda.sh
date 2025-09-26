#!/bin/bash

# Lambda Package Builder Script
# This script builds AWS Lambda packages using Docker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE="public.ecr.aws/lambda/python:3.13"
SOURCE_DIR="../lambdas_source_code"
OUTPUT_DIR="../terraform/lambda_packages"
TEMP_DIR="/tmp/lambda_build_$$"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to clean up temporary files
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        print_info "Cleaned up temporary directory"
    fi
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to get available lambdas
get_available_lambdas() {
    local lambdas=()

    if [ ! -d "$SOURCE_DIR" ]; then
        print_error "Source directory $SOURCE_DIR not found"
        exit 1
    fi

    # Find directories that contain requirements.txt
    while IFS= read -r -d '' dir; do
        lambda_name=$(basename "$dir")
        if [ "$lambda_name" != "__pycache__" ] && [ -f "$dir/requirements.txt" ]; then
            lambdas+=("$lambda_name")
        fi
    done < <(find "$SOURCE_DIR" -maxdepth 1 -type d -print0)

    echo "${lambdas[@]}"
}

# Function to display menu and get user selection
select_lambda() {
    local lambdas=($1)

    if [ ${#lambdas[@]} -eq 0 ]; then
        print_error "No Lambda functions found with requirements.txt"
        exit 1
    fi

    # Display menu to stderr so it doesn't interfere with return value
    echo >&2
    print_info "Available Lambda functions:" >&2
    echo >&2

    # Add "All" option
    echo "  0) Build all Lambda functions" >&2

    # List individual lambdas
    for i in "${!lambdas[@]}"; do
        echo "  $((i+1))) ${lambdas[$i]}" >&2
    done

    echo >&2
    read -p "Select Lambda to build (0-${#lambdas[@]}): " selection >&2

    # Validate selection
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 0 ] || [ "$selection" -gt ${#lambdas[@]} ]; then
        print_error "Invalid selection"
        exit 1
    fi

    # Return only the selection number to stdout
    echo "$selection"
}

# Function to build a single lambda
build_lambda() {
    local lambda_name=$1
    local source_path="$SOURCE_DIR/$lambda_name"

    # Convert to absolute path to avoid issues with directory changes
    local output_file
    output_file=$(cd "$(dirname "$OUTPUT_DIR")" && pwd)/$(basename "$OUTPUT_DIR")/${lambda_name}.zip

    print_info "Building Lambda package: $lambda_name"

    # Check if source directory exists
    if [ ! -d "$source_path" ]; then
        print_error "Source directory not found: $source_path"
        return 1
    fi

    # Check if requirements.txt exists
    if [ ! -f "$source_path/requirements.txt" ]; then
        print_error "requirements.txt not found in $source_path"
        return 1
    fi

    # Create temporary build directory
    local build_dir="$TEMP_DIR/$lambda_name"
    mkdir -p "$build_dir"

    # Copy source code to build directory
    cp -r "$source_path"/* "$build_dir/"

    # Install dependencies using Docker
    print_info "Installing dependencies using Docker..."
    docker run --rm \
        --entrypoint="" \
        -v "$build_dir":/var/task \
        -w /var/task \
        "$DOCKER_IMAGE" \
        /bin/bash -c "
            if [ -f requirements.txt ]; then
                pip install --no-cache-dir --upgrade --root-user-action=ignore -r requirements.txt -t . 2>&1 | grep -v 'WARNING:\|notice\]'
            fi
        "

    if [ $? -ne 0 ]; then
        print_error "Failed to install dependencies for $lambda_name"
        return 1
    fi

    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"

    # Create zip package
    print_info "Creating ZIP package..."
    cd "$build_dir"

    # Remove any existing zip file
    rm -f "$output_file"

    # Ensure output directory exists
    mkdir -p "$(dirname "$output_file")"

    # Create the zip file (exclude unnecessary files)
    zip -q -r "$output_file" . \
        -x "*.pyc" \
        -x "__pycache__/*" \
        -x "*.egg-info/*" \
        -x ".git/*" \
        -x "tests/*" \
        -x "*.md" \
        -x ".DS_Store"

    # Store zip result before changing directory
    zip_result=$?

    # Change back to original directory
    cd - > /dev/null

    if [ $zip_result -eq 0 ] && [ -f "$output_file" ]; then
        local size=$(du -h "$output_file" | cut -f1)
        print_success "Successfully created $lambda_name package ($size): $output_file"
        return 0
    else
        print_error "Failed to create ZIP package for $lambda_name"
        return 1
    fi
}

# Function to build all lambdas
build_all_lambdas() {
    local lambdas=($1)
    local success_count=0
    local total_count=${#lambdas[@]}

    print_info "Building all Lambda packages..."
    echo

    for lambda_name in "${lambdas[@]}"; do
        if build_lambda "$lambda_name"; then
            ((success_count++))
        fi
        echo  # Add spacing between builds
    done

    echo
    print_info "Build Summary:"
    print_success "$success_count/$total_count Lambda packages built successfully"

    if [ $success_count -lt $total_count ]; then
        print_warning "$((total_count - success_count)) Lambda packages failed to build"
        exit 1
    fi
}

# Main execution
main() {
    print_info "AWS Lambda Package Builder"
    echo "=============================="

    # Check prerequisites
    check_docker

    # Get available lambdas
    available_lambdas=$(get_available_lambdas)
    lambdas_array=($available_lambdas)

    if [ ${#lambdas_array[@]} -eq 0 ]; then
        print_error "No Lambda functions found"
        exit 1
    fi

    # Get user selection
    selection=$(select_lambda "$available_lambdas")

    echo
    print_info "Starting build process..."

    # Build based on selection
    if [ "$selection" -eq 0 ]; then
        # Build all lambdas
        build_all_lambdas "$available_lambdas"
    else
        # Build selected lambda
        lambda_name=${lambdas_array[$((selection-1))]}
        build_lambda "$lambda_name"
    fi

    print_success "Build process completed!"
}

# Run main function
main "$@"