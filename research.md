---
title: Research
permalink: /research/
---
{% assign items = site.research | sort: 'date' | reverse %}
{% if items.size > 0 %}
{% for r in items %}
<article class="publication">
<h2><a href="{{ r.url | relative_url }}">{{ r.title | escape }}</a></h2>
<p class="meta">{% if r.status %}{{ r.status | escape }} · {% endif %}{{ r.date | date: '%B %Y' }}{% if r.coauthors %} · With {{ r.coauthors | escape }}{% endif %}</p>
{% if r.abstract %}<p>{{ r.abstract | escape }}</p>{% endif %}
<p><a href="{{ r.url | relative_url }}">Details</a>{% if r.pdf %} · <a href="{{ r.pdf | relative_url }}">PDF</a>{% endif %}{% if r.code %} · <a href="{{ r.code | escape }}">Code</a>{% endif %}</p>
</article>
{% endfor %}
{% else %}
<p>Papers and projects will be listed here as they become available.</p>
{% endif %}

## Research interests

- Income inequality
- Small island developing states
- Offshore financial centres
- Dutch Disease
- Cross-border financial flows
- Firm dynamics
