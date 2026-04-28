## Plan: Project Consolidation and Documentation Overhaul

This plan outlines restructuring the workspace to an intern-level, professional monorepo setup while creating a clean, cohesive documentation suite. We will rename the scattered folders, consolidate the intermediate documentation into a structured `docs/` folder, and clean up the root repository.

**Steps**
1. **Directory Renaming**
   - Rename the `Extension` folder to `frontend`.
   - Rename the `himanshu` folder to `backend`. 
2. **Metadata Extraction & Summarization**
   - Extract key architectural, database (FAISS), API, and WebSocket details from the current 26 `.md` scattered files.
3. **Draft New Documentation Suite** (in parallel with step 2)
   - Create `docs/ARCHITECTURE.md`: Cover system design, modular backend, and frontend WXT architecture.
   - Create `docs/SETUP.md`: Provide local environment setup, `.env` file requirements, RAG/FAISS vector setup, and Python dependencies.
   - Create `docs/AGENTS.md`: Detail the deep agents, DOM extraction agents, and Google Tools subagents.
   - Create a polished root `README.md`: Feature a high-level overview, quick start, and links to the comprehensive `docs/`.
4. **Cleanup Unnecessary Files**
   - Delete all old markdown clutter (e.g., `*SUMMARY.md`, `*FIX.md`, `*_SETUP.md`, `*_GUIDE.md`) from the root and old backend paths.
5. **Path and Script Updates**
   - Update repository helper scripts (like `setup_context_optimization.bat`, `setup_context_optimization.sh` or `.gitignore`) to reference `backend` instead of `himanshu` and `frontend` instead of `Extension`.

**Relevant files**
- `Extension/` -> to `frontend/`
- `himanshu/` -> to `backend/`
- `.bat` / `.sh` environment scripts — Update paths to reflect directory changes
- New layout:
  - `docs/ARCHITECTURE.md`
  - `docs/SETUP.md`
  - `docs/AGENTS.md`
  - `README.md`
- All 26 `.md` files in the root — targeted for deletion

**Verification**
1. Check that the `/frontend/` build (e.g., WXT build) completes properly without path errors.
2. Check that the `/backend/server.py` boots up cleanly with its `.env` config.
3. Preview the generated markdown documentation locally to ensure proper structure and links.

**Decisions**
- Intermediate and patch log files (like `COMPATIBILITY_FIX.md` and `BACKEND_MIGRATION.md`) are no longer needed as a live document; their stable insights will be baked into the final architectural overview.
- Adopt standard `frontend` / `backend` naming convention expected in professional setups.