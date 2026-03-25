const IMAGE_EXT_RE = /\.(png|jpe?g|gif|webp|bmp|svg)(?:[?#][^\s"')>]*)?$/i;

function safeDecode(value) {
  try {
    return decodeURIComponent(value);
  } catch (_err) {
    return value;
  }
}

export function normalizeMalformedLocalHost(value) {
  if (!value) return "";
  let out = safeDecode(String(value).trim());

  // Normalize broken absolute URLs like https://app/tmp/... or https://korev/tmp/...
  out = out.replace(/^https?:\/\/(?:app|korev|a0)(?=\/)/i, "");

  // Normalize file URLs pointing to local container prefixes.
  out = out.replace(/^file:\/\/\/?(?:app|korev|a0)\//i, "/");
  out = out.replace(/^file:\/\//i, "/");

  return out;
}

export function extractInternalPathFromHref(href) {
  if (!href) return null;
  const normalized = normalizeMalformedLocalHost(href);

  // Never rewrite real external hosts.
  if (/^https?:\/\//i.test(normalized)) return null;

  const match = normalized.match(
    /^(?:\/)?(?:app\/|korev\/|a0\/)?(tmp\/(?:generated|uploads|generated_images)\/[^\s?#]+|shared\/[^\s?#]+)/i
  );
  return match ? match[1] : null;
}

function toImageGetPath(localPath) {
  const clean = localPath.replace(/^\/+/, "");
  return `/image_get?path=${clean}`;
}

export function rewriteInlineImagePaths(input) {
  if (typeof input !== "string" || !input) return input;
  let out = input;

  // Normalize broken local-host URLs first so markdown/image src gets fixed.
  out = out.replace(/https?:\/\/(?:app|korev|a0)(?=\/)/gi, "");
  out = out.replace(/file:\/\/\/?(?:app|korev|a0)\//gi, "/");

  // Convert img:// and sandbox:// internal schemes.
  out = out.replace(/img:\/\/\/?/g, "/image_get?path=");
  out = out.replace(/sandbox:\/\/\/?/g, "/image_get?path=");

  // Route local image paths through image_get for robust serving.
  out = out.replace(
    /(?:\/(?:app|korev|a0))?\/(tmp\/(?:generated_images|generated|uploads)\/[^\s"')>]+)/gi,
    (full, p1) => (IMAGE_EXT_RE.test(p1) ? toImageGetPath(p1) : full)
  );

  // Clean duplicate slashes in image_get path parameter.
  out = out.replace(/(\/image_get\?path=)\/+/g, "$1");

  return out;
}

