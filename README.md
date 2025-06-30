
# Consolidated CI/CD Workflow

This directory contains the new, consolidated CI/CD workflow for all projects.

## How to Use

To use this consolidated workflow in your project, you need to do two things:

1.  **Create Repository Variables:**

    In your project's GitHub repository settings, go to `Settings > Secrets and variables > Actions` and create the following variables:

    *   `PACKAGE_MANAGER`: The package manager used by your project (`pixi` or `hatch`).
    *   `PYTHON_VERSIONS`: A JSON array of Python versions to test against (e.g., `["3.10", "3.11"]`).
    *   `OS_MATRIX`: A JSON array of operating systems to test against (e.g., `["ubuntu-latest", "macos-latest"]`).
    *   `ENABLE_PERFORMANCE`: `true` or `false` to enable/disable performance benchmarks.
    *   `ENABLE_SECURITY`: `true` or `false` to enable/disable comprehensive security scans.
    *   `ENABLE_RELEASE`: `true` or `false` to enable/disable automated releases.

2.  **Create a `ci.yml` file in your project's `.github/workflows` directory:**

    This file should call the main orchestrator workflow. Here is a template:

    ```yaml
    name: CI/CD

    on:
      push:
        branches: [main, master, development]
      pull_request:
        branches: [main, master, development]
      workflow_dispatch:

    jobs:
      call-main-workflow:
        uses: your-org/your-repo/.github/workflows/main-ci-cd.yml@main
        secrets: inherit
    ```

    Replace `your-org/your-repo` with the path to the repository containing this consolidated workflow.

# Recommended Practices

In addition to the automated workflows provided here, we highly recommend that consuming projects adopt the following practices for a state-of-the-art developer experience:

### Dev Containers

Create a `.devcontainer/devcontainer.json` file in the root of your repository. This will define a consistent, pre-configured development environment that can be used with GitHub Codespaces or VS Code with Docker. This practice completely eliminates the "it works on my machine" problem and allows new contributors to get a perfect, running environment in minutes.
