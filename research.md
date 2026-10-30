---
title: Research
permalink: /research/
eyebrow: Questions & connections
intro: Inequality, small island economies and international finance.
---
{% assign items = site.research | sort: 'date' | reverse %}
{% if items.size > 0 %}
<div class="research-list">
{% for r in items %}
<article class="publication"><p class="meta">{% if r.status %}{{ r.status | escape }} · {% endif %}{{ r.date | date: '%B %Y' }}</p><h2><a href="{{ r.url | relative_url }}">{{ r.title | escape }}</a></h2>{% if r.coauthors %}<p class="meta">With {{ r.coauthors | escape }}</p>{% endif %}{% if r.abstract %}<p>{{ r.abstract | escape }}</p>{% endif %}<a class="text-link" href="{{ r.url | relative_url }}">Read more <span aria-hidden="true">→</span></a></article>
{% endfor %}
</div>
{% else %}
<section class="empty-state"><p class="eyebrow">Research archive</p><h2>Papers & projects</h2><p>Research papers and projects will be added here as they become available.</p></section>
{% endif %}

## Research interests

My interests include income inequality, small island developing states, offshore financial centres, Dutch Disease, cross-border financial flows and firm dynamics.

For shorter pieces, visit [Writing]({{ '/writing/' | relative_url }}).
