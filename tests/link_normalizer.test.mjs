import test from "node:test";
import assert from "node:assert/strict";

import {
  extractInternalPathFromHref,
  rewriteInlineImagePaths,
} from "../webui/js/link-normalizer.mjs";

test("extractInternalPathFromHref handles malformed app host", () => {
  const path = extractInternalPathFromHref(
    "https://app/tmp/generated_images/facture.png"
  );
  assert.equal(path, "tmp/generated_images/facture.png");
});

test("extractInternalPathFromHref handles file scheme with legacy prefix", () => {
  const path = extractInternalPathFromHref(
    "file:///korev/tmp/generated/render-final.png"
  );
  assert.equal(path, "tmp/generated/render-final.png");
});

test("extractInternalPathFromHref ignores real external domains", () => {
  const path = extractInternalPathFromHref(
    "https://example.com/tmp/generated_images/x.png"
  );
  assert.equal(path, null);
});

test("rewriteInlineImagePaths rewrites malformed app-host markdown image URLs", () => {
  const input = "![Image](https://app/tmp/generated_images/final.png)";
  const out = rewriteInlineImagePaths(input);
  assert.equal(out, "![Image](/image_get?path=tmp/generated_images/final.png)");
});

test("rewriteInlineImagePaths rewrites legacy local container paths", () => {
  const input = "![Out](/korev/tmp/generated/a/b/c-logo.webp)";
  const out = rewriteInlineImagePaths(input);
  assert.equal(out, "![Out](/image_get?path=tmp/generated/a/b/c-logo.webp)");
});

test("rewriteInlineImagePaths keeps external image URLs unchanged", () => {
  const input = "![Logo](https://korev.ai/assets/logo.png)";
  const out = rewriteInlineImagePaths(input);
  assert.equal(out, input);
});

test("rewriteInlineImagePaths converts img scheme to image_get", () => {
  const input = "![Img](img://tmp/generated_images/x.png)";
  const out = rewriteInlineImagePaths(input);
  assert.equal(out, "![Img](/image_get?path=tmp/generated_images/x.png)");
});

test("rewriteInlineImagePaths converts sandbox scheme to image_get", () => {
  const input = "![Img](sandbox://tmp/uploads/photo.jpeg)";
  const out = rewriteInlineImagePaths(input);
  assert.equal(out, "![Img](/image_get?path=tmp/uploads/photo.jpeg)");
});

test("extractInternalPathFromHref supports uppercase malformed host", () => {
  const path = extractInternalPathFromHref(
    "HTTPS://KOREV/tmp/uploads/scan-01.png"
  );
  assert.equal(path, "tmp/uploads/scan-01.png");
});

test("extractInternalPathFromHref supports encoded href content", () => {
  const path = extractInternalPathFromHref(
    "https%3A%2F%2Fapp%2Ftmp%2Fgenerated_images%2Fnote%25201.png"
  );
  assert.equal(path, "tmp/generated_images/note%201.png");
});

