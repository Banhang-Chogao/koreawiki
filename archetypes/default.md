---
title: "{{ replace .Name "-" " " | title }}"
description: ""
keywords: []
date: {{ .Date }}
lastmod: {{ .Date }}
draft: true
author: "KoreaWiki Newsroom"
tags: []
categories: []
slug: ""
cover:
  image: ""
  alt: ""
  caption: ""
# Required: powers "Bài này trả lời" under the title + FAQ anchors (#faq-1…)
faq:
  - q: "Bài viết này nói về chủ đề gì?"
    a: "Tóm tắt 1–2 câu dựa trên nội dung bài (không bịa fact)."
  - q: "Điểm thông tin chính độc giả nên nhớ là gì?"
    a: "1–2 câu then chốt từ body."
---

Nội dung bài viết…

{{/* REQUIRED at end of every article — source, links, copyright; FAQ from front matter */}}
{{< article-footer >}}
source: ""
source_url: ""
copyright: >
  Ghi nguồn / bản quyền. Không bịa.
external: []
internal: []
{{< /article-footer >}}
