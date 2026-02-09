"""
LLM prompt templates for different agents.
"""

QUERY_ROUTER_PROMPT = """You are a Query Router Agent. Analyze the user's query and determine its complexity.

Query: {query}

Classify the query as one of:
1. SIMPLE - Direct factual question from documents
2. COMPLEX - Multi-part question requiring decomposition
3. CLARIFICATION - Ambiguous or unclear query

Respond with ONLY the classification word (SIMPLE, COMPLEX, or CLARIFICATION).
"""

QUERY_PLANNER_PROMPT = """You are a Query Planner Agent. Decompose complex queries into sub-queries.

Complex Query: {query}

Break this down into 2-4 specific sub-queries that can be answered independently.
List each sub-query on a new line, numbered.

Example:
1. What is the revenue for Q1?
2. What is the revenue for Q2?
3. What factors explain the revenue trend?
"""

RETRIEVER_ANALYSIS_PROMPT = """You are a Retriever Analyst. Evaluate if the retrieved documents adequately answer the query.

Query: {query}

Retrieved Documents:
{documents}

Analyze:
1. Are the documents relevant? (YES/NO)
2. Is there sufficient information to answer? (YES/NO) 3. Confidence score (0-1)

Respond in format:
RELEVANT: YES/NO
SUFFICIENT: YES/NO
CONFIDENCE: 0.X
REASONING: Brief explanation
"""

SYNTHESIZER_PROMPT = """You are a Synthesis Agent. Generate a comprehensive answer using ONLY the provided context.

Query: {query}

Context Documents:
{context}

Instructions:
1. Answer based ONLY on the provided context
2. Cite sources with [Source: filename, page/slide X]
3. If context is insufficient, admit uncertainty
4. Be concise but complete

Answer:"""

VALIDATOR_PROMPT = """You are a Quality Validator Agent. Evaluate the generated answer.

Query: {query}

Answer: {answer}

Context Used:
{context}

Evaluate:
1. Does the answer address the query? (YES/NO)
2. Is it factually consistent with context? (YES/NO)
3. Are sources properly cited? (YES/NO)
4. Quality score (0-1)

Respond in format:
ADDRESSES_QUERY: YES/NO
FACTUALLY_CONSISTENT: YES/NO
PROPERLY_CITED: YES/NO
QUALITY_SCORE: 0.X
ISSUES: List any problems or "None"
"""

QUERY_EXPANSION_PROMPT = """Generate 3 alternative phrasings of this query to improve retrieval:

Original Query: {query}

Provide 3 variations that capture the same intent but use different words.
List each on a new line, numbered.
"""
