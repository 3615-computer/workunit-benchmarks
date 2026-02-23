#!/usr/bin/env bash
# Reset all benchmark test data for the benchmark user's organization.
# Wipes all projects, workunits, tasks, context atoms, assets, directories,
# executions, and notifications — preserving users and the organization itself.
#
# Run from any directory (script locates project root automatically).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Set BENCHMARK_ORG_ID to your organization's UUID.
# Find it in your Workunit org settings or via the get_authenticated_user MCP tool.
BENCHMARK_ORG_ID="${BENCHMARK_ORG_ID:?Error: BENCHMARK_ORG_ID env var must be set}"

FORCE=${FORCE:-0}

echo "=== Workunit MCP Benchmark — Full Environment Reset ==="
echo ""
echo "Target org: $BENCHMARK_ORG_ID"
echo ""

if [[ "$FORCE" != "1" ]]; then
    echo "This will permanently delete ALL of the following in the benchmark org:"
    echo "  • projects, workunits, tasks, context atoms"
    echo "  • assets (all types: product, system, people, knowledge)"
    echo "  • directories"
    echo "  • executions, execution steps, execution jobs"
    echo "  • notifications"
    echo ""
    echo "Users and the organization itself are preserved."
    echo ""
    read -p "Continue? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

echo ""
echo "Resetting benchmark data in dev database..."
echo ""

docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T db psql -U workunit -d workunit <<SQL
-- ============================================================
-- Benchmark environment reset
-- Org: $BENCHMARK_ORG_ID
--
-- Deletion order respects foreign key constraints.
-- Cascades handle most child rows automatically; explicit
-- deletes here are for tables with ON DELETE SET NULL or
-- tables not directly parented to projects/workunits.
-- ============================================================

-- Snapshot before
SELECT
    (SELECT COUNT(*) FROM projects      WHERE organization_id = '$BENCHMARK_ORG_ID') AS projects_before,
    (SELECT COUNT(*) FROM workunits     WHERE organization_id = '$BENCHMARK_ORG_ID') AS workunits_before,
    (SELECT COUNT(*) FROM tasks t
        JOIN workunits w ON t.workunit_id = w.id
        WHERE w.organization_id = '$BENCHMARK_ORG_ID')                               AS tasks_before,
    (SELECT COUNT(*) FROM context_atoms ca
        JOIN workunits w ON ca.workunit_id = w.id
        WHERE w.organization_id = '$BENCHMARK_ORG_ID')                               AS context_atoms_before,
    (SELECT COUNT(*) FROM assets        WHERE organization_id = '$BENCHMARK_ORG_ID') AS assets_before,
    (SELECT COUNT(*) FROM executions    WHERE organization_id = '$BENCHMARK_ORG_ID') AS executions_before,
    (SELECT COUNT(*) FROM notifications WHERE organization_id = '$BENCHMARK_ORG_ID') AS notifications_before,
    (SELECT COUNT(*) FROM directories   WHERE organization_id = '$BENCHMARK_ORG_ID') AS directories_before;

-- Notifications (ON DELETE SET NULL on project/workunit/task/asset refs —
-- rows would be left as orphaned shells; delete them explicitly)
DELETE FROM notifications WHERE organization_id = '$BENCHMARK_ORG_ID';

-- Subscriptions (same pattern — CASCADE handles workunit/task/asset deletes
-- but project_id uses ON DELETE SET NULL, leaving orphans)
DELETE FROM subscriptions WHERE organization_id = '$BENCHMARK_ORG_ID';

-- Executions (ON DELETE CASCADE from workunits, but delete explicitly
-- before workunits to ensure execution_steps/jobs go with them)
DELETE FROM executions WHERE organization_id = '$BENCHMARK_ORG_ID';

-- Projects → cascades to:
--   workunits → context_atoms, tasks (→ task_comments, task_time_logs),
--               workunit_assets, checkin_response_workunits
--   project_assets
--   checkins (project_id SET NULL only, but checkins belong to org via
--             organization_id cascade anyway)
DELETE FROM projects WHERE organization_id = '$BENCHMARK_ORG_ID';

-- Assets (project_assets cascade removed them from join table above;
-- now remove the asset rows themselves)
DELETE FROM assets WHERE organization_id = '$BENCHMARK_ORG_ID';

-- Directories (assets use ON DELETE SET NULL for directory_id, so
-- asset rows are already gone; delete directory tree)
DELETE FROM directories WHERE organization_id = '$BENCHMARK_ORG_ID';

-- Snapshot after
SELECT
    (SELECT COUNT(*) FROM projects      WHERE organization_id = '$BENCHMARK_ORG_ID') AS projects_after,
    (SELECT COUNT(*) FROM workunits     WHERE organization_id = '$BENCHMARK_ORG_ID') AS workunits_after,
    (SELECT COUNT(*) FROM tasks t
        JOIN workunits w ON t.workunit_id = w.id
        WHERE w.organization_id = '$BENCHMARK_ORG_ID')                               AS tasks_after,
    (SELECT COUNT(*) FROM context_atoms ca
        JOIN workunits w ON ca.workunit_id = w.id
        WHERE w.organization_id = '$BENCHMARK_ORG_ID')                               AS context_atoms_after,
    (SELECT COUNT(*) FROM assets        WHERE organization_id = '$BENCHMARK_ORG_ID') AS assets_after,
    (SELECT COUNT(*) FROM executions    WHERE organization_id = '$BENCHMARK_ORG_ID') AS executions_after,
    (SELECT COUNT(*) FROM notifications WHERE organization_id = '$BENCHMARK_ORG_ID') AS notifications_after,
    (SELECT COUNT(*) FROM directories   WHERE organization_id = '$BENCHMARK_ORG_ID') AS directories_after;
SQL

echo ""
echo "Reset complete."
echo ""
echo "Next: ensure LM Studio is running, then launch the benchmark:"
echo "  python benchmark/scripts/runner.py --models benchmark/models.txt 2>&1 | tee benchmark/reports/agentic_run.log"
