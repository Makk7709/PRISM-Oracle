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
  out = out.replace(/^\/(?:app|korev|a0)\/+(?=tmp\/)/i, "/");

  return out;
}

export function extractInternalPathFromHref(href) {
  if (!href) return null;
  const normalized = normalizeMalformedLocalHost(href);

  // Never rewrite real external hosts.
  if (/^https?:\/\//i.test(normalized)) return null;

  // Support links produced as /download_work_dir_file?path=<internal-path>.
  // We convert them back to the underlying internal path for openFileLink().
  const downloadMatch = normalized.match(
    /^\/?download_work_dir_file\?path=([^&]+)/i
  );
  if (downloadMatch) {
    const raw = safeDecode(downloadMatch[1] || "").replace(/^\/+/, "");
    return raw || null;
  }

  const match = normalized.match(
    /^(?:\/)?(?:app\/+|korev\/+|a0\/+)?((?:tmp\/(?:generated|uploads|generated_images)|shared|reports|generated|work_dir)\/[^\s?#]+)/i
  );
  if (match) return match[1];

  // Catch any remaining internal PDF/document path the AI might generate.
  // If the href is a local path (starts with /) ending in a known doc extension
  // and not an external URL, treat it as an internal file link.
  const docPathMatch = normalized.match(
    /^(?:\/)?(?:app\/+|korev\/+|a0\/+)?([^\s?#]+\.(?:pdf|docx?|xlsx?|csv|pptx?|zip|odt|rtf|txt|md))$/i
  );
  if (docPathMatch) return docPathMatch[1];

  return null;
}

function toImageGetPath(localPath) {
  const clean = localPath.replace(/^\/+/, "");
  return `/image_get?path=${clean}`;
}

export function rewriteInlineImagePaths(input) {
  if (typeof input !== "string" || !input) return input;
  let out = input;

  // Normalize broken local-host URLs first so markdown/image src gets fixed.
  out = out.replaceAll(/https?:\/\/(?:app|korev|a0)(?=\/)/gi, "");
  out = out.replaceAll(/file:\/\/\/?(?:app|korev|a0)\//gi, "/");

  // Convert img:// and sandbox:// internal schemes.
  out = out.replaceAll(/img:\/\/\/?/g, "/image_get?path=");
  out = out.replaceAll(/sandbox:\/\/\/?/g, "/image_get?path=");

  // Route local image paths through image_get for robust serving.
  out = out.replaceAll(
    /(^|[\s('"`>])(?:\/(?:app|korev|a0))?\/+(tmp\/(?:generated_images|generated|uploads)\/[^\s"')>]+)/gi,
    (full, prefix, p1) => (IMAGE_EXT_RE.test(p1) ? `${prefix}${toImageGetPath(p1)}` : full)
  );

  // Clean duplicate slashes in image_get path parameter.
  out = out.replaceAll(/(\/image_get\?path=)\/+/g, "$1");

  return out;
}

