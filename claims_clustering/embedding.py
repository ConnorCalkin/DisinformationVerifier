import asyncio
import pandas as pd
from openai import AsyncOpenAI  # Ensure you use the Async client

# Assuming your connection module can provide an AsyncOpenAI client


async def get_text_embedding(client: AsyncOpenAI, text: str) -> list[float]:
    """Asynchronous call to OpenAI."""
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error processing text: {e}")
        return None


async def process_all_embeddings(claims: list[str]) -> list[list[float]]:
    """Orchestrates the concurrent API calls."""
    client = AsyncOpenAI()  # Or get_async_openai_client()
    tasks = [get_text_embedding(client, text) for text in claims]
    # gather returns results in the same order as the tasks list
    return await asyncio.gather(*tasks)


async def embed_claims_async(claims_df: pd.DataFrame) -> pd.DataFrame:
    """Wrapper to run the async processing and update the DataFrame."""
    # 1. Extract the column as a list
    claims_list = claims_df['claim'].tolist()

    # 2. FIX: Await the coroutine directly instead of using asyncio.run()
    embeddings = await process_all_embeddings(claims_list)

    # 3. Assign back to the DataFrame
    claims_df['openai_embedding'] = embeddings
    return claims_df
