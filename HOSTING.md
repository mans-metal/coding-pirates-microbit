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

## Hardening (optional)

Add inside `<head>` of every page (`index.html`, `en/index.html`, `da/index.html`). The page has no scripts, fonts or inline styles, so this should not break anything; check by opening the hosted page.

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
```

If you add `target="_blank"` to any link, also add `rel="noopener noreferrer"`.
