# Project Reorganization and Release Preparation Plan

**Date:** 2025-06-01
**Time:** 05:07:14

This document outlines the architectural plan for reorganizing project documentation, creating a comprehensive release checklist, and generating visual representations of the documentation structure.

## Phase 1: Planning & Design

### 1. Comprehensive Release Checklist (`RELEASE_CHECKLIST_YYYYMMDD_HHMMSS.md`)
    *   **Location**: A new directory `checklists/` will be created in the project root.
    *   **Content Structure**: The checklist will be detailed enough for a less sophisticated AI model to follow. It will be divided into:
        *   **A. Pre-Release Activities**:
            *   A.1. Code Freeze & Branching:
                *   Create a release branch (e.g., `release/vX.Y.Z`).
                *   Ensure no new features are merged into this branch. Only bug fixes.
            *   A.2. Final Testing:
                *   Unit Tests: Ensure all pass. Command: `python -m unittest discover -s tests` (adjust if needed).
                *   Integration Tests: Verify component interactions.
                *   User Acceptance Testing (UAT): If applicable, conduct UAT.
                *   Performance Tests: Check for regressions.
                *   Security Scans: Run vulnerability checks (e.g., Bandit for Python).
            *   A.3. Documentation Finalization:
                *   Update `docs/CHANGELOG.md` with all changes for the new version.
                *   Update `README.md` (root) with new features/instructions.
                *   Update `docs/USER_GUIDE.md`, `docs/TECHNICAL_DESIGN.md`, etc.
                *   Verify all internal links in documentation, especially after moving files to `docs/`.
            *   A.4. Version Bumping:
                *   Update version number in `setup.py` (e.g., from `0.3.0` to `0.4.0` or `1.0.0`).
                *   Update version in `docs/CHANGELOG.md` (header for the new version).
                *   Commit version changes: `git commit -am "Bump version to vX.Y.Z"`.
            *   A.5. Build & Packaging:
                *   Clean previous build artifacts: `rm -rf build dist *.egg-info`.
                *   Build source distribution: `python setup.py sdist`.
                *   Build wheel: `python setup.py bdist_wheel`.
                *   Build Debian package (if applicable, using `debuild` or similar in `debian/` dir).
                *   Build Generic Linux package (e.g., `tar -czvf WowUSB-DS9-vX.Y.Z.tar.gz WowUSB/ ...`).
                *   Test installation of each package type on clean environments/VMs.
        *   **B. Release Activities**:
            *   B.1. Tagging: Create a Git tag: `git tag -a vX.Y.Z -m "Version X.Y.Z"`. Push tag: `git push origin vX.Y.Z`.
            *   B.2. Deployment:
                *   Upload to PyPI: `twine upload dist/*`.
                *   Publish Debian packages to repository.
                *   Make generic Linux package available for download (e.g., upload to GitHub Releases).
            *   B.3. Release Notes: Publish `docs/RELEASE_NOTES.md` (or a summary) on GitHub Releases.
        *   **C. Post-Release Activities**:
            *   C.1. Announce Release: Notify users/community (e.g., mailing list, project website).
            *   C.2. Merge Release Branch: Merge the release branch back into `main`/`develop`: `git checkout main && git merge release/vX.Y.Z && git push`.
            *   C.3. Monitor: Watch for any immediate issues or bug reports.
            *   C.4. Housekeeping:
                *   Update `docs/ROADMAP.md` reflecting the release.
                *   Archive old checklist, create a new one for the next cycle.
    *   **Hints for a "Weak Local Model"**: Each item will include specific commands or file paths where possible, and clear, unambiguous language.

### 2. Documentation Reorganization
    *   **Action**: Move existing Markdown documentation files from the project root into a new `docs/` subdirectory.
    *   **Files to Move**:
        *   `ARCHITECTURE.md`
        *   `CHANGELOG.md`
        *   `CHECKLIST-BALANCED.md`
        *   `CHECKLIST.md`
        *   `CONTRIBUTING.md`
        *   `F2FS_BTRFS_TEST_PLAN.md`
        *   `F2FS_LINUX_SPEC.md`
        *   `IMPLEMENTATION_SUMMARY.md`
        *   `Initial-Planning-exfat-ntfs-addition-cline_task_mar-3-2025_1-32-04-pm.md`
        *   `MULTIBOOT_DESIGN.md`
        *   `PRODUCTION_BUILD.md`
        *   `README-ENHANCED.md`
        *   `RELEASE_NOTES.md`
        *   `ROADMAP-BALANCED.md`
        *   `ROADMAP.md`
        *   `TECHNICAL_DESIGN.md`
        *   `TROUBLESHOOTING.md`
        *   `UI_FLOW_ASSESSMENT.md`
        *   `USER_GUIDE.md`
        *   `WINDOWS11_TO_GO_SPEC.md`
    *   **Note**: `README.md` will remain in the root. `COPYING` and `.gitignore` also remain in root.

### 3. Visual/UML Representation of Documentation (`docs/DOCUMENTATION_MAP.md`)
    *   **Format**: Mermaid.js graph diagram.
    *   **Content**: A map showing categories and individual documentation files.
    *   **Mermaid Diagram**:
        ```mermaid
        graph TD
            A[WowUSB Documentation Root: /docs] --> B(Design Documents)
            A --> C(User Information & Guides)
            A --> D(Development & Contribution)
            A --> E(Release, Planning & Checklists)
            A --> F(Testing, Specifications & Summaries)

            B --> B1[ARCHITECTURE.md]
            B --> B2[TECHNICAL_DESIGN.md]
            B --> B3[MULTIBOOT_DESIGN.md]
            B --> B4[UI_FLOW_ASSESSMENT.md]

            C --> C1[USER_GUIDE.md]
            C --> C2[TROUBLESHOOTING.md]
            C --> C3["README.md (in project root)"]
            C --> C4[README-ENHANCED.md]

            D --> D1[CONTRIBUTING.md]
            D --> D2[F2FS_LINUX_SPEC.md]
            D --> D3[WINDOWS11_TO_GO_SPEC.md]

            E --> E1[CHANGELOG.md]
            E --> E2[RELEASE_NOTES.md]
            E --> E3[ROADMAP.md]
            E --> E3_balanced[ROADMAP-BALANCED.md]
            E --> E4[CHECKLIST.md (old, to be archived or reviewed)]
            E --> E4_balanced[CHECKLIST-BALANCED.md (old, to be archived or reviewed)]
            E --> E5[PRODUCTION_BUILD.md]
            E --> E6["Initial-Planning-exfat-ntfs-addition-....md"]

            F --> F1[F2FS_BTRFS_TEST_PLAN.md]
            F --> F2[IMPLEMENTATION_SUMMARY.md]

            %% New Checklist Location
            A --> G(Checklists Directory @ /checklists)
            G --> G1["RELEASE_CHECKLIST_YYYYMMDD_HHMMSS.md (New)"]
        ```
    *   This diagram will be placed in the new `docs/DOCUMENTATION_MAP.md` file.

### 4. Knowledge Graph Updates
    *   **Neo4j**:
        *   Create nodes for: `ProjectRoot`, `ChecklistsDir`, `DocsDir`, `DocumentationMapFile`, `NewReleaseChecklistFile`.
        *   Create nodes for each moved documentation file with attributes for their new path (`docs/filename.md`) and original path (`filename.md`).
        *   Establish relationships: `CONTAINS` (e.g., `ProjectRoot` CONTAINS `DocsDir`), `LOCATED_IN` (e.g., `ARCHITECTURE.md` LOCATED_IN `DocsDir`), `DESCRIBES_STRUCTURE_OF` (`DocumentationMapFile` DESCRIBES_STRUCTURE_OF `DocsDir`).
    *   **Qdrant**:
        *   Embed: "Architectural plan for WowUSB project reorganization and release v0.4.0 (or next version) preparation, including documentation move to /docs, new release checklist in /checklists, and documentation map."
        *   Embed: Summary of the new release checklist structure.
        *   Embed: The Mermaid diagram content from `docs/DOCUMENTATION_MAP.md`.

## Phase 2: Tooling & Execution (for Coder Mode)
*   Use `mcp3_create_directory` to create `checklists/` and `docs/`.
*   Use `mcp3_write_file` to create the new timestamped checklist in `checklists/` and the `DOCUMENTATION_MAP.md` in `docs/`.
*   Use `mcp3_list_directory` to confirm files in root, then `mcp3_move_file` for each documentation file to `docs/`.
*   Use `mcp6_create_entities`, `mcp6_create_relations` for Neo4j.
*   Use `mcp8_qdrant-store` for Qdrant.
