# NDE Community Crawler

An agentic system for discovering community forum posts that the [NIAID Data Ecosystem (NDE)](https://data.niaid.nih.gov) can help answer, and for drafting contextually relevant replies.

## Background

The NIAID Data Ecosystem (NDE) is a portal that aggregates and integrates dataset metadata for infectious and immune-related diseases. It enables researchers to search across dozens of repositories — including NCBI, ImmPort, ClinicalTrials.gov, and others — through a single unified interface.

As part of the NDE outreach strategy, the team periodically monitors community forums such as [SEQanswers](http://seqanswers.com), [Biostars](https://www.biostars.org), and similar platforms for questions where NDE could provide value: pointing users to relevant datasets, explaining NDE search capabilities, or connecting researchers to resources they may not know exist.

This process is currently manual: someone reads through recent posts, judges relevance, and composes a reply. It is time-consuming and inconsistent.

## Goal

This repository explores **agentic approaches** to automate or semi-automate that workflow:

1. **Discovery** — periodically crawl target forums for new posts; score relevance to NDE's scope (infectious disease, immunology, dataset discovery, multi-repository search)
2. **Triage** — surface high-value posts that warrant a response, filtering out noise
3. **Drafting** — generate contextually appropriate draft replies that explain how NDE can help and link to relevant resources
4. **Review** — present drafts to a human reviewer before any reply is posted

## Target Forums

| Forum | Notes |
|---|---|
| [Biostars](https://www.biostars.org) | Broad bioinformatics Q&A |
| [SEQanswers](http://seqanswers.com) | Sequencing-focused discussion |
| [Reddit r/bioinformatics](https://www.reddit.com/r/bioinformatics/) | General bioinformatics community |

Additional sources (Twitter/X, Bluesky, mailing lists) may be added as the project matures.

## Approach

The system is designed around an LLM agent loop:

```
crawl forums → extract posts → score relevance → draft reply → human review
```

Relevance scoring considers whether a post is asking about:
- Finding datasets for a specific disease, pathogen, or condition
- Multi-repository or cross-database dataset search
- Infectious disease or immune-related research data
- Metadata standards (schema.org, Dataset schema) in biomedical contexts

Draft replies are grounded in NDE documentation and search capabilities, and are always reviewed by a human before posting.

## Status

Early exploration. No production deployment yet.

## Related Resources

- NDE portal: https://data.niaid.nih.gov
- NDE documentation: https://discovery.biothings.io/niaid
- NIAID: https://www.niaid.nih.gov
