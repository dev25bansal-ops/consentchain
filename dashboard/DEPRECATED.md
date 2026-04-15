# DEPRECATED: Legacy Dashboard

This directory contains the legacy Vue.js dashboard that is **deprecated**.

## Status: DEPRECATED

This dashboard is maintained for reference only. It should not be used for new projects.

## Migration Path

Please use the **modern dashboard** in `dashboard-v2/` directory instead.

### Why migrate?

| Feature      | Legacy (`dashboard/`) | Modern (`dashboard-v2/`) |
| ------------ | --------------------- | ------------------------ |
| Framework    | Vue 2                 | Vite + React             |
| Build Tool   | Vue CLI               | Vite                     |
| Bundle Size  | Larger                | Optimized                |
| TypeScript   | No                    | Yes                      |
| Hot Reload   | Slower                | Faster                   |
| Dependencies | Outdated              | Current                  |
| Dark Mode    | Partial               | Full                     |

### Feature Comparison

Both dashboards support:

- ✅ Consent management
- ✅ Fiduciary registration
- ✅ Audit trail viewing
- ✅ Grievance submission

The modern dashboard adds:

- ✨ Real-time updates
- ✨ Better accessibility
- ✨ Mobile-responsive design
- ✨ Improved performance
- ✨ Dark mode support

### How to migrate

1. Build the new dashboard:

   ```bash
   cd dashboard-v2
   npm install
   npm run build
   ```

2. Update nginx config to serve from `dashboard-v2/dist`

3. The old dashboard can be safely removed

## Removal Timeline

- **Q2 2024**: Marked as deprecated
- **Q3 2024**: No longer receive updates
- **Q4 2024**: Scheduled for removal

## Questions?

Open an issue at: https://github.com/consentchain/consentchain/issues
