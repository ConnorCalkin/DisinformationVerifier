import json
import logging
from os import environ
import boto3
import wikipedia
import wikipediaapi
from openai import OpenAI

sm_client = boto3.client('secretsmanager', region_name='eu-west-2')
wiki_api = wikipediaapi.Wikipedia(
    user_agent="DisinformationVerifier/1.0",
    language='en')

_CACHED_SECRET = None
_OPENAI_CLIENT = None


def setup_logging():
    """ Configures logging for the Lambda function. Logs will be sent to CloudWatch. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def get_secrets() -> dict:
    """Fetches OpenAI API key from AWS Secrets Manager."""
    global _CACHED_SECRET
    if _CACHED_SECRET:
        return _CACHED_SECRET
    secret_name = environ.get("SECRET_ID")
    if not secret_name:
        logging.error("SECRET_ID environment variable not set.")
        raise EnvironmentError("SECRET_ID environment variable not set.")

    try:
        response = sm_client.get_secret_value(SecretId=secret_name)
        _CACHED_SECRET = json.loads(response['SecretString'])
        logging.info("Secrets successfully retrieved and cached.")
        return _CACHED_SECRET
    except Exception as e:
        logging.error(f"Error fetching secrets from AWS Secrets Manager: {e}")
        raise EnvironmentError(
            "Failed to retrieve secrets from AWS Secrets Manager.")


def get_openai_client() -> OpenAI:
    """ Abstracted function to intialise and cache the OpenAI client. """
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT:
        return _OPENAI_CLIENT
    try:
        secrets = get_secrets()
        api_key = secrets.get('OPENAI_API_KEY')

        if not api_key:
            logging.error("OPENAI_API_KEY not found in secrets.")
            raise KeyError("OPENAI_API_KEY not found in secrets.")
        _OPENAI_CLIENT = OpenAI(api_key=api_key)

        logging.info("OpenAI client initialized and cached.")
        return _OPENAI_CLIENT
    except Exception as e:
        logging.error(f"Error initializing OpenAI client: {e}")
        raise RuntimeError("Failed to initialize OpenAI client.")


def _call_llm_for_terms(openai_client: OpenAI, prompt: str) -> list[str]:
    """ Phase 1: API Interaction - Only for networking calls to the LLM. """
    response = openai_client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content


def _parse_llm_response(raw_content: str) -> list[str]:
    """ Phase 2: Response Handling - Only for parsing and validating the LLM's output. """
    try:
        data = json.loads(raw_content)
        return list(set(data.get("search_terms", [])))  # Ensure uniqueness
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(
            f"Error parsing LLM response: {e}, Raw content: {raw_content}")
        return []


def extract_wiki_terms_from_claims(claims: list[str]) -> list[str]:
    """ Extracts relevant Wikipedia article titles to verify the list of claims."""
    openai_client = get_openai_client()

    prompt = f"""
    Analyze the following claims and identify 1-3 specific Wikipedia article titles
    needed to verify each. Focus on Named Entities (People, Orgs) and specific Events.

    Claims: {claims}

    Return ONLY a JSON object with the key 'search_terms'.
    Example: {{"search_terms": ["NASA", "Artemis program", "2024 Solar Eclipse"]}}
    """
    # Call OpenAI API with the prompt and return the list of article titles
    try:
        raw_content = _call_llm_for_terms(openai_client, prompt)
        return _parse_llm_response(raw_content)
    except Exception as e:
        logging.error(f"LLM extraction error: {e}")
        return []


def resolve_wiki_titles(query_terms: list[str]) -> list[str]:
    """ Takes the LLM's suggested terms and finds actual, existing Wikipedia article titles. """
    valid_titles = []
    for term in query_terms:
        search_hits = wikipedia.search(term, results=1)
        if search_hits:
            valid_titles.append(search_hits[0])  # Take the top search result
        else:
            logging.warning(f"No Wikipedia article found for term: {term}")

    return list(set(valid_titles))  # Ensure uniqueness


def _extract_relevant_sections(
        sections: list[wikipediaapi.WikipediaPageSection], keywords: list[str]) -> str:
    """ Helper function to scan Wikipedia sections for relevance based on claim keywords. """
    smart_content = ""
    for section in sections:
        if any(word in section.title.lower() or word in section.text.lower()
               for word in keywords):
            smart_content += f"SECTION: [{section.title} : {section.text}]\n\n"
    return smart_content


def _format_article_response(
        title: str,
        url: str,
        summary: str,
        relevant_sections: str) -> dict:
    """ Helper function to structure the Wikipedia article data in a consistent format. """
    return {
        "title": title,
        "url": url,
        "summary": summary,
        "relevant_sections": relevant_sections
    }


def fetch_article_body(title: str, claims: list[str]) -> dict:
    """ Retrieves context prioritising the summary and relevant sections of the Wikipedia article. """

    page = wiki_api.page(title)

    if not page.exists():
        logging.warning(f"Article not found: {title}")
        return {}

    # Scan sections for keywords from the claims to find relevant context
    # Flattens claims into a list of keywords
    keywords = " ".join(claims).lower().split()
    relevant_sections = _extract_relevant_sections(page.sections, keywords)

    return _format_article_response(
        title=title,
        url=page.fullurl,
        summary=page.summary,
        relevant_sections=relevant_sections
    )


setup_logging()  # Initialize logging configuration at the start of the Lambda execution


def lambda_handler(event, context):
    """ Coordinates the flow from Claim Input -> Search Terms -> Wiki Data Retrieval. """

    logging.info(f"Lambda execution started", extra={"event": event})

    try:
        # Step 1: Parse input from previous pipeline step ie the list of claims
        claims = event.get("claims", [])
        if not claims:
            logging.warning(
                "Validation Failed: 'claims' key is missing or empty in the event.")
            return {"statusCode": 400, "body": json.dumps(
                {"error": "No claims provided in the event."})}
        # Step 2: Extract relevant Wikipedia article titles using LLM
        search_queries = extract_wiki_terms_from_claims(claims)
        if not search_queries:
            logging.warning(
                "LLM did not return any search terms. Skipping Wikipedia retrieval.")
            return {
                "statusCode": 200,
                # Return empty context if no search terms found
                "body": json.dumps({"wiki_context": [],
                                    "message": "No relevant search terms found."})
            }
        # Step 3: Resolve those titles to actual Wikipedia articles
        valid_titles = resolve_wiki_titles(search_queries)
        # Step 4: Fetch the content of each valid Wikipedia article
        wiki_evidence = []
        for title in valid_titles:
            article_data = fetch_article_body(title, claims)
            if article_data:
                wiki_evidence.append(article_data)

        logging.info(f"Retrieved Wikipedia context: {wiki_evidence}")
        return {
            "statusCode": 200,
            "body": json.dumps({"wiki_context": wiki_evidence})
        }
    except Exception as e:
        logging.critical(f"Top-Level Pipeline Failure: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal research engine error."})
        }
