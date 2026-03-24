import json
import boto3
import logging
from os import environ
import wikipedia
import wikipediaapi
from openai import OpenAI


sm_client = boto3.client('secretsmanager', region_name='eu-west-2')  # Ensure this matches your Secrets Manager region
wiki_api = wikipediaapi.Wikipedia(user_agent="DisinformationVerifier/1.0", language='en')

_CACHED_SECRET = None
_OPENAI_CLIENT = None

def setup_logging():
    """ Configures logging for the Lambda function. Logs will be sent to CloudWatch. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def get_secrets():
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
        raise EnvironmentError("Failed to retrieve secrets from AWS Secrets Manager.")


def get_openai_client():
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
    

def extract_wiki_terms_from_claims(claims: list[str]) -> list[str]:
    """ Uses an LLM to extract relevant Wikipedia article titles needed to verify the list of claims."""
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
        response = openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content_dict = json.loads(response.choices[0].message.content)
        terms = list(set(content_dict.get("search_terms", [])))  # Ensure uniqueness
        logging.info(f"Extracted Wikipedia search terms: {terms}")
        return terms
    
    except Exception as e:
        logging.error(f"Error during LLM article extraction: {e}")
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


def fetch_article_body(title: str, claims: list[str]) -> dict:
    """ Retrieves structured context by prioritising the summary and relevant sections of the Wikipedia article. """

    page = wiki_api.page(title)
    
    if not page.exists():
        logging.warning(f"Article not found: {title}")
        return None
    
    smart_content = f"SUMMARY: {page.summary}\n\n"

    # Scan sections for keywords from the claims to find relevant context
    keywords = " ".join(claims).lower().split() # Flattens claims into a list of keywords

    for section in page.sections:
        if any(word in section.title.lower() or word in section.text.lower() for word in keywords):
            smart_content += f"SECTION: [{section.title} : {section.text}]\n\n"

    return {
        "title": title,
        "url": page.fullurl,
        "summary": page.summary,
        "relevant_sections": smart_content
    }


def lambda_handler(event, context):
    """ Coordinates the flow from Claim Input -> Search Terms -> Wiki Data Retrieval. """
    
    logging.info(f"Processing event: {json.dumps(event)}")

    try:
        # Step 1: Parse input from previous pipeline step ie the list of claims
        claims = event.get("claims", [])
        if not claims:
            logging.warning("No claims provided in the event.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No claims provided in the event."})
            }
        # Step 2: Extract relevant Wikipedia article titles using LLM
        search_queries = extract_wiki_terms_from_claims(claims)
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
            "statusCode" : 200,
            "wiki_context" : wiki_evidence
        }
    except Exception as e:
        logging.critical(f"Pipeline Failure: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal research engine error."})
        }