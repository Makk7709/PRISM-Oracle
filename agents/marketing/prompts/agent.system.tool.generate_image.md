### generate_image:
create images and visual content using AI image generation
use this tool whenever user requests:
- image generation
- visual creation
- illustrations
- marketing visuals
- logos
- banners
- social media graphics
- product mockups
- moodboards

IMPORTANT: for any visual/image request you MUST use this tool
do NOT respond with text only when image is requested
the system will automatically select the best available provider

arguments:
- prompt (string, required): detailed description of the image to generate
  - be specific about style, colors, composition, mood
  - include relevant details for the intended use
- size (string, optional): "1024x1024" | "1792x1024" | "1024x1792"
  - 1024x1024 = square (default, social media posts)
  - 1792x1024 = landscape (banners, headers)
  - 1024x1792 = portrait (stories, mobile)
- quality (string, optional): "standard" | "hd"
  - standard = faster, good for drafts
  - hd = better quality, final assets
- n (int, optional): number of images to generate (default 1, max 4)
- style (string, optional): "vivid" | "natural"
  - vivid = hyper-real, dramatic (marketing)
  - natural = realistic, subtle
- purpose (string, optional): context for the image
  - "marketing" | "branding" | "product" | "social" | "presentation" | "illustration"

response format:
- status: "success" | "error"
- provider: which provider was used
- images: array of image URLs or base64
- fallback_used: true if primary provider failed

**CRITICAL: AFTER IMAGE GENERATION**
Once generate_image returns successfully:
1. The image is ALREADY displayed in the chat (no need to show it again)
2. Use the `response` tool to confirm completion to the user
3. Do NOT call any other tools - the task is complete

Example after successful generation:
~~~json
{
    "thoughts": [
        "Image was generated successfully",
        "I should confirm to the user and end the task"
    ],
    "headline": "Image delivered",
    "tool_name": "response",
    "tool_args": {
        "text": "Voici votre image ! Si vous souhaitez des modifications, n'hésitez pas à demander."
    }
}
~~~

usage example 1 - marketing visual:
~~~json
{
    "thoughts": [
        "User needs a marketing visual for social media",
        "Should use vibrant style for engagement",
        "Square format optimal for feed posts"
    ],
    "headline": "Generating marketing visual",
    "tool_name": "generate_image",
    "tool_args": {
        "prompt": "Modern minimalist product showcase, sleek smartphone on marble surface, soft natural lighting, premium feel, clean white background with subtle shadows, professional product photography style",
        "size": "1024x1024",
        "quality": "hd",
        "style": "vivid",
        "purpose": "marketing"
    }
}
~~~

usage example 2 - banner:
~~~json
{
    "thoughts": [
        "User needs a LinkedIn banner",
        "Landscape format required",
        "Professional branding style"
    ],
    "headline": "Creating LinkedIn banner",
    "tool_name": "generate_image",
    "tool_args": {
        "prompt": "Professional business banner, abstract geometric shapes in blue and purple gradient, modern corporate design, clean lines, suitable for LinkedIn header, subtle tech elements",
        "size": "1792x1024",
        "quality": "hd",
        "style": "natural",
        "purpose": "branding"
    }
}
~~~

usage example 3 - illustration:
~~~json
{
    "thoughts": [
        "User wants an illustration for a blog post",
        "Should be engaging but professional"
    ],
    "headline": "Generating blog illustration",
    "tool_name": "generate_image",
    "tool_args": {
        "prompt": "Isometric illustration of a person working at a desk with multiple screens, warm color palette, flat design style, productivity and focus theme, soft shadows",
        "size": "1792x1024",
        "quality": "standard",
        "purpose": "illustration"
    }
}
~~~

trigger keywords (use tool when user mentions):
- "crée un visuel", "génère une image", "fais une image"
- "create image", "generate visual", "make a picture"
- "design", "illustration", "logo", "banner", "graphic"
- "visuel marketing", "post linkedin", "social media graphic"
- "moodboard", "mockup", "thumbnail"
