---
title: Datasets
permalink: /datasets/
description: Bermuda datasets compiled by Ywione Darrell, with downloads in Excel and CSV formats.
---
This page brings together my datasets on Bermuda, with Excel and CSV downloads where available.

{% assign datasets = site.datasets | sort: 'title' %}
{% if datasets.size > 0 %}
{% for dataset in datasets %}
<section class="publication" aria-labelledby="dataset-{{ forloop.index }}">
<h2 id="dataset-{{ forloop.index }}">{{ dataset.title | escape }}</h2>
{% if dataset.description %}<p>{{ dataset.description | escape }}</p>{% endif %}
{% if dataset.coverage or dataset.frequency or dataset.updated %}
<p class="meta">{% if dataset.coverage %}Coverage: {{ dataset.coverage | escape }}{% endif %}{% if dataset.frequency %}{% if dataset.coverage %} · {% endif %}Frequency: {{ dataset.frequency | escape }}{% endif %}{% if dataset.updated %}{% if dataset.coverage or dataset.frequency %} · {% endif %}Updated: {{ dataset.updated | date: '%-d %B %Y' }}{% endif %}</p>
{% endif %}
{% if dataset.excel and dataset.excel != '' or dataset.csv and dataset.csv != '' %}
<p>{% if dataset.excel and dataset.excel != '' %}<a href="{{ dataset.excel | relative_url | escape }}" download>Download Excel</a>{% endif %}{% if dataset.csv and dataset.csv != '' %}{% if dataset.excel and dataset.excel != '' %} · {% endif %}<a href="{{ dataset.csv | relative_url | escape }}" download>Download CSV</a>{% endif %}</p>
{% endif %}
{% if dataset.source_name and dataset.source_name != '' %}<p class="meta">Source: {% if dataset.source_url and dataset.source_url != '' %}<a href="{{ dataset.source_url | escape }}">{{ dataset.source_name | escape }}</a>{% else %}{{ dataset.source_name | escape }}{% endif %}</p>{% endif %}
{{ dataset.content | markdownify }}
{% if dataset.citation and dataset.citation != '' %}<p><strong>Suggested citation:</strong> {{ dataset.citation | escape }}</p>{% endif %}
{% if dataset.license and dataset.license != '' %}<p class="small-note">Reuse: {{ dataset.license | escape }}</p>{% endif %}
</section>
{% endfor %}
{% else %}
<p>Datasets will be listed here as they become available.</p>
{% endif %}
