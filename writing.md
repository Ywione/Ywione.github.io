---
title: Writing
permalink: /writing/
---
I publish articles on [Substack]({{ site.substack_url }}).

{% assign posts = site.data.substack.posts %}
{% if posts and posts.size > 0 %}
{% for p in posts %}
<article class="publication">
<h2><a href="{{ p.link | escape }}">{{ p.title | escape }}</a></h2>
{% if p.date %}<p class="meta">{{ p.date | date: '%-d %B %Y' }}</p>{% endif %}
{% if p.summary != "" %}<p>{{ p.summary | escape }}</p>{% endif %}
<p><a href="{{ p.link | escape }}">Read on Substack</a></p>
</article>
{% endfor %}
{% else %}
<p>No articles have been published yet.</p>
{% endif %}

<p class="small-note">This list is updated daily. The full archive is on <a href="{{ site.substack_url }}">Substack</a>.</p>
