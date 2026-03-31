import pandas as pd
import numpy as np
from requests import get
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import umap

from connection import get_db_connection, get_secrets, get_openai_client


def get_test_claims_evidence() -> list[str]:
    data = [
        # Topic 1: Flat Earth
        "The Earth is a flat disc protected by an ice wall.",
        "Gravity is an illusion; the Earth is accelerating upwards.",
        "Satellite photos of a curved Earth are all CGI manipulations.",
        "The horizon always appears perfectly flat to the human eye.",

        # Topic 2: Vaccines
        "Vaccines are a primary cause of childhood autism.",
        "The COVID-19 vaccine is used to implant trackable microchips.",
        "Mandatory vaccinations are a tool for population control.",
        "Natural immunity is always superior to any synthetic vaccine.",

        # Topic 3: Moon Landing
        "NASA staged the moon landing on a Hollywood film set.",
        "The American flag waving on the moon proves there was wind.",
        "Humans cannot survive passing through the Van Allen radiation belts.",
        "No stars are visible in the background of lunar photographs.",

        # Topic 4: Climate Change
        "Global warming is a hoax invented for carbon tax revenue.",
        "The Earth is actually entering a period of global cooling.",
        "Climate change is a natural cycle and CO2 has no impact.",
        "Arctic ice caps are actually expanding rather than melting.",

        # Topic 5: 5G Technology
        "5G cellular radiation weakens the immune system to spread viruses.",
        "The rollout of 5G towers is linked to the COVID-19 outbreak.",
        "High-frequency 5G signals are being used for mind control.",
        "5G infrastructure is a weaponized surveillance system.",

        "The Financial Conduct Authority will implement a redress scheme for car finance mis-selling affecting agreements dated 6 April 2007 to 1 November 2024.",
        "12.1 million agreements are eligible for redress under the scheme.",
        "Average redress per eligible agreement is £829.",
        "Total cost to firms for redress is £7.5 billion, with £1.6 billion in non-redress costs, totaling £9.1 billion (down from £11 billion).",
        "Uptake of the scheme is estimated at 75 percent.",
        "Firms have three months from the end of the implementation period to inform complainants of eligibility and compensation amounts.",
        "A taskforce will be created to crack down on claims management companies and law firms targeting drivers, in cooperation with regulators such as the SRA, ICO, and ASA.",
        "The government is reviewing the ZEV mandate and may lower the EV sale quotas.",
        "The ZEV mandate requires annual increases in the share of zero-emission car and van sales to reach 100% by 2035.",
        "The 2026 ZEV target is 33%; the 2025 target was 28%; the 2024 target was 22%.",
        "UK car production in 2025 was the lowest since 1952.",
        "One in four new cars sold last year was zero emission (about 25%).",
        "Carmakers face a £12,000 penalty for each car not sold to meet the quota.",
        "The government removed some EV buyer incentives by ending the vehicle excise duty exemption for EVs and introducing a pay-per-mile road tax from 2028.",
        "Hybrids can be sold until 2035; small manufacturers are exempt from the 2030 petrol/diesel phase-out.",
        "The government plans to publish the ZEV mandate review by early 2027.",
        "Labour aims to manufacture 1.3 million vehicles per year by 2035 (nearly double 2024/2025 levels).",
        "The policy has been criticized by Conservatives as financially burdensome and ideologically driven by net-zero targets.",
        "The European Union proposes an emergency brake mechanism to limit surges of youth mobility visa entrants rather than imposing an upfront numerical cap.",
        "Kirsten Bailey is subject to a lifetime disqualification from keeping animals.",
        "Bailey admitted breaching the disqualification order.",
        "An SSPCA inspector found the house in disarray with used puppy pads containing urine and faeces.",
        "The two dogs belonged to Bailey's partner.",
        "Bailey claimed she was caring for the dogs and believed the order had been appealed successfully.",
        "The dogs were seized for seven days and returned to Baileys' partner.",
        "Sheriff McGeehan fined Bailey £320."
    ]

    return data


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


def get_cluster_name_prompt(claims_df: pd.DataFrame, cluster_num: int) -> str:
    '''
    Creates a prompt for the LLM to generate a concise name for a given cluster.
    '''
    cluster_claims = claims_df[claims_df['cluster']
                               == cluster_num]['claim'].tolist()
    prompt = f"Given the following claims, provide a concise name that captures the common theme:\n\n"
    for claim in cluster_claims:
        prompt += f"- {claim}\n"
    prompt += "\nCluster Name:"
    return prompt


def get_cluster_name_from_llm(claims_df: pd.DataFrame, cluster_num: int) -> str:
    '''
    For a given cluster number, 
    creates a prompt with the claims in that cluster and 
    sends it to the LLM to get a concise cluster name.
    '''
    prompt = get_cluster_name_prompt(claims_df, cluster_num)
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes clusters of claims."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=50,
        temperature=0.5
    )
    cluster_name = response.choices[0].message.content.strip()
    return cluster_name


def assign_cluster_names(claims_df: pd.DataFrame) -> pd.DataFrame:
    '''For each unique cluster number, get a name from the LLM and map it back to the DataFrame.'''
    cluster_names = {}
    for cluster_num in claims_df['cluster'].unique():
        cluster_name = get_cluster_name_from_llm(claims_df, cluster_num)
        cluster_names[cluster_num] = cluster_name
    claims_df['cluster_name'] = claims_df['cluster'].map(cluster_names)
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


if __name__ == "__main__":
    load_dotenv()
    claims = get_claims_and_evidence()
    claims_df = convert_claims_evidence_to_df(claims)
    clustered_claims_df = cluster_claims(claims_df)
    print(clustered_claims_df["cluster_name"].value_counts())
    print(clustered_claims_df[['claim', 'cluster',
          'cluster_name', 'evidence']].head(20))
