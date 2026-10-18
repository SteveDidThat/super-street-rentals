# Super Street Rentals: website prototype

A static, $0 website: exotic and ex-rental auction listings (auto-updated feed), a broker "Request this car" lead form, and a Turo-style peer-to-peer rental preview (demo data).
**Nothing in this repo bids, registers at, or buys from any auction.**

## Structure
```
index.html            Home (hero, broker model, ending-soon cars)
exotic.html           Exotic auctions (filters: make, site, ending window, sort; countdowns; detail modal)
ex-rental.html        Ex-rental / fleet auctions (+ sporty filter)
request.html          "Request this car" broker lead form (?listing=<id>)
rent.html, car.html   P2P rental search + car detail w/ availability calendar & booking request  (DEMO data)
list-your-car.html    Host onboarding form
host-dashboard.html   Host dashboard mock
how-it-works.html, faq.html, contact.html
feed.json             Generated listings feed (do not hand-edit)
data/                 exotic_listings / rental_listings CSV+JSON, stub_rental_cars.json (demo)
assets/               style.css, app.js, config.js (PLACEHOLDERS: lead email, form endpoint), logo, fonts
scripts/fetch_listings.py   Ingester (Python 3.9+ stdlib only)
.github/workflows/update-listings.yml   Cron every 30 min → regenerate feed → commit → Pages redeploys
```

## Run locally
```bash
python3 scripts/fetch_listings.py --out data --site .   # refresh feed.json
python3 -m http.server 8787                              # open http://localhost:8787
```

## Deploy free on GitHub Pages (recommended)
1. Create a free GitHub account and a **public** repo, e.g. `superstreetrentals` (Pages on private repos needs a paid plan).
2. Push this folder:
   ```bash
   git remote add origin https://github.com/<you>/superstreetrentals.git
   git push -u origin main
   ```
3. Repo **Settings → Pages**: Source = "Deploy from a branch", Branch = `main`, folder `/ (root)`. The site goes live at `https://<you>.github.io/superstreetrentals/`.
4. Repo **Settings → Actions → General → Workflow permissions**: select "Read and write permissions" (the workflow commits feed.json).
5. **Actions** tab → "Update auction listings" → **Run workflow** once to test. After that it runs every 30 min.
6. Optional custom domain (about $10/yr): Settings → Pages → Custom domain, then add the DNS CNAME at the registrar.

### Alternative: Cloudflare Pages
Connect the GitHub repo in Cloudflare Pages (framework: none, build command: empty, output directory: `/`). The free plan allows 500 builds/month, and a 30-min cron triggers about 1,440. Use GitHub Pages for the auto-updating feed, or set the cron to `0 */2 * * *` if you use Cloudflare.

## Before launch: edit `assets/config.js`
- `formEndpoint`: create a free Formspree form (https://formspree.io) and paste its endpoint. Without it, forms fall back to `mailto:`.
- `leadEmail`, `phone`, `brokerFeeText`: these are placeholders now.
- Review the legal/ToS notes in `data_pipeline_plan.md`. Get permission before republishing auction photos commercially, and have a lawyer write the Terms, Privacy Policy and disclaimers.
