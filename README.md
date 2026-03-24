# DisinformationVerifier

# Disinformation Verifier: RAG-Powered Fact Checker

A cloud-native solution designed to combat misinformation using **Retrieval-Augmented Generation (RAG)**. This tool leverages AWS serverless architecture including AWS Secrets Manager, Large Language Models (LLMs), and vector databases to cross-reference user claims against verified Wikipedia data and trusted RSS news feeds.

---

## 🏗 System Architecture

The project is split into two primary components: the **Verification Pipeline** (User-facing) and the **Ingestion Pipeline** (Data sourcing).

### 1. Verification Phase (The User Journey)
When a user interacts with the **Streamlit** interface, the following workflow is triggered:

* **Input Handling:** Users submit a claim, a full article body, or a URL, along with a source dropdown (URL, "TikTok", "BBC NEWS", etc).
    * The 'Source' will allow analysis on largest sources of misinformation as a possible "Next Steps".
* **Content Extraction:**
    * An LLM call is made to extract individual, verifiable claims from the text.
        * If a URL is provided, an **AWS Lambda (Web Scraper)** extracts the article body first.
* **Parallel Fact-Sourcing:**
    * **Contextual Research:** A Lambda function performs **Named Entity Recognition (NER)** on the claims and queries the **Wikipedia API** to retrieve relevant background articles.
    * **Evidence Retrieval:** A second Lambda embeds the claims and queries a **ChromaDB** database (running on **ECS**) to find the most similar "truth chunks" from our trusted sources.
* **Final Verification:** The Streamlit app sends the claims, the Wiki context, and the trusted news chunks to an LLM. The LLM categorizes each claim as:

    * ✅ **Supported**
    * ⚠️ **Misleading**
    * ❌ **Contradicted**
    * ❓ **Unclear**
* **Logging:** All results (UserID, Confidence, Accuracy, Claims and Source) are stored in **DynamoDB** for history and auditing.

### 2. Ingestion Phase (The Source of Truth)
To ensure the verifier has high-quality data, we maintain a background process for trusted data:

* **Trigger:** **AWS EventBridge** schedules periodic runs of the **Ingestion Lambda**.
* **Scraping:** The Lambda pulls content from reliable RSS feeds and verified news outlets.
* **Processing:** Articles are "poor-man" chunked and embedded using AI models.
* **Storage:** The chunks are stored in **ChromaDB** (backed by **Amazon EFS** for persistence) with the following metadata:
    * `article_chunk_text`
    * `article_url`
    * `article_published` (ISO 8601 string)
    * `generated_hash_id`

---

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Frontend** | Streamlit (Python) |
| **Compute** | AWS Lambda, AWS ECS (Fargate) |
| **Database** | DynamoDB (User History), ChromaDB (Vector Store) |
| **Storage** | Amazon EFS (Elastic File System) |
| **Orchestration**| AWS EventBridge |
| **AI/ML** | LLMs (for Extraction/Verification), AI Embeddings |

---

## 🚀 Getting Started

### Prerequisites
* AWS CLI configured with appropriate permissions.
* Python 3.9+
* Docker (for ECS-based services).

### Installation
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/disinformation-verifier.git](https://github.com/your-username/disinformation-verifier.git)
    ```
2.  **Environment Setup:**
    Create a `.env` file with your LLM API keys and AWS region details.
3.  **Deploy Infrastructure:**
    Use the provided CloudFormation/Terraform templates to spin up the Lambda functions and ECS clusters.
4.  **Run Streamlit Locally:**
    ```bash
    cd streamlit-app
    pip install -r requirements.txt
    streamlit run app.py
    ```

---

## 📝 Data Governance & Privacy
User history is tracked in DynamoDB to provide insights into disinformation trends and system accuracy. We prioritize "Trusted Sources" to ensure the RAG context is not poisoned by unverified web data.
