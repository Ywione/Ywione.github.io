---
title: Writing
permalink: /writing/
eyebrow: Essays & reflections
intro: Writing on economics, published on Substack.
---
{% assign posts = site.data.substack.posts %}
{% if posts and posts.size > 0 %}
<div class="research-list">
{% for p in posts %}
<article class="publication"><p class="meta">{% if p.date %}{{ p.date | date: '%-d %B %Y' }} · {% endif %}Substack</p><h2><a href="{{ p.link | escape }}">{{ p.title | escape }}</a></h2>{% if p.summary != "" %}<p>{{ p.summary | escape }}</p>{% endif %}<a class="text-link" href="{{ p.link | escape }}">Read on Substack <span aria-hidden="true">↗</span></a></article>
{% endfor %}
</div>
{% else %}
<section class="empty-state"><p class="eyebrow">A new chapter</p><h2>First article coming soon.</h2><p>My latest articles will appear here once published. You can subscribe on Substack to receive new writing by email.</p><a class="button" href="{{ site.substack_url }}">Visit my Substack <span aria-hidden="true">↗</span></a></section>
{% endif %}

<p class="small-note">This page checks for new articles daily. The full archive is on <a href="{{ site.substack_url }}">Substack</a>.</p>
