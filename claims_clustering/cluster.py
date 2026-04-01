import pandas as pd
import numpy as np
from requests import get
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import umap
from pydantic import BaseModel

from connection import get_db_connection, get_openai_client


def get_claims_and_evidence() -> list[str]:
    '''Fetches claims and evidence from the database and returns them as a list of strings.'''
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT claim_text, evidence FROM claim")
            rows = cur.fetchall()

    return rows


def embed_claims(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''Uses Sentence Transformers to create embeddings for each claim in the DataFrame.'''
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    claims_df['encode_transforemers'] = claims_df['claim'].apply(
        lambda text: model.encode(text, convert_to_numpy=True).flatten())
    return claims_df


def get_cluster_name_and_desc_prompt(claims_df: pd.DataFrame, cluster_num: int) -> str:
    '''
    Creates a prompt for the LLM to generate a concise name for a given cluster.
    '''
    cluster_claims = claims_df[claims_df['cluster']
                               == cluster_num]['claim'].tolist()
    prompt = f"""
        You are an expert data analyst. Below is a list of text claims grouped into a single cluster based on their semantic similarity.

        ### Task:
        1. **Cluster Name**: Create a concise, high-level name (3-6 words) that captures the core theme.
        2. **Summary**: Provide a description that talks about one or two common misconceptions in this cluster. Focus on the most prevalent misinformation themes.

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
    description: str


def get_cluster_name_and_desc_from_llm(claims_df: pd.DataFrame, cluster_num: int) -> Cl:
    '''
    For a given cluster number, 
    creates a prompt with the claims in that cluster and 
    sends it to the LLM to get a concise cluster name and description.
    '''
    prompt = get_cluster_name_and_desc_prompt(claims_df, cluster_num)
    client = get_openai_client()
    response = client.responses.parse(
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


def assign_cluster_names(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''For each unique cluster number, get a name from the LLM and map it back to the DataFrame.'''
    cluster_names = {}
    for cluster_num in claims_df['cluster'].unique():
        cluster_name_and_desc = get_cluster_name_and_desc_from_llm(
            claims_df, cluster_num)
        cluster_name = cluster_name_and_desc.cluster_name
        cluster_description = cluster_name_and_desc.description
        cluster_names[cluster_num] = {
            'name': cluster_name,
            'description': cluster_description
        }
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
        claims_df['encode_transforemers'].tolist())
    return claims_df


def cluster_claims(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Main function to cluster claims. 
    Takes a DataFrame of claims and evidence and returns a DataFrame with claims,
    their assigned cluster, and cluster names.
    '''
    claims_df = embed_claims(claims_df)
    claims_df = reduce_dimensionality(claims_df)
    n_clusters = get_best_k_value(claims_df)
    clustered_df = kmeans_clustering(claims_df, n_clusters=n_clusters)
    clustered_df = assign_cluster_names(clustered_df)
    return clustered_df


def reduce_dimensionality(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''Uses UMAP to reduce the dimensionality of the claim embeddings for better clustering performance.'''
    umap_model = umap.UMAP()
    claims_df['umap'] = list(umap_model.fit_transform(
        claims_df['encode_transforemers'].tolist()))
    return claims_df


def get_best_k_value(claims_df: pd.DataFrame) -> int:
    '''Determines the optimal number of clusters (k) for KMeans using silhouette scores.'''
    silhouette_scores = {}
    for k in range(2, 11):
        kmeans = KMeans(n_clusters=k, random_state=42)
        clusters = kmeans.fit_predict(
            claims_df['umap'].tolist())
        score = silhouette_score(
            claims_df['umap'].tolist(), clusters)
        silhouette_scores[k] = score
    best_k = max(silhouette_scores, key=silhouette_scores.get)
    print(silhouette_scores)
    return best_k


def convert_claims_evidence_to_df(claims_evidence: list[tuple[str, str]]) -> pd.DataFrame:
    '''Converts a list of (claim, evidence) tuples into a DataFrame.'''
    claims = [item[0] for item in claims_evidence]
    evidence = [item[1] for item in claims_evidence]
    return pd.DataFrame({'claim': claims, 'evidence': evidence})


def get_claims_clustered_with_evidence() -> pd.DataFrame:
    '''Fetches claims and evidence from the database, clusters the claims, and returns a DataFrame with cluster names and descriptions.'''
    claims_evidence = get_claims_and_evidence()
    claims_df = convert_claims_evidence_to_df(claims_evidence)
    clustered_claims_df = cluster_claims(claims_df)
    return clustered_claims_df


if __name__ == "__main__":
    load_dotenv()
    clustered_claims_df = get_claims_clustered_with_evidence()
    print(clustered_claims_df["cluster_name"].value_counts())
    for claim in clustered_claims_df.itertuples():
        print(f"Claim: {claim.claim}")
        print(f"Evidence: {claim.evidence}")
        print(f"Cluster: {claim.cluster_name}")
        print(f"Description: {claim.cluster_description}")
        print("-----")
