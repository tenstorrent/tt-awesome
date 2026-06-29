// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Tenstorrent USA, Inc.

const fs = require("fs");
const path = require("path");
const MarkdownIt = require("markdown-it");

// Inline-only markdown renderer for short feed descriptions (release summaries,
// article blurbs). We use renderInline() rather than render() so the output has
// no block wrapper — it drops cleanly inside the existing <p class="planet-item-desc">
// without producing invalid nested <p> tags. html:false escapes any raw HTML in
// the source, which matters because some descriptions originate from untrusted
// external RSS feeds; linkify:false keeps bare URLs untouched so only explicit
// markdown ([text](url), **bold**, `code`) is interpreted.
const mdInline = new MarkdownIt({ html: false, linkify: false });
// Disable image syntax: ![alt](url) would emit an <img> that auto-fetches on
// render. Since this runs on untrusted external feed content, that would allow
// tracking pixels / unexpected network requests. We keep links/code/emphasis only.
mdInline.disable("image");

// Block-level markdown renderer for full feed <content> blocks. Same safety
// posture as mdInline (no raw HTML, no auto-fetching images), but keeps block
// wrappers so multi-paragraph release summaries render as real <p> tags.
const mdBlock = new MarkdownIt({ html: false, linkify: false });
mdBlock.disable("image");

// Shared HTML escaper for text we interpolate directly into the content block.
const escapeHtml = mdBlock.utils.escapeHtml;

// Build the rich HTML <content> block shared by every feed (Atom <content
// type="html"> and JSON Feed content_html). Sections whose data is absent are
// omitted entirely. Accepts a single normalized object — see plan Task 1.
function buildFeedContentHtml(item) {
  if (!item) return "";
  const parts = [];

  // 1. Description / summary — block markdown (paragraphs preserved).
  if (item.description) parts.push(mdBlock.render(item.description));

  // 2. Links — every typed link as a labeled anchor. Label falls back to a
  //    title-cased link type (e.g. "article" → "Article").
  // Defense-in-depth: only render http(s) links. Entry/release URLs are
  // https-validated upstream (entries.js isSafeHttpsUrl), but this builder is
  // general — drop javascript:/data:/etc. so a bad URL can't become a live href.
  const links = (item.links || []).filter(
    (l) => l && l.url && /^https?:\/\//i.test(l.url)
  );
  if (links.length) {
    // Render links inline, separated by " · ", rather than as a <ul>/<li> list.
    // HTML readers show a tidy one-liner, and — crucially — clients that flatten
    // HTML to plain text (Slack's RSS app, plain-text views) still get readable
    // output: "<li>Repo</li><li>1.3.0</li>" flattens to "Repo1.3.0", but
    // "<a>Repo</a> · <a>1.3.0</a>" flattens to "Repo · 1.3.0". (See deep feed
    // review 2026-06-29.)
    const anchors = links
      .map((l) => {
        const label = l.label
          ? escapeHtml(l.label)
          : l.type
          ? escapeHtml(l.type.charAt(0).toUpperCase() + l.type.slice(1))
          : escapeHtml(l.url);
        return `<a href="${escapeHtml(l.url)}">${label}</a>`;
      })
      .join(" · ");
    parts.push(`<p><strong>Links:</strong> ${anchors}</p>`);
  }

  // 3. Attribution — author, affiliation, date added, separated by middots.
  const attr = [];
  if (item.author) {
    // Only treat the author as a GitHub @handle when author_url is a github.com
    // profile (entries.js derives that URL from the repo owner login). For
    // papers/talks/blogs the `author` field is a display name or author list
    // ("Jenny Lynn Almerol, …"), so an "@" prefix would be misleading — render
    // it as a plain name instead. (See deep feed review 2026-06-29.)
    // Same defense-in-depth as the link list: only turn author_url into a live
    // <a href> when it's an http(s) URL, so an unvalidated javascript:/data:
    // author_url can't become an XSS vector; otherwise render the name plainly.
    const httpAuthorUrl =
      item.author_url && /^https?:\/\//i.test(item.author_url);
    const isGitHubHandle =
      httpAuthorUrl && /^https?:\/\/github\.com\//i.test(item.author_url);
    if (isGitHubHandle) {
      attr.push(`By <a href="${escapeHtml(item.author_url)}">@${escapeHtml(item.author)}</a>`);
    } else if (httpAuthorUrl) {
      attr.push(`By <a href="${escapeHtml(item.author_url)}">${escapeHtml(item.author)}</a>`);
    } else {
      attr.push(`By ${escapeHtml(item.author)}`);
    }
  }
  if (item.affiliation) attr.push(escapeHtml(item.affiliation));
  if (item.added_at) attr.push(`added ${escapeHtml(item.added_at)}`);
  if (attr.length) parts.push(`<p>${attr.join(" · ")}</p>`);

  // 4. Tags + categories — comma-separated, emphasized.
  const tagBits = [...(item.tags || []), ...(item.categories || [])];
  if (tagBits.length) {
    parts.push(`<p><em>${tagBits.map(escapeHtml).join(", ")}</em></p>`);
  }

  return parts.join("\n");
}

// Build a feed timestamp from a date that may be date-only. See the feedDateTime
// filter registration below for the full rationale. Shared as a module-scope
// function so both the filter and jsonFeedItems produce identical timestamps.
function feedDateTime(dateStr, index = 0) {
  if (!dateStr) return "1970-01-01T00:00:00Z";
  if (/T\d{2}:\d{2}/.test(dateStr)) return dateStr; // already a full timestamp
  const i = Math.max(0, Math.min(86399, Number(index) || 0)); // clamp to 1 day
  const secs = 86399 - i; // earlier in feed (newer) → later time that day
  const hh = String(Math.floor(secs / 3600)).padStart(2, "0");
  const mm = String(Math.floor((secs % 3600) / 60)).padStart(2, "0");
  const ss = String(secs % 60).padStart(2, "0");
  return `${dateStr}T${hh}:${mm}:${ss}Z`;
}

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addPassthroughCopy({ ".nojekyll": ".nojekyll" });
  // Copy the generated API export to the site root so it's reachable at /data.json
  // on GitHub Pages.  The file is generated by scripts/generate_data_json.py before
  // `npm run build` runs (see deploy.yml).
  eleventyConfig.addPassthroughCopy({ "data.json": "data.json" });

  eleventyConfig.addFilter("truncate", (str, len) =>
    str && str.length > len ? str.slice(0, len) + "…" : str
  );

  // Render inline markdown in a short string (e.g. a feed description) to HTML.
  // Must be paired with `| safe` in the template since it returns HTML markup.
  // Returns "" for falsy input so templates can pipe unconditionally.
  eleventyConfig.addFilter("markdownInline", (str) =>
    str ? mdInline.renderInline(str) : ""
  );

  // Render the full rich HTML content block for a feed item. Pair with
  // `| cdataSafe | safe` in Atom templates. See buildFeedContentHtml above.
  eleventyConfig.addFilter("feedContentHtml", (item) => buildFeedContentHtml(item));

  // Build a feed timestamp from a date that may be date-only (entry `added_at`
  // is "YYYY-MM-DD" with no time). Many entries share an `added_at`, so emitting
  // a flat "T00:00:00Z" leaves readers that sort by <updated>/date_published
  // unable to order same-day items. We synthesize a deterministic *descending*
  // time-of-day from the item's position in the (newest-first) feed so that
  // date-sorting in a reader reproduces our curated order. This is an ordering
  // key, NOT a real timestamp — `added_at` carries no real time-of-day.
  // Strings that already include a time (release `publishedAt`) pass through.
  eleventyConfig.addFilter("feedDateTime", (dateStr, index = 0) =>
    feedDateTime(dateStr, index)
  );

  // Collapse all runs of whitespace (including newlines) to single spaces.
  // Used on the release feed <summary> so a multi-paragraph summary can never
  // render as a run-on — the summary must be a single clean line, while the
  // full text still appears (with paragraphs) in <content>.
  eleventyConfig.addFilter("singleLine", (str) =>
    (str || "").replace(/\s+/g, " ").trim()
  );

  // Make a string safe to embed inside an XML CDATA section. A literal "]]>"
  // would close the section early and break the feed (or allow injection), so
  // split it across two CDATA sections per the standard idiom. markdownInline's
  // output already escapes ">" to "&gt;" so this is normally a no-op, but we
  // neutralize explicitly so the guarantee can't drift with config changes.
  eleventyConfig.addFilter("cdataSafe", (str) =>
    (str || "").replace(/]]>/g, "]]]]><![CDATA[>")
  );

  // Format an ISO date string (YYYY-MM-DD) as "Mon DD, YYYY" (e.g. "May 8, 2026").
  eleventyConfig.addFilter("prettyDate", (dateStr) => {
    if (!dateStr) return "";
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const parts = dateStr.split("-");
    if (parts.length < 3) return dateStr;
    const [y, m, d] = parts;
    return `${months[parseInt(m, 10) - 1]} ${parseInt(d, 10)}, ${y}`;
  });

  // Return the top entry for a category (featured first, then by sort order).
  eleventyConfig.addFilter("featuredForCategory", (entries, slug) => {
    const cat = (entries || []).filter(
      (e) => Array.isArray(e.categories) && e.categories.includes(slug)
    );
    return cat.find((e) => e.featured) || cat[0] || null;
  });

  // Count entries belonging to a category.
  eleventyConfig.addFilter("countForCategory", (entries, slug) =>
    (entries || []).filter(
      (e) => Array.isArray(e.categories) && e.categories.includes(slug)
    ).length
  );

  // Assign one unique featured entry per category for the home page showcase.
  // Each entry is used at most once (first category it best fits wins).
  // Within a category, candidates are ranked: featured first, then by stars.
  // Grayskull-only and BUDA entries are deprioritized to last resort.
  eleventyConfig.addFilter("diversifiedFeatured", (entries, categories) => {
    const used = new Set();
    const result = {};

    // Deprioritize entries that are Grayskull-only or BUDA-related.
    const isDeprioritized = (e) => {
      const id   = (e.id   || "").toLowerCase();
      const name = (e.name || "").toLowerCase();
      if (id.includes("buda") || name.includes("buda")) return true;
      // Grayskull-only: hardware list exists and every item is "grayskull"
      const hw = e.hardware || [];
      if (hw.length > 0 && hw.every((h) => h === "grayskull")) return true;
      return false;
    };

    // Showcase sort: featured entries first, then by stars descending.
    const showcaseSort = (a, b) => {
      const fd = (a.featured ? 0 : 1) - (b.featured ? 0 : 1);
      if (fd !== 0) return fd;
      return (b.stars || 0) - (a.stars || 0);
    };

    for (const cat of categories) {
      const candidates = (entries || [])
        .filter((e) => Array.isArray(e.categories) && e.categories.includes(cat.slug))
        .slice()
        .sort(showcaseSort);

      // Prefer: not yet used AND not deprioritized.
      const preferred = candidates.filter((e) => !used.has(e.id) && !isDeprioritized(e));
      // Fallback: not yet used (even if deprioritized).
      const fallback  = candidates.filter((e) => !used.has(e.id));

      const pick = preferred[0] || fallback[0] || null;
      if (pick) used.add(pick.id);
      result[cat.slug] = pick;
    }

    return result;
  });

  // Build a deduplicated, date-sorted list of article-type feed items from the
  // full entries collection.  Runs entirely in JS to avoid Nunjucks limitations
  // around namespace mutation with complex object literals.
  //
  // Returns up to `limit` objects with the shape:
  //   { entryId, entryName, entryDesc, affiliation, categories,
  //     linkType, linkUrl, linkLabel, added_at }
  //
  // Article link types: article, lesson, paper, talk, video, demo.
  eleventyConfig.addFilter("articleFeedItems", (entries, limit = 50) => {
    const ARTICLE_TYPES = new Set(["article", "lesson", "paper", "talk", "video", "demo"]);
    const sorted = [...(entries || [])].sort((a, b) => {
      const da = a.added_at || "1970-01-01";
      const db = b.added_at || "1970-01-01";
      // Descending: newest first.
      return db < da ? -1 : db > da ? 1 : 0;
    });

    const seen = new Set();
    const items = [];

    for (const entry of sorted) {
      for (const link of entry.links || []) {
        if (!ARTICLE_TYPES.has(link.type)) continue;
        if (seen.has(link.url)) continue;
        seen.add(link.url);
        items.push({
          entryId:    entry.id,
          entryName:  entry.name,
          entryDesc:  entry.description || "",
          affiliation: entry.affiliation || "",
          categories: entry.categories || [],
          linkType:   link.type,
          linkUrl:    link.url,
          linkLabel:  link.label || (link.type.charAt(0).toUpperCase() + link.type.slice(1)),
          added_at:   entry.added_at || "1970-01-01",
          // feedContentHtml contract fields:
          description: entry.description || "",
          links:      entry.links || [],
          author:     entry.author || "",
          author_url: entry.author_url || "",
          tags:       entry.tags || [],
        });
        if (items.length >= limit) return items;
      }
    }
    return items;
  });

  // Build the complete JSON Feed 1.1 items array for the combined feed.
  //
  // Accepts:
  //   entries       — full entries collection (from _data/entries.js)
  //   recentReleases — from _data/recentReleases.js
  //
  // Returns an array of JSON Feed item objects containing:
  //   - One item per release in recentReleases
  //   - One item per entry (up to 50, sorted newest-first by added_at)
  //   - One item per article-type link per entry (deduped by URL)
  //
  // Article link types matched: article, lesson, paper, talk, video, demo.
  eleventyConfig.addFilter("jsonFeedItems", (entries, recentReleases) => {
    const ARTICLE_TYPES = new Set(["article", "lesson", "paper", "talk", "video", "demo"]);
    const items = [];

    // 1. Release items — one per entry in recentReleases.
    for (const rel of recentReleases || []) {
      const summary = rel.summary ||
        `${rel.entryName} released ${rel.tagName}. Repository: ${rel.repoUrl}`;
      items.push({
        id:             rel.url,
        url:            rel.url,
        title:          `${rel.entryName} ${rel.tagName}`,
        content_html:   buildFeedContentHtml(rel),
        summary:        summary,
        date_published: rel.publishedAt,
        tags:           [rel.affiliation, "release"].filter(Boolean),
      });
    }

    // 2. Sort entries by added_at descending (newest first).
    const sorted = [...(entries || [])].sort((a, b) => {
      const da = a.added_at || "1970-01-01";
      const db = b.added_at || "1970-01-01";
      return db < da ? -1 : db > da ? 1 : 0;
    });

    const seenLinks = new Set();

    for (let i = 0; i < Math.min(sorted.length, 50); i++) {
      const entry = sorted[i];

      // Resolve a canonical URL for the entry.  Prefer the repo link; fall back
      // to the first link of any type; last resort is an anchor on the homepage.
      const repoLink = (entry.links || []).find((l) => l.type === "repo");
      const anyLink  = (entry.links || []).find((l) => l.url);
      const repoUrl  = repoLink ? repoLink.url : null;

      // Full ISO 8601 timestamp. added_at is date-only, so synthesize a
      // deterministic descending time-of-day from the feed position (i) to give
      // same-day items a stable order in date-sorting readers. See feedDateTime.
      const entryDate = feedDateTime(entry.added_at, i);

      // 2a. One item for the entry itself.
      items.push({
        id:             repoUrl || `https://tenstorrent.github.io/tt-awesome/#${entry.id}`,
        url:            repoUrl || (anyLink ? anyLink.url : `https://tenstorrent.github.io/tt-awesome/#${entry.id}`),
        title:          entry.name,
        content_html:   buildFeedContentHtml(entry),
        summary:        entry.description || "",
        date_published: entryDate,
        tags:           [...(entry.categories || []), entry.affiliation, "entry"].filter(Boolean),
      });

      // 2b. One item per article-type link (deduped by URL).
      for (const link of entry.links || []) {
        if (!ARTICLE_TYPES.has(link.type)) continue;
        if (seenLinks.has(link.url)) continue;
        seenLinks.add(link.url);
        items.push({
          id:             link.url,
          url:            link.url,
          title:          `${entry.name} — ${link.label || link.type}`,
          // This item represents one specific link, so its content lists only
          // that link — not the entry's whole link set (which the entry item
          // above already carries). Avoids byte-identical duplicate content
          // across the two items in the combined feed. (Deep feed review.)
          content_html:   buildFeedContentHtml({ ...entry, links: [link] }),
          summary:        entry.description || "",
          date_published: entryDate,
          tags:           [
            ...(entry.categories || []),
            entry.affiliation,
            link.type,
            "article",
          ].filter(Boolean),
        });
      }
    }

    // Sort all items newest-first regardless of which sub-list they came from.
    items.sort((a, b) => (a.date_published < b.date_published ? 1 : a.date_published > b.date_published ? -1 : 0));
    return items;
  });

  // Builds the Planet Tenstorrent item list from three sources:
  //   entries        — article-type links from curated entry JSONs
  //   recentReleases — stable releases (dev builds filtered out)
  //   externalFeeds  — approved items from planet_feeds.json (YouTube, arXiv, etc.)
  // Returns items sorted newest-first; URLs are deduplicated across all sources.
  eleventyConfig.addFilter("planetItems", (entries, recentReleases, externalFeeds) => {
    const ARTICLE_TYPES = new Set(["article", "lesson", "paper", "talk", "video", "demo"]);
    const items = [];
    const seenUrls = new Set();

    // Article-type links from all entries
    for (const entry of entries || []) {
      for (const link of entry.links || []) {
        if (!ARTICLE_TYPES.has(link.type)) continue;
        if (seenUrls.has(link.url)) continue;
        seenUrls.add(link.url);
        const dateStr = entry.added_at || "1970-01-01";
        items.push({
          type:        link.type,
          title:       entry.name,
          url:         link.url,
          description: entry.description || "",
          date:        dateStr,
          dateISO:     dateStr + "T00:00:00Z",
          projectName: entry.name,
          projectId:   entry.id,
          affiliation: entry.affiliation || "",
          label:       link.label || "",
        });
      }
    }

    // Build a repo-URL → entry lookup for backfilling missing projectIds below.
    const entryByRepoUrl = {};
    for (const entry of entries || []) {
      const repoLink = (entry.links || []).find(l => l.type === "repo");
      if (repoLink && repoLink.url) entryByRepoUrl[repoLink.url] = entry;
    }

    // Approved external feed items first (YouTube, arXiv, Reddit, community blogs,
    // and summarized releases). Processed before recentReleases so that summarized
    // release items from planet_feeds.json win the URL dedup over the generic fallback.
    // approved=false items stay in planet_feeds.json for PR review but don't render.
    for (const item of externalFeeds || []) {
      if (!item.approved) continue;
      if (seenUrls.has(item.url)) continue;
      seenUrls.add(item.url);
      // Backfill projectId for summarized release items — summarize_releases.py stores
      // null, but we can recover it by matching the release URL against known repo URLs.
      if (item.type === "release" && !item.projectId && item.url) {
        for (const [repoUrl, entry] of Object.entries(entryByRepoUrl)) {
          if (item.url.startsWith(repoUrl + "/releases/")) {
            item.projectId = entry.id;
            item.projectName = item.projectName || entry.name;
            break;
          }
        }
      }
      items.push(item);
    }

    // Stable releases from recentReleases — skip pre-release builds and any release
    // already covered by a summarized item in externalFeeds (seenUrls handles dedup).
    // dev: "1.2.0.dev20260530", "v0.72.0-dev20260529"  RC: "v0.72.0-rc4"  QA: "v1.0-qa1"
    for (const rel of recentReleases || []) {
      if (/[\.\-]dev[\.\d]|[-.]rc\d|[-.]qa[\d.]/i.test(rel.tagName || "")) continue;
      if (seenUrls.has(rel.url)) continue;
      seenUrls.add(rel.url);
      const dateStr = rel.publishedAt ? rel.publishedAt.slice(0, 10) : "1970-01-01";
      items.push({
        type:        "release",
        title:       `${rel.entryName} ${rel.tagName}`,
        url:         rel.url,
        description: `New release: ${rel.entryName} ${rel.tagName}`,
        date:        dateStr,
        dateISO:     rel.publishedAt || dateStr + "T00:00:00Z",
        projectName: rel.entryName,
        projectId:   rel.entryId,
        affiliation: rel.affiliation || "",
        label:       rel.tagName,
      });
    }

    // Sort all items newest-first
    items.sort((a, b) => (a.dateISO < b.dateISO ? 1 : a.dateISO > b.dateISO ? -1 : 0));
    return items;
  });

  // Extract "YYYY-MM" from a "YYYY-MM-DD" (or "YYYY-MM") date string.
  // Used on the Planet Tenstorrent page to group items by month without the
  // ellipsis that the truncate filter appends.
  eleventyConfig.addFilter("monthKey", (dateStr) => {
    if (!dateStr) return "";
    return String(dateStr).slice(0, 7);
  });

  // Convert a "YYYY-MM" or "YYYY-MM-DD" date string to a human-readable month
  // label such as "May 2026".  Returns an empty string for falsy input.
  eleventyConfig.addFilter("monthLabel", (dateStr) => {
    if (!dateStr) return "";
    const months = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"];
    // Accept "YYYY-MM" or "YYYY-MM-DD"
    const parts = String(dateStr).split("-");
    if (parts.length < 2) return dateStr;
    const month = parseInt(parts[1], 10) - 1;
    const year = parts[0];
    if (month < 0 || month > 11) return dateStr;
    return `${months[month]} ${year}`;
  });

  // Count items of a given type in a planetItems array. Used by the planet
  // sidebar instead of selectattr, which doesn't filter reliably in Eleventy's Nunjucks.
  eleventyConfig.addFilter("planetCount", (items, type) =>
    (items || []).filter((i) => i.type === type).length
  );

  // Inline a file's content directly into the template.
  // Used to embed CSS and JS into the HTML so that private GitHub Pages
  // authentication doesn't intercept sub-resource requests and return an
  // HTML auth page instead of the actual CSS/JS (which causes the browser
  // to ignore the stylesheet and leaves the page unstyled).
  eleventyConfig.addShortcode("inlineFile", (filePath) =>
    fs.readFileSync(path.join(__dirname, filePath), "utf-8")
  );

  return {
    pathPrefix: "/tt-awesome/",
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
  };
};
