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
