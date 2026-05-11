module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addPassthroughCopy({ ".nojekyll": ".nojekyll" });
  eleventyConfig.addFilter("truncate", (str, len) =>
    str && str.length > len ? str.slice(0, len) + "…" : str
  );
  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
  };
};
