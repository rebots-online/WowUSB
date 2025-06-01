# WowUSB Comprehensive Release Checklist

**Date Generated:** 2025-06-01
**Target Version:** (Specify Target Version, e.g., v0.4.0 or v1.0.0)

This checklist provides a detailed guide for executing a public release of WowUSB. It is designed to be clear enough for any team member or a less sophisticated AI model to follow.

## A. Pre-Release Activities

### A.1. Code Freeze & Branching
- **[ ] Action:** Create a dedicated release branch from the main development branch (e.g., `develop` or `main`).
  - **Hint:** `git checkout develop && git pull && git checkout -b release/vX.Y.Z` (replace `vX.Y.Z` with target version).
- **[ ] Policy:** Ensure no new features are merged into this release branch. Only critical bug fixes are permitted.
  - **Hint:** Communicate this policy to the development team.

### A.2. Final Testing
- **[ ] Unit Tests:** Execute all unit tests and ensure 100% pass rate.
  - **Hint:** Command: `python -m unittest discover -s ./tests` (or specific test runner command for the project). Verify no tests are skipped unless intentionally.
- **[ ] Integration Tests:** Run all integration tests to verify interactions between components.
  - **Hint:** Identify and run integration test suites. Document any specific setup required.
- **[ ] User Acceptance Testing (UAT):** If applicable, conduct UAT with designated testers or a subset of users.
  - **Hint:** Prepare UAT scenarios. Collect and address feedback.
- **[ ] Performance Tests:** Check for any performance regressions, especially in critical operations (e.g., ISO parsing, USB writing speed).
  - **Hint:** Use existing benchmarks or create new ones if necessary.
- **[ ] Security Scans:** Run static analysis security tools (e.g., Bandit for Python) and review outputs.
  - **Hint:** Command: `bandit -r WowUSB/`. Address any high or medium severity findings.
- **[ ] Cross-Platform Testing:** Test on all supported operating systems (Windows, various Linux distributions).
  - **Hint:** Use VMs or physical machines. Test both GUI and CLI versions.

### A.3. Documentation Finalization
- **[ ] Update `CHANGELOG.md`:** Add a new section for the upcoming release version. List all significant changes, additions, fixes, and deprecations.
  - **Hint:** File location after reorg: `docs/CHANGELOG.md`. Follow "Keep a Changelog" format.
- **[ ] Update `README.md`:** Ensure the main `README.md` (in project root) is up-to-date with new features, installation instructions, and basic usage.
- **[ ] Update User & Technical Guides:** Review and update `docs/USER_GUIDE.md`, `docs/TECHNICAL_DESIGN.md`, `docs/ARCHITECTURE.md`, etc., to reflect any changes.
- **[ ] Verify Internal Links:** Check all Markdown files for broken internal links, especially after moving files to the `docs/` directory.
  - **Hint:** Use a link checker tool or manually verify.
- **[ ] Update `RELEASE_NOTES.md`:** Prepare detailed release notes for the new version.
  - **Hint:** File location after reorg: `docs/RELEASE_NOTES.md`.

### A.4. Version Bumping
- **[ ] Update Version in `setup.py`:** Modify the `version` string in `setup.py` to the new target version.
  - **Hint:** e.g., `version='0.4.0'`.
- **[ ] Update Version in `CHANGELOG.md`:** Ensure the version header in `docs/CHANGELOG.md` matches the target version.
- **[ ] Commit Version Changes:** Commit the version updates to the release branch.
  - **Hint:** `git add setup.py docs/CHANGELOG.md && git commit -m "Bump version to vX.Y.Z"`.

### A.5. Build & Packaging
- **[ ] Clean Previous Build Artifacts:** Remove any old build directories or files.
  - **Hint:** `rm -rf build/ dist/ *.egg-info/`.
- **[ ] Build Source Distribution:** Create the source distribution package (sdist).
  - **Hint:** `python setup.py sdist`.
- **[ ] Build Wheel:** Create the binary wheel package.
  - **Hint:** `python setup.py bdist_wheel`.
- **[ ] Build Debian Package:** (If applicable) Navigate to the `debian/` directory and build the `.deb` package.
  - **Hint:** Typically involves `debuild -us -uc` or similar. Ensure all build dependencies are met.
- **[ ] Build Generic Linux Package:** Create a `tar.gz` archive containing all necessary files for manual installation.
  - **Hint:** `tar -czvf WowUSB-DS9-vX.Y.Z.tar.gz WowUSB/ scripts/ setup.py README.md COPYING ...` (include all relevant files).
- **[ ] Test Package Installation:** Install each generated package type on a clean environment (VMs are ideal) to ensure they install correctly and the application runs.
  - **Hint:** For sdist/wheel: `pip install WowUSB-DS9-vX.Y.Z.whl`. For Debian: `sudo dpkg -i wowusb-ds9_X.Y.Z_all.deb && sudo apt-get -f install`. For tar.gz: follow manual install steps.

## B. Release Activities

### B.1. Tagging in Version Control
- **[ ] Create Git Tag:** Create an annotated Git tag for the release version on the release branch.
  - **Hint:** `git tag -a vX.Y.Z -m "Release version X.Y.Z"`.
- **[ ] Push Git Tag:** Push the new tag to the remote repository.
  - **Hint:** `git push origin vX.Y.Z`.

### B.2. Deployment & Distribution
- **[ ] Upload to PyPI:** Upload the source distribution and wheel to the Python Package Index (PyPI).
  - **Hint:** `twine upload dist/*`. Ensure you have PyPI credentials configured.
- **[ ] Publish Debian Packages:** Upload the `.deb` package to the project's Debian repository or PPA.
- **[ ] Publish Generic Linux Package:** Upload the `tar.gz` archive to a publicly accessible location (e.g., GitHub Releases, project website).
- **[ ] Update GitHub Releases:** Create a new release on GitHub. Upload binaries/packages there. Use the content from `docs/RELEASE_NOTES.md`.

### B.3. Publish Release Notes
- **[ ] Ensure `docs/RELEASE_NOTES.md` is finalized and accessible.**
  - **Hint:** Link to it from GitHub release, website, etc.

## C. Post-Release Activities

### C.1. Announce Release
- **[ ] Notify Community:** Announce the new release on project channels (e.g., mailing list, Discord, Twitter, project blog/website).
  - **Hint:** Include a link to the release notes and download locations.

### C.2. Merge Release Branch
- **[ ] Merge to Main Development Branch:** Merge the release branch (e.g., `release/vX.Y.Z`) back into the main development branch (e.g., `develop`).
  - **Hint:** `git checkout develop && git merge --no-ff release/vX.Y.Z && git push`.
- **[ ] Merge to Main/Production Branch:** Merge the release branch into the main/production branch (e.g., `main` or `master`).
  - **Hint:** `git checkout main && git merge --no-ff release/vX.Y.Z && git push`.
- **[ ] Delete Release Branch (Optional):** `git branch -d release/vX.Y.Z && git push origin --delete release/vX.Y.Z`.

### C.3. Monitor
- **[ ] Actively Monitor:** Watch for bug reports, user feedback, and any critical issues arising from the new release.
  - **Hint:** Check issue trackers, forums, social media.

### C.4. Housekeeping
- **[ ] Update `docs/ROADMAP.md`:** Mark released features as completed. Update future plans if necessary.
- **[ ] Archive Old Checklists:** Move or archive this completed checklist.
- **[ ] Create New Checklist for Next Cycle:** Prepare a new checklist for the subsequent release based on this template.

---
End of Checklist.