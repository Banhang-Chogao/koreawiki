# SEO reports

GitHub Actions writes compact Search Console summaries and research candidates here at
runtime. They are uploaded as workflow artifacts and ignored by Git so raw query/page data
and any environment-derived material are never committed. Configure `GSC_CLIENT_EMAIL`,
`GSC_PRIVATE_KEY` and `GSC_SITE_URL` as repository secrets to enable the report.
