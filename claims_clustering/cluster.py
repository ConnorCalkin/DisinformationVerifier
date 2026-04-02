import pandas as pd
from sklearn.metrics import silhouette_score
from dotenv import load_dotenv
from pydantic import BaseModel
import time
import asyncio
import logging
import umap
from sklearn.cluster import KMeans

from connection import get_db_connection, get_openai_client
from embedding import embed_claims_async

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_claims_and_evidence() -> list[str]:
    '''Fetches claims and evidence from the database and returns them as a list of strings.'''
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT claim_text, evidence FROM claim")
                rows = cur.fetchall()
    except Exception as e:
        logging.error(f"Error fetching claims and evidence: {e}")
        raise RuntimeError("Failed to fetch claims and evidence.")

    return rows


def get_cluster_name_and_desc_prompt(cluster_claims: list[str]) -> str:
    '''
    Creates a prompt for the LLM to generate a concise name for a given cluster.
    '''

    prompt = f"""
        You are an expert data analyst. Below is a list of text claims grouped into a single cluster based on their semantic similarity.

        ### Task:
        1. **Cluster Name**: Create a concise, high-level name (3-6 words) that captures the core theme.
        2. **Topic 1**: Identify the most common misconception or theme in the claims and describe it in 1-2 sentences.
        3. **Topic 2**: If there is a second common misconception or theme, describe it in 1-2 sentences. If not, leave this blank.

        example output format:
        Cluster Name: Flat Earth Conspiracies
        Summary: 'The common misconceptions in this topic are:
        1. The Earth is flat and disc-shaped. 
        2. Satellite images showing a round Earth are fabricated.'

        ### Claims:
    """
    for claim in cluster_claims:
        prompt += f"- {claim}\n"
    prompt += "\nCluster Name:"
    return prompt


class Cluster(BaseModel):
    cluster_name: str
    claims_topic_1: str = None
    claims_topic_2: str = None


async def get_cluster_name_and_desc_from_llm(client, cluster_claims: list[str]) -> Cluster:
    '''
    For a given cluster number,
    creates a prompt with the claims in that cluster and
    sends it to the LLM to get a concise cluster name and description.
    '''
    prompt = get_cluster_name_and_desc_prompt(cluster_claims)
    response = await client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": prompt
            },
        ],
        text_format=Cluster,
    )

    cluster_data = response.output_parsed
    return cluster_data


async def assign_cluster_name(client, cluster_claims: list[str]) -> pd.DataFrame:
    '''takes in a unique cluster number, gets a name and description from the LLM, and maps it back to the DataFrame.'''

    cluster_name_and_desc = await get_cluster_name_and_desc_from_llm(client, cluster_claims)
    cluster_name = cluster_name_and_desc.cluster_name
    cluster_description = "\n\nCommon misconceptions in this topic include:\n"
    if cluster_name_and_desc.claims_topic_1:
        cluster_description += f"1. {cluster_name_and_desc.claims_topic_1}\n"
    if cluster_name_and_desc.claims_topic_2:
        cluster_description += f"2. {cluster_name_and_desc.claims_topic_2}\n"
    return {
        'name': cluster_name,
        'description': cluster_description,
    }


async def assign_cluster_names(client, claims_df: pd.DataFrame) -> pd.DataFrame:
    '''For each unique cluster number, get a name from the LLM and map it back to the DataFrame.'''
    cluster_names = {}

    tasks = []
    unique_clusters = claims_df['cluster'].unique()
    for cluster in unique_clusters:
        cluster_claims = claims_df[claims_df['cluster']
                                   == cluster]['claim'].tolist()
        tasks.append(assign_cluster_name(client, cluster_claims))

    # Use await here, NOT asyncio.run
    cluster_name_results = await asyncio.gather(*tasks)

    for cluster, result in zip(unique_clusters, cluster_name_results):
        cluster_names[cluster] = result

    claims_df['cluster_name'] = claims_df['cluster'].map(
        lambda x: cluster_names[x]['name'])
    claims_df['cluster_description'] = claims_df['cluster'].map(
        lambda x: cluster_names[x]['description'])
    return claims_df


def kmeans_clustering(claims_df: pd.DataFrame, n_clusters: int = 5) -> pd.DataFrame:
    '''
    Performs KMeans clustering on the claim embeddings.
    '''
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    claims_df['cluster'] = kmeans.fit_predict(
        claims_df['openai_embedding'].tolist())
    return claims_df


async def cluster_claims(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Main function to cluster claims.
    Takes a DataFrame of claims and evidence and returns a DataFrame with claims,
    their assigned cluster, and cluster names.
    '''

    logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Embedding claims...")
    claims_df = await embed_claims_async(claims_df)
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Reducing dimensionality...")
    claims_df = reduce_dimensionality(claims_df)
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Determining optimal number of clusters and clustering claims...")
    n_clusters = get_best_k_value(claims_df)
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Optimal number of clusters determined: {n_clusters}. Clustering claims...")
    clustered_df = kmeans_clustering(claims_df, n_clusters=n_clusters)
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Assigning cluster names and descriptions using LLM...")
    client = get_openai_client()
    clustered_df = await assign_cluster_names(client, clustered_df)
    return clustered_df


def reduce_dimensionality(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''Uses UMAP to reduce the dimensionality of the claim embeddings for better clustering performance.'''
    umap_model = umap.UMAP()
    claims_df['umap'] = list(umap_model.fit_transform(
        claims_df['openai_embedding'].tolist()))
    return claims_df


def get_best_k_value(claims_df: pd.DataFrame) -> int:
    '''Determines the optimal number of clusters (k) for KMeans using silhouette scores.'''
    silhouette_scores = {}
    for k in range(2, 8):
        kmeans = KMeans(n_clusters=k, random_state=42)
        clusters = kmeans.fit_predict(
            claims_df['umap'].tolist())
        score = silhouette_score(
            claims_df['umap'].tolist(), clusters)
        silhouette_scores[k] = score
    best_k = max(silhouette_scores, key=silhouette_scores.get)
    logger.info(f"Silhouette scores: {silhouette_scores}")
    return best_k


def convert_claims_evidence_to_df(claims_evidence: list[tuple[str, str]]) -> pd.DataFrame:
    '''Converts a list of (claim, evidence) tuples into a DataFrame.'''
    claims = [item[0] for item in claims_evidence]
    evidence = [item[1] for item in claims_evidence]
    return pd.DataFrame({'claim': claims, 'evidence': evidence})


async def get_claims_clustered_with_evidence() -> list[dict]:
    '''Fetches claims and evidence from the database, clusters the claims, and returns a list of dictionaries with cluster names and descriptions.'''
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Fetching claims and evidence from the database...")
    claims_evidence = get_claims_and_evidence()
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Fetched {len(claims_evidence)} claims and evidence pairs.")
    claims_df = convert_claims_evidence_to_df(claims_evidence)
    logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Clustering claims...")
    clustered_claims_df = await cluster_claims(claims_df)
    logger.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Clustering complete. Converting to list of dictionaries...")
    return convert_claims_to_cluster_dicts(clustered_claims_df)


def convert_claims_to_cluster_dicts(claims_evidence: pd.DataFrame) -> list[dict]:
    '''Converts a DataFrame of claims and evidence into a list of dictionaries.'''
    clusters = claims_evidence['cluster_name'].unique()
    cluster_dicts = []
    for cluster in clusters:
        cluster_claims = claims_evidence[claims_evidence['cluster_name'] == cluster]
        cluster_dicts.append({
            'cluster_name': cluster,
            'description': cluster_claims['cluster_description'].iloc[0],
            'claims': cluster_claims[['claim', 'evidence']].to_dict(orient='records')
        })
    return cluster_dicts


def main(event: None, context: None) -> list[dict]:
    '''Main function to be called by the serverless framework.'''
    try:
        clustered_claims = asyncio.run(get_claims_clustered_with_evidence())
    except Exception as e:
        logger.error(f"Error clustering claims: {e}")
        return {
            "statusCode": 500,
            "body": "An error occurred while clustering claims. Please check the logs for more details."
        }
    try:
        add_clusters_to_db(clustered_claims)
    except Exception as e:
        logger.error(f"Error adding clusters to the database: {e}")
        return {
            "statusCode": 500,
            "body": "An error occurred while adding clusters to the database. Please check the logs for more details."
        }

    return {
        "statusCode": 200,
        "body": "Claims clustered and added to database successfully."
    }


def add_clusters_to_db(clustered_claims: list[dict]) -> None:
    '''Takes the clustered claims and adds them to the database.'''
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # deletes all the rows in the table
            cur.execute("DELETE FROM cluster")
            conn.commit()
            for cluster in clustered_claims:
                cur.execute(
                    "INSERT INTO cluster (cluster_name, cluster_description, claim_count) VALUES (%s, %s, %s) RETURNING cluster_id",
                    (cluster['cluster_name'],
                     cluster['description'], len(cluster['claims']))
                )
        conn.commit()


if __name__ == "__main__":
    load_dotenv()
    main(None, None)
