import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js";
import hljs from "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/es/highlight.min.js";

export function renderMarkdown(text) {
  const html = marked.parse(text, { breaks: true, gfm: true });
  const temp = document.createElement("div");
  temp.innerHTML = html;
  temp.querySelectorAll("pre code").forEach((block) => {
    hljs.highlightElement(block);
  });
  return temp.innerHTML;
}
