import os
from openai import AsyncOpenAI
import json

async def generate_match_summary(match_data: dict, locale: str = "en") -> str:
    """
    Generates a witty, 2-sentence match summary using the OpenAI API.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "AI summary generation is not configured."

    client = AsyncOpenAI(api_key=api_key)

    system_prompt = "You are an energetic Padel sportscaster. Your tone should be fun and slightly dramatic."
    language = "Hebrew" if locale == "he" else "English"

    user_prompt = f"""
    Write a 2-sentence witty summary in {language} of the following Padel match.
    Highlight the winners and be sure to mention any 'bagels' (sets won 6-0).
    ---
    Match Data:
    {json.dumps(match_data, indent=2)}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        # In a real app, you'd want to log this error
        print(f"Error generating match summary: {e}")
        return "Could not generate AI summary at this time."
