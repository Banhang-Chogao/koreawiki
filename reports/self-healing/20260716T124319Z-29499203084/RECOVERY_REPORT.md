# Recovery Report

- **Timestamp:** 2026-07-16T12:43:35+00:00
- **Run ID:** 29499203084
- **Round:** 1 / 5
- **Status:** failed

## Root Cause

Categories: hugo, markdown, python_qa, seo, frontmatter, images, workflow, dependency

### Signals
- build	Run QA	2026-07-16T12:42:54.6580715Z ##[error]Process completed with exit code 1.

## Files Changed
- `content/** (faq + article-footer via apply_article_footer.py)`
- `content/en/artist/bts-suga-solo-artist-profile.md`
- `content/en/artist/iu-actor-musician-duality.md`
- `content/en/artist/park-chan-wol-interview.md`
- `content/en/culture/hanbok-modern-revival.md`
- `content/en/culture/korean-weddings-evolving.md`
- `content/en/exclusive/behind-the-scenes-goryeo-drama.md`
- `content/en/exclusive/bts-members-individual-futures.md`
- `content/en/exclusive/sm-entertainment-new-girl-group.md`
- `content/en/fashion/k-beauty-fashion-convergence.md`
- `content/en/fashion/seoul-fashion-week-july-2026.md`
- `content/en/feature/hallyu-20-korean-culture-global-wave.md`
- `content/en/feature/korean-voice-actors-rise.md`
- `content/en/feature/seongsu-dong-transformation.md`
- `content/en/food/modern-temple-cuisine.md`
- `content/en/food/sinchon-korean-street-food-guide.md`
- `content/en/kdrama/casting-announcement-july-2026.md`
- `content/en/kdrama/kbs-sageuk-slot-2027.md`
- `content/en/kdrama/lovely-runner-episode-8-recap.md`
- `content/en/kdrama/when-stars-fall-review.md`
- `content/en/kpop/aespa-comeback-armageddon.md`
- `content/en/kpop/newjeans-japan-debut.md`
- `content/en/kpop/riize-rise-of-4th-gen.md`
- `content/en/kpop/seventeen-world-tour-review.md`
- `content/en/movies/harbinger-review.md`
- `content/en/movies/jeonju-film-festival-2026.md`
- `content/en/movies/korean-box-office-july-2026.md`
- `content/en/news/hybe-second-quarter-earnings.md`
- `content/en/news/korean-film-tax-credit-expansion.md`
- `content/en/news/netflix-2027-korean-slate.md`
- `content/en/news/samsung-k-pop-concert.md`
- `content/en/opinion/globalization-of-korean-culture.md`
- `content/en/opinion/mental-health-kpop-industry.md`
- `content/en/photos/busan-night-photography-essay.md`
- `content/en/photos/seoul-night-photography-guide.md`
- `content/en/travel/beyond-seoul-busan-travel-guide.md`
- `content/en/travel/jeju-island-eco-tourism.md`
- `content/en/tv/mnet-street-woman-fighter-season-3.md`
- `content/en/tv/running-man-600th-episode.md`
- `content/en/videos/korean-creator-economy-boom.md`
- `content/en/videos/kpop-video-production-bts.md`

## Fixes Applied
- **article_features**: 1 file(s)
- **markdown_format**: 37 file(s)
- **slugs**: 40 file(s)

## Validation
REMAINING FAILURES: qa, seo

## Remaining Errors

### qa
```
2 files with issues:

  en/travel/jeju-island-eco-tourism.md:
    - Title missing or >120 chars
  en/kdrama/casting-announcement-july-2026.md:
    - Title missing or >120 chars

Tip: python3 scripts/apply_article_footer.py --apply
```

### seo
```
SEO issues in 2 files:

  en/travel/jeju-island-eco-tourism.md:
    - Title >120 (122)
  en/kdrama/casting-announcement-july-2026.md:
    - Title >120 (136)
```

## Suggested Manual Fix

1. Open the workflow log in `workflow.log`.
2. Consult `scientist.md` for a matching past entry.
3. Apply a minimal fix; never fabricate content.
4. Run `python3 scripts/self_healing.py validate`.
5. Commit and push — do **not** force-deploy while validations are red.
