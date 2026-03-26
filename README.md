# ContextGraph — Supply Chain Intelligence

> LLM-powered context graph system with natural language query interface for SAP Order-to-Cash business data.

**Live Frontend:** [https://dodgeai-wtxr.onrender.com/](https://dodgeai-wtxr.onrender.com/)
**Live Backend API:** [https://dodgeai-yh1n.onrender.com/](https://dodgeai-yh1n.onrender.com/)---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack & Justification](#tech-stack--justification)
- [Database Design](#database-design)
- [Graph Modelling](#graph-modelling)
- [LLM Prompting Strategy](#llm-prompting-strategy)
- [Guardrails](#guardrails)
- [Bonus Extensions](#bonus-extensions)
- [Setup & Running](#setup--running)
- [API Reference](#api-reference)
- [AI Session Logs](#ai-session-logs)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                      Frontend                            │
│    React 19 + Vite 6 + Tailwind CSS v4 + React Flow     │
│   ┌──────────────┐ ┌──────────────┐ ┌───────────────┐   │
│   │  GraphView   │ │  ChatPanel   │ │  NodeDrawer   │   │
│   │ (React Flow) │ │ (Dark theme) │ │ (Tooltip card)│   │
│   └──────┬───────┘ └──────┬───────┘ └───────────────┘   │
└──────────┼────────────────┼──────────────────────────────┘
           │                │
    GET /api/graph     POST /api/chat
           │                │
┌──────────┼────────────────┼──────────────────────────────┐
│          │     FastAPI Backend                            │
│   ┌──────▼──────┐  ┌──────▼───────┐  ┌───────────────┐  │
│   │  Graph API  │  │ LLM Pipeline │  │  Flow Tracer  │  │
│   │ (graph.py)  │  │  (llm.py)    │  │  (flows.py)   │  │
│   └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│          └────────────────┼──────────────────┘           │
│                    ┌──────▼───────┐                      │
│                    │  SQLite DB   │                      │
│                    │   (WAL mode) │                      │
│                    └──────────────┘                      │
│                    ┌──────────────┐                      │
│                    │   Groq API   │                      │
│                    │ (Llama 3.1)  │                      │
│                    └──────────────┘                      │
└──────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. CSVs are parsed and loaded into SQLite on startup with FK constraints
2. The graph API constructs nodes (entities) and edges (relationships) from the relational data
3. The user types a natural language question in the chat
4. The LLM translates it into SQL, executes it safely, and returns a data-backed answer
5. Referenced entity IDs are extracted and linked back to the graph as clickable highlights

---

## Tech Stack & Justification

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 19 + Vite 6 | Fast HMR, modern JSX, optimal DX |
| **Styling** | Tailwind CSS v4 | Utility-first, rapid iteration, zero dead CSS |
| **Graph Viz** | React Flow | Built-in pan/zoom/controls, custom node types, handles 500+ nodes with virtualization |
| **Backend** | FastAPI (Python) | Async, auto OpenAPI docs, native type hints, ideal for LLM orchestration |
| **Database** | SQLite (WAL mode) | Zero-config, single-file deployment, sufficient for 1K records, FK enforcement built-in |
| **LLM** | Groq API (Llama 3.1 8B) | Free tier, ~200ms inference, excellent at structured SQL generation |
| **Logging** | Structured JSON | Machine-parseable query logs with latency tracking |

### Why SQLite over PostgreSQL?

For a dataset of ~1,000 records with read-heavy workloads, SQLite is the optimal choice:
- **Zero deployment complexity** — no separate database server needed
- **WAL mode** enables concurrent reads during LLM query execution
- **Foreign key enforcement** validates relational integrity at the DB level
- **Single-file portability** — the entire database ships with the repo

For production at scale (10K+ records, concurrent writes), migrating to PostgreSQL would be straightforward since all queries are standard SQL.

---

## Database Design

### Entity-Relationship Model

```
customers ─────┐
               │ 1:N
               ▼
            orders ──────────┬──────────┐
               │             │          │
               │ 1:N         │ 1:N      │ 1:N
               ▼             ▼          ▼
          order_items    deliveries   invoices
               │             │          │
               │ N:1         │ N:1      │ 1:N
               ▼             ▼          ▼
           products      addresses  invoice_items
                                       │
                                       │ 1:N
                                       ▼
                                    payments
```

### Tables (9 total, 1,003 records)

| Table | Records | Primary Key | Foreign Keys |
|-------|---------|-------------|--------------|
| `customers` | 50 | `id` (CUST-xxx) | — |
| `products` | 30 | `id` (PROD-xxx) | — |
| `addresses` | 75 | `id` (ADDR-xxx) | — |
| `orders` | 200 | `id` (ORD-xxx) | `customer_id → customers` |
| `order_items` | 350 | `id` (OI-xxx) | `order_id → orders`, `product_id → products` |
| `deliveries` | 180 | `id` (DEL-xxx) | `order_id → orders`, `address_id → addresses` |
| `invoices` | 160 | `id` (INV-xxx) | `order_id → orders` |
| `invoice_items` | 200 | `id` (II-xxx) | `invoice_id → invoices` |
| `payments` | 120 | `id` (PAY-xxx) | `invoice_id → invoices` |

### Performance

All foreign key columns are indexed (`CREATE INDEX`) for fast JOINs. The LLM-generated SQL queries (often 3-5 table JOINs) execute in **< 5ms**.

---

## Graph Modelling

### Nodes (Business Entities)

Each database record becomes a graph node with:
- **Unique ID** (e.g., `ORD-001`, `CUST-045`)
- **Type** (ORDER, DELIVERY, INVOICE, PAYMENT, CUSTOMER, PRODUCT)
- **Color coding** for visual differentiation
- **Metadata** (all table columns accessible on click)

### Edges (Relationships)

| Source | Target | Relationship |
|--------|--------|-------------|
| Customer | Order | `PLACED_ORDER` |
| Order | Product | `CONTAINS_PRODUCT` |
| Order | Delivery | `HAS_DELIVERY` |
| Order | Invoice | `HAS_INVOICE` |
| Invoice | Payment | `HAS_PAYMENT` |

### Layout Strategy

Nodes are placed in a **radial force-directed layout** grouped by entity type:
- Customers and Products form the outer rings
- Orders sit in the middle ring
- Deliveries, Invoices, and Payments form inner rings

This creates natural visual clusters that mirror the supply chain flow.

### Interaction

- **Click a node** → Opens a tooltip card with full metadata and connection count
- **Hover a node** → Shows the entity ID label
- **Click node chips in chat** → Highlights corresponding nodes on the graph with a pulsing glow animation

---

## LLM Prompting Strategy

### Two-Stage Text-to-SQL Pipeline

This is the core innovation of the system. Rather than asking the LLM to answer questions directly, we use a **structured two-stage pipeline**:

#### Stage 1 — SQL Generation

```
System Prompt:
  "You are a data analyst assistant for an ERP supply chain dataset.
   You ONLY answer questions about: Orders, Deliveries, Invoices,
   Payments, Customers, Products, and Addresses.
   For valid questions:
   1. Write a SQLite-compatible SQL query
   2. Wrap it in <SQL></SQL> tags
   Rules: Only SELECT statements. Never INSERT/UPDATE/DELETE/DROP."

User Context (injected automatically):
  - Full schema DDL (CREATE TABLE statements)
  - 3 sample rows per table (so the LLM understands data format)
  - User's natural language question
```

The LLM generates a SQL query. We extract it from `<SQL>` tags using regex.

#### Stage 2 — Answer Synthesis

```
System Prompt:
  "Here are the SQL results: [JSON rows]
   Write a clear, concise natural language answer.
   Reference specific entity IDs wrapped in <NODES>id1,id2</NODES> tags."
```

The LLM reads the **actual data** and formulates a grounded answer. This ensures:
- **No hallucination** — every claim is backed by query results
- **Transparency** — the SQL is visible to the user (expandable "View SQL" toggle)
- **Traceability** — entity IDs link back to the graph

### Why Two Stages?

| Approach | Pros | Cons |
|----------|------|------|
| Single-stage (direct answer) | Simpler | Can hallucinate, no auditability |
| **Two-stage (SQL → Answer)** | **Data-grounded, auditable, SQL visible** | **Two API calls (~400ms total)** |

The slight latency increase is worth the massive improvement in answer accuracy and transparency.

---

## Guardrails

### Layer 1 — Domain Keyword Filter (Pre-LLM)

Before any API call, the user query is checked against 28 domain keywords:

```python
DOMAIN_KEYWORDS = [
    "order", "delivery", "invoice", "payment", "customer", "product",
    "billing", "shipment", "material", "vendor", "plant", "flow",
    "document", "sales", "address", "amount", "total", "price",
    "tracking", "sku", "quantity", "item", "revenue", "pending",
    "overdue", "paid", "shipped", "cancelled", "supply", "chain"
]
```

**If no keywords match → immediate rejection without burning API tokens.**

Response: *"This system is designed to answer questions related to the provided dataset only."*

### Layer 2 — Read-Only SQL Enforcement

```python
# Application-level regex blocks destructive SQL
DANGEROUS_SQL_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH)",
    re.IGNORECASE
)

# Multi-statement injection prevention
if cleaned.strip().rstrip(";").count(";") > 0:
    raise ValueError("Multiple SQL statements are not allowed.")
```

### Layer 3 — SQLite Read-Only Connection

```python
uri = f"file:{DB_PATH}?mode=ro"
conn = sqlite3.connect(uri, uri=True)
```

Even if Layers 1 and 2 fail, the database connection itself is read-only at the driver level.

### Layer 4 — LLM System Prompt Constraint

The system prompt explicitly instructs the LLM to reject off-topic queries and never generate write operations.

### Test Results

| Query | Domain? | Result |
|-------|---------|--------|
| "How many orders are there?" | ✅ | SQL COUNT(*) → correct answer |
| "Which products have the most invoices?" | ✅ | Multi-table JOIN → ranked list |
| "Trace flow for order ORD-001" | ✅ | 4-table JOIN → full chain |
| "Identify broken flows" | ✅ | Broken flow detection |
| "What is the weather today?" | ❌ | Rejected at keyword filter |
| "Write me a poem" | ❌ | Rejected at keyword filter |
| "DROP TABLE orders" | ❌ | Blocked by regex + read-only DB |

---

## Bonus Extensions

### 1. Natural Language to SQL Translation (Deep)

The entire query pipeline is built around this. The generated SQL is:
- Extracted via regex from `<SQL>` tags
- Validated for safety (read-only enforcement)
- Executed against the real database
- Visible to the user via an expandable "View SQL" toggle in the chat

### 2. Highlighting Nodes Referenced in Responses

When the LLM references entity IDs (e.g., `ORD-001`, `CUST-045`):
1. IDs are extracted from `<NODES>` tags and SQL result values
2. The frontend renders them as **clickable blue chips** below the answer
3. Clicking a chip triggers a CSS `nodeGlow` animation on the graph, highlighting the exact node
4. The glow auto-fades after 5 seconds

### 3. Broken Flow Detection

The validator engine detects incomplete supply chains:
- Orders with no delivery (`DELIVERY_MISSING`)
- Orders delivered but not invoiced (`DELIVERED_NOT_BILLED`)
- Invoices with no payment (`PAYMENT_MISSING`)

These are surfaced via the "⚠ Broken Flows" button, which highlights affected nodes in red.

---

## Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API key ([free at console.groq.com](https://console.groq.com))

### Backend

```bash
cd backend
pip install -r requirements.txt
python generate_data.py          # Generate synthetic SAP data (CSVs)
cp .env.example .env             # Create environment file
# Edit .env → GROQ_API_KEY=your_key_here
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # Starts at http://localhost:5173
```

### Verify

Open http://localhost:5173 — you should see the graph with 435 nodes and 657 edges, and a dark-themed chat panel on the right.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/graph` | Full graph (all nodes + edges) |
| `GET` | `/api/node/{type}/{id}` | Single node metadata + connections |
| `GET` | `/api/flow/{order_id}` | Trace order → delivery → invoice → payment |
| `GET` | `/api/broken-flows` | All orders with incomplete chains |
| `POST` | `/api/chat` | Natural language query → SQL → answer |
| `GET` | `/api/debug/summary` | Database table counts & stats |
| `GET` | `/api/debug/logs` | Recent LLM query logs with latency |

---

## Project Structure

```
├── backend/
│   ├── main.py                # FastAPI app entry point
│   ├── db.py                  # SQLite schema, ingestion, read-only executor
│   ├── llm.py                 # Groq/Llama text-to-SQL pipeline + guardrails
│   ├── validator.py           # Broken flow detection engine
│   ├── logger.py              # Structured JSON logging
│   ├── generate_data.py       # Synthetic SAP data generator
│   ├── routes/
│   │   ├── graph.py           # Graph construction API
│   │   ├── flows.py           # Flow tracing API
│   │   ├── chat.py            # LLM chat endpoint
│   │   └── debug.py           # Debug stats & logs API
│   └── data/                  # Generated CSV files (9 tables)
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main layout (graph + chat)
│   │   ├── index.css          # Global styles + React Flow overrides
│   │   ├── components/
│   │   │   ├── GraphView.jsx  # React Flow graph (memo-optimized)
│   │   │   ├── ChatPanel.jsx  # Dark-themed AI chat interface
│   │   │   ├── NodeDrawer.jsx # Node metadata tooltip
│   │   │   └── DebugPanel.jsx # System stats viewer
│   │   └── hooks/
│   │       ├── useGraph.js    # Graph state management
│   │       └── useChat.js     # Chat state & API calls
│   └── vite.config.js         # Tailwind v4 + API proxy
├── AI_SESSION_TRANSCRIPT.md   # AI coding session logs
└── README.md                  # This file
```

---

## AI Session Logs

The complete AI-assisted development transcript is available in [`AI_SESSION_TRANSCRIPT.md`](./AI_SESSION_TRANSCRIPT.md).

It documents:
- All major prompts and AI responses
- Architecture decisions and rationale
- Debugging workflow (screenshot → feedback → fix iteration)
- Performance optimization steps

---

## License

MIT
