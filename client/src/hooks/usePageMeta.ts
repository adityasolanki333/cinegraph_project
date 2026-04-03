import { useEffect } from "react";

interface PageMetaOptions {
  title: string;
  description?: string;
  ogTitle?: string;
  ogDescription?: string;
  ogImage?: string;
  ogType?: string;
}

function setMetaTag(property: string, content: string, isOg = false) {
  const attr = isOg ? "property" : "name";
  let tag = document.querySelector(`meta[${attr}="${property}"]`);
  if (!tag) {
    tag = document.createElement("meta");
    tag.setAttribute(attr, property);
    document.head.appendChild(tag);
  }
  tag.setAttribute("content", content);
}

function removeMetaTag(property: string, isOg = false) {
  const attr = isOg ? "property" : "name";
  const tag = document.querySelector(`meta[${attr}="${property}"]`);
  if (tag) {
    tag.remove();
  }
}

export function usePageMeta({
  title,
  description,
  ogTitle,
  ogDescription,
  ogImage,
  ogType = "website",
}: PageMetaOptions) {
  useEffect(() => {
    const fullTitle = title ? `${title} | CineGraph` : "CineGraph";
    document.title = fullTitle;

    if (description) {
      setMetaTag("description", description);
    }

    setMetaTag("og:title", ogTitle || title || "CineGraph", true);
    setMetaTag("og:type", ogType, true);

    if (ogDescription || description) {
      setMetaTag("og:description", ogDescription || description || "", true);
    }

    if (ogImage) {
      setMetaTag("og:image", ogImage, true);
    } else {
      removeMetaTag("og:image", true);
    }

    return () => {
      document.title = "CineGraph";
    };
  }, [title, description, ogTitle, ogDescription, ogImage, ogType]);
}
