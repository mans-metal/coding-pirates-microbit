# Hosting (not hosted yet)

The site is plain HTML and CSS: no build step, no dependencies. Any static host works.

## To do before hosting

- [ ] Check you may publish every image in `images/` (see Credits in the README), and fill in the two missing sources.
- [ ] Use your GitHub no-reply email for commits, and turn on "Block command line pushes that expose my email" in GitHub Settings, Emails.

## GitHub Pages

1. Repo Settings, Pages.
2. Source: Deploy from a branch, branch `main`, folder `/ (root)`.
3. Tick "Enforce HTTPS".
4. The site appears at `https://<username>.github.io/coding-pirates-microbit/`.

## Languages

- [ ] Once you know the address, add `<link rel="alternate" hreflang="en" href="https://.../en/">` style tags (full URLs) to the `<head>` of each page, one per language, so search engines link the versions.

## Hardening

Every page already carries a Content-Security-Policy tag (it blocks scripts, forms and anything loaded from outside) and a no-referrer tag. A test checks this. If you add a page, copy the two `<meta>` lines from an existing page. Do not add inline styles or scripts, because the policy blocks them.

If you add `target="_blank"` to any link, also add `rel="noopener noreferrer"`.
