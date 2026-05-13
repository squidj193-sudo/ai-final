# PRD: AI Research Assistant Agent

## 1. Project Overview
The **AI Research Assistant Agent** is an intelligent system designed to streamline the academic research process. It assists users in discovering papers via keyword search, analyzing uploaded literature, generating comparison matrices, and suggesting potential research directions based on a specialized "Role State" (Large/Medium/Small research directions).

## 2. Target Audience & Pain Points
### Target Users
- PhD and Master's students.
- Undergraduate students working on senior projects.
- Researchers exploring new fields.

### Key Pain Points
1. **Information Overload**: Difficulty in keeping up with the vast number of papers.
2. **Organization Effort**: Manual creation of literature comparison matrices is tedious and error-prone.
3. **Research Gap Discovery**: Hard for beginners to identify actionable research problems from existing literature.
4. **Scope Management**: Difficulty in narrowing down search results from broad topics to specific research questions.

## 3. Product Goals & Success Metrics
- **Efficiency**: Reduce time spent on initial literature review by at least 50%.
- **Accuracy**: Ensure AI-generated summaries and comparison tables faithfully represent the source material.
- **Guidance**: Provide structured research suggestions that align with the user's defined research scope.

## 4. Core Workflows

### Workflow A: Discovery (Keyword-based)
1. User defines **Role State** (e.g., "Optoelectronics" -> "Solar Cells" -> "Perovskite").
2. User enters search keywords.
3. Agent uses `search_papers` tool, filtered by the defined directions.
4. Agent returns a list of papers with summaries.

### Workflow B: Deep Analysis (Upload-based)
1. User uploads one or more PDF papers.
2. Agent uses `parse_paper` (via MarkItDown) to convert PDFs to Markdown.
3. Agent uses `summarize_paper` to generate structured summaries.
4. User requests a comparison.
5. Agent uses `build_literature_matrix` to generate a Markdown table comparing methods, findings, and limitations.

### Workflow C: Research Suggestion
1. Agent analyzes the comparison matrix and existing summaries.
2. Agent identifies "Research Gaps" (e.g., missing experimental verification, specific environmental conditions).
3. Agent uses `analyze_directions` to suggest 3-5 feasible research topics.

## 5. Functional Requirements (Skill Modules)

| Skill Module | Description | Key Responsibilities |
| :--- | :--- | :--- |
| **Paper Search** | Academic search integration | Call APIs (Semantic Scholar, arXiv), filter by role state, return metadata. |
| **Literature Analysis** | Document processing | PDF-to-MD conversion, structured summarization, RAG ingestion. |
| **Literature Matrix** | Comparative synthesis | Aggregate multiple summaries into a structured comparison table. |
| **Direction Analysis** | Strategic guidance | Identify gaps in the matrix and propose research directions. |
| **Role State Management**| Context persistence | Maintain user's hierarchical research focus (Large/Medium/Small). |

## 6. Technical Architecture
The system follows a **Multi-Skill Single Agent Architecture**.

- **Agent Core**: LLM-driven orchestrator that interprets user intent and selects the appropriate skill/tool.
- **Tools**: Atomic functions for searching, parsing, and analyzing.
- **RAG System**: 
    - **Parsing**: MarkItDown for high-fidelity MD conversion.
    - **Storage**: Vector Database (e.g., ChromaDB) for semantic retrieval of paper segments.
    - **Context**: Retrieved chunks are injected into LLM prompts for grounded answering.

## 7. UI/UX Design Specifications
- **Main Chat Interface**: Persistent sidebar for "Conversations", central chat area with support for PDF uploads.
- **Summary Cards**: Visual components for displaying paper summaries with quick actions (e.g., "Add to Comparison").
- **Matrix View**: A dedicated table-focused view for comparing multiple papers, supporting export to Markdown/CSV.
- **Direction Report**: A structured report page for research suggestions with tree diagrams showing the field hierarchy.

## 8. Data & Privacy Strategy
- **Source Attribution**: Every claim in summaries or matrices must be linked to a specific paper (Title, DOI, Authors).
- **Format**: All internal data exchange should use JSON; user-facing reports use Markdown.

## 9. Future Roadmap
- Integration with reference managers (Zotero, Mendeley).
- Collaborative research workspaces for lab groups.
- Automated citation generation in multiple styles.
