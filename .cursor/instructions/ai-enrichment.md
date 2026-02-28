# AI Lead Enrichment Service

## Overview
This service enriches lead data using AI (OpenAI/Codex, Claude, or local LLMs). It adds:
- Company size estimation
- Revenue range prediction
- Industry classification
- Pain point identification
- Outreach angle suggestions

## Integration Points
1. **During lead generation**: Enrich each lead after scraping
2. **Batch processing**: Enrich existing leads in bulk
3. **On-demand**: Enrich single lead via API

## Data Flow
```
Raw Lead (from Google Places) 
  → Standardization 
  → AI Enrichment (parallel: size, industry, pain points)
  → Combined Enrichment Object
  → Store in PostgreSQL (JSONB column)
```

## API Design
```python
POST /api/v1/leads/{lead_id}/enrich
GET /api/v1/leads/{lead_id}/enrichment
POST /api/v1/jobs/{job_id}/enrich-all
```

## Enrichment Prompts

### Company Size Estimation
```
Estimate company size for {business_name} in {industry} located in {city}, {state}.

Consider:
- Industry benchmarks
- Location factors
- Online presence indicators
- Review count ({review_count}) as proxy for customer base

Return: {"size_range": "1-10|11-50|51-200|201-500|501-1000|1000+", "confidence": 0.85}
```

### Revenue Estimation
```
Estimate annual revenue for {business_name} in {industry}.

Consider:
- Industry average revenue per employee
- Company size estimate
- Location cost factors
- Online reviews as engagement proxy

Return: {"revenue_range": "0-1M|1M-5M|5M-10M|10M-50M|50M+", "confidence": 0.80}
```

### Pain Point Identification
```
Identify likely pain points for {business_name} in {industry}.

Consider:
- Common challenges in this industry
- Business size implications
- Location-specific issues
- Online presence gaps

Return: {"pain_points": ["list", "of", "3-5", "pain points"], "confidence": 0.75}
```

### Outreach Angle
```
Suggest personalized outreach angle for {business_name}.

Consider:
- Company size
- Industry
- Pain points
- Location

Return: {"angle": "personalized outreach suggestion", "confidence": 0.80}
```

## Implementation Notes
- Cache AI responses in Redis (24h TTL) to reduce costs
- Implement retry logic with exponential backoff for API failures
- Use streaming responses for better UX
- Log enrichment performance metrics (latency, cost, success rate)
- A/B test different prompt templates