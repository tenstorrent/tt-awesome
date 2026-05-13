const fs = require("fs");
const path = require("path");

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addPassthroughCopy({ ".nojekyll": ".nojekyll" });

  eleventyConfig.addFilter("truncate", (str, len) =>
    str && str.length > len ? str.slice(0, len) + "…" : str
  );

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

  // Inline a file's content directly into the template.
  // Used to embed CSS and JS into the HTML so that private GitHub Pages
  // authentication doesn't intercept sub-resource requests and return an
  // HTML auth page instead of the actual CSS/JS (which causes the browser
  // to ignore the stylesheet and leaves the page unstyled).
  eleventyConfig.addShortcode("inlineFile", (filePath) =>
    fs.readFileSync(path.join(__dirname, filePath), "utf-8")
  );

  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
  };
};
