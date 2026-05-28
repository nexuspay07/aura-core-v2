import os

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


async def generate_strategic_intelligence(prompt: str):

    system_prompt = """
    You are AURA Strategic Intelligence.

    You provide:
    - business strategy
    - market analysis
    - growth recommendations
    - operational intelligence
    - risk evaluation
    - executive-level planning

    Be concise, intelligent, strategic, and practical.
    """

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content