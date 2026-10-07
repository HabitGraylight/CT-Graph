# Deploy Cocktail Atelier on Vercel

[中文](DEPLOY_VERCEL.md) · The application UI currently defaults to Chinese.

The cloud application reuses the public Python advisor through a stateless Vercel function. Supabase provides email accounts and PostgreSQL with row-level access policies. Local books, menus, recipes, inventory and tasting databases are never imported.

## Setup

1. Create a new [Supabase project](https://supabase.com/dashboard). Run [cloud/schema.sql](../cloud/schema.sql) once in its SQL Editor. Do not run it over an existing installation or disable RLS.
2. Import `HabitGraylight/CT-Graph` into [Vercel](https://vercel.com/new). Use the repository root and the **Other** preset. `vercel.json` sets the build command to `python scripts/build_cloud.py`, output to `cloud-dist`, and the Python API to `/api/app`.
3. Deploy once to obtain the stable production domain. Before configuration the app clearly labels account/storage features as unavailable; the public advisor still works.
4. Set these Vercel production environment variables and redeploy:

   | Variable | Value |
   |---|---|
   | `SUPABASE_URL` | Supabase project HTTPS URL |
   | `SUPABASE_PUBLISHABLE_KEY` | Publishable key or legacy anon key; never a secret/service-role key |
   | `APP_ORIGIN` | Exact stable HTTPS production origin, without a path or trailing slash |

5. In Supabase Authentication, enable email/password and email confirmation. Set Site URL to `APP_ORIGIN` and allow `APP_ORIGIN/` as a redirect. Keep the default confirmation and password-recovery link templates.
6. Configure your own SMTP sender before inviting ordinary users. Supabase's default sender is limited to pre-authorized project-team addresses and is not intended for production. See the [official SMTP instructions](https://supabase.com/docs/guides/auth/auth-smtp).

Use Git deployment from the reviewed repository, not an upload of the entire local workspace. Do not place credentials in source, issues or chat. Domain changes require updating both the origin and Auth redirects. Use a separate database/project for staging.

## User flow

Register → confirm email → set nickname and desired flavor intensities → choose a cocktail framework → evaluate or complete → save a private immutable recipe version → actually make and taste it → record intensity, quality and liking separately.

Publication is opt-in and displays a preview of the recipe and preparation context. Private tasting notes stay private. Users may withdraw a publication, delete their own tasting records, and export the current personal window (up to 50 recipes and 200 tasting records).

## Baselines and community selection

Personal targets use recent liked recipes (liking ≥7), optionally shrunk toward an explicit questionnaire target with weight 3. Missing dimensions remain unknown. The chosen framework filters observed evidence. Low desired sweetness changes only an unspecified syrup amount or suggests a small comparison; it does not silently overwrite supplied amounts or predict liking.

Community results count one current, opt-in vote per non-author account and recipe version. At least three votes are required to expose a mean; selection also requires mean liking ≥7. Ranking uses `(sum of liking + 5×6)/(voters+5)`, alongside raw mean and sample count. Each intensity has its own three-person disclosure threshold. Author votes and private notes are excluded.

This is a small-community release. It does not verify unique humans, prevent multi-account voting, or include a moderation console. Scores are self-reported and are not objective sensory certification.

## Verification

```sh
python scripts/cloud_preview.py --port 8877
python -m unittest discover -s tests -q
node --check cloud/web/app.js
python scripts/build_cloud.py
npm ci --prefix tests/database --ignore-scripts
npm test --prefix tests/database
npm ci --prefix tests/web --ignore-scripts
npm test --prefix tests/web
```

Database tests execute the actual PostgreSQL migration, RLS, constraints and triggers in PGlite with synthetic users; they do not test live email delivery. After cloud setup, use separate accounts to verify private-data isolation, publication/withdrawal, one vote per version, login/logout and password-recovery emails.

No cloud project or live account has been provisioned as part of the source implementation. Deployment and live Auth acceptance require the owner's setup above.

References: [Vercel Python functions](https://vercel.com/docs/functions/runtimes/python/api-directory), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
