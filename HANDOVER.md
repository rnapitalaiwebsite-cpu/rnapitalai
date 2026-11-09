# Napitalai Engineers website: setup and handover

Phase 1 of the R. Napitalai Limited website, built by Eyemagine PNG.
This repository holds everything: the content, the site builder, the editing screen and the publishing set-up.

## How it works

1. RNL staff sign in at **napitalaiengineers.com/admin** and edit projects, news, team, services, offices or page text.
2. Each save is stored in this GitHub repository, with a full history that can be rolled back.
3. GitHub rebuilds the site (`python3 build.py`) and publishes it to GitHub Pages, usually within 2 to 3 minutes.

| Folder / file | What it is |
|---|---|
| `content/` | All editable text and photo choices (JSON). Changed by the editing screen. |
| `static/` | Design, scripts, logos and photos. New uploads land in `static/assets/img/uploads/`. |
| `static/admin/` | The editing screen (Decap CMS, free and open source). |
| `build.py` | Turns `content/` into the website in `_site/`. Python 3 only, no packages. |
| `.github/workflows/deploy.yml` | Rebuilds and publishes on every change. |
| `oauth-worker/` | Small free sign-in helper so staff can log in to `/admin` with GitHub. |
| `netlify.toml` | Only if RNL ever moves to Netlify (see costs below). |

## Go-live steps

**1. GitHub (RNL's own account)**
- Create a **public** repository, e.g. `rnl-website`, and upload this folder.
  Public is recommended: the site content is public anyway, and GitHub Pages from a private repository needs a paid plan.
- Settings > Pages > Source: **GitHub Actions**. Custom domain: `napitalaiengineers.com`, tick *Enforce HTTPS*.
- Settings > Collaborators: add each staff member who will edit (they each need a free GitHub account).

**2. Sign-in helper (Cloudflare, free)**
- GitHub > Settings > Developer settings > OAuth Apps > New:
  homepage `https://napitalaiengineers.com`, callback `https://rnl-cms-auth.<your-subdomain>.workers.dev/callback`.
- Deploy `oauth-worker/` to Cloudflare Workers (`npx wrangler deploy` from that folder, or paste `worker.js` in the dashboard).
- Add secrets `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` from the OAuth App.

**3. Point the editing screen at them**
In `static/admin/config.yml`, replace the two `SET-ME` values:
`repo: rnapitalaiwebsite-cpu/rnapitalai` (already set) and `base_url: https://rnl-cms-auth.<your-subdomain>.workers.dev`.

**4. Enquiry form**
- Create a free key at web3forms.com using the inbox that should receive enquiries.
- In `/admin` > Pages and settings > Company details > Enquiry form, paste the access key.
- Until a key is set, the form opens the visitor's email app with the enquiry filled in, so nothing is lost.

**5. Google**
- Create a Google Analytics 4 property in RNL's Google account; paste the `G-…` ID in `/admin` > Search and analytics.
- Add the site to Google Search Console (HTML tag method); paste the code in the same place, then submit `https://napitalaiengineers.com/sitemap.xml`.

**6. Domain (RNL's ICT Manager)**
At the domain registrar, point `napitalaiengineers.com` to GitHub Pages:
A records `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`; `www` CNAME `rnapitalaiwebsite-cpu.github.io`.

## Running costs

| Item | Cost |
|---|---|
| GitHub repository, Pages hosting and rebuilds (public repo) | Free |
| Editing screen (Decap CMS) | Free, open source |
| Sign-in helper (Cloudflare Workers free tier) | Free |
| Enquiry form (Web3Forms free tier) | Free |
| Google Analytics 4 and Search Console | Free |
| Domain renewal | What RNL already pays each year |

Why not Netlify's free plan: each publish uses 15 of its 300 monthly credits, so roughly 20 saves a month before the site is paused until the next month.

## Building on a computer

```
python3 build.py               # production build into _site/
python3 build.py --staging     # adds a staging banner and blocks search engines
python3 -m http.server -d _site 8000   # view at http://localhost:8000
```

To try the editing screen locally: run `npx decap-server` in this folder, then open `http://localhost:8000/admin/`.

## Still needed from RNL before launch

- Confirmation of figures shown: project values (K100m+, K200m+), client list, "20+ long-term clients".
- Which project each Facebook site photo belongs to, so photos can be attached to the right project pages.
- Photo of Donald Lemeki; photos and titles of any other staff to be shown.
- Addresses, phones and emails for the Lae, Kokopo and Goroka offices.
- The inbox for enquiries, the names and emails of staff who will edit, and access to the GitHub account and domain settings.
